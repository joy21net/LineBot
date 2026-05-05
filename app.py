import os
import re
import time
import logging
from functools import lru_cache

from flask import Flask, request, abort, render_template, jsonify
from dotenv import load_dotenv
from pronunciation import japanese_to_korean_pronunciation

from linebot.v3 import WebhookHandler
from linebot.v3.messaging import MessagingApi
from linebot.v3.messaging.configuration import Configuration
from linebot.v3.messaging.api_client import ApiClient
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent
)

import sqlite3
import unicodedata
import uuid
import subprocess
import io
import requests as http_requests
from PIL import Image, ImageDraw, ImageFont
from urllib.parse import quote
import imageio_ffmpeg
from mutagen.mp4 import MP4
from linebot.v3.messaging.models import ImageMessage, AudioMessage, ShowLoadingAnimationRequest
from linebot.v3.messaging.models import (
    TextMessage,
    ReplyMessageRequest,
    TemplateMessage,
    ButtonsTemplate,
    URIAction
)
from openai import OpenAI
import random

# 환경 변수 로드

# 환경 변수 로드
load_dotenv()

# Flask 앱 초기화
app = Flask(__name__)

# 로깅 설정
logging.basicConfig(level=logging.INFO)

# 환경 변수에서 필요한 정보 가져오기
LINE_CHANNEL_ID = os.getenv('LINE_CHANNEL_ID')
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

DB_PATH = os.path.join(os.path.dirname(__file__), "db.sqlite3")


# 라인봇 API 및 핸들러 초기화
configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
api_client = ApiClient(configuration=configuration)
line_bot_api = MessagingApi(api_client)
handler = WebhookHandler(channel_secret=LINE_CHANNEL_SECRET)

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=OPENAI_API_KEY)

# 학습 데이터 로드
def load_dialogs():
    dialogs = []
    try:
        path = os.path.join(os.path.dirname(__file__), "dialog1.txt")
        with open(path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
            for i in range(0, len(lines), 3):
                if i + 2 < len(lines):
                    line_text: str = lines[i]
                    # "A: ", "B: " 접두어 제거
                    if line_text.startswith(("A: ", "B: ")):
                        line_text = line_text[3:]
                    
                    dialogs.append({
                        "sentence": line_text,
                        "pronunciation": lines[i+1].strip("()"),
                        "meaning": lines[i+2]
                    })
    except Exception as e:
        app.logger.error(f"Error loading dialogs: {e}")
    return dialogs

def load_verbs():
    verbs = []
    try:
        path = os.path.join(os.path.dirname(__file__), "verb1.txt")
        with open(path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
            for i in range(0, len(lines), 2):
                if i + 1 < len(lines):
                    verbs.append({
                        "word": lines[i],
                        "answer": lines[i+1]
                    })
    except Exception as e:
        app.logger.error(f"Error loading verbs: {e}")
    return verbs

# =====================================================================
# 사용자별 설정 DB (SQLite) - 통역/발음/음성 ON/OFF
# H2(Java 전용) 대신 Python 내장 SQLite 사용 (동일한 임베디드 파일 DB)
# =====================================================================

DIALOG_DATA = load_dialogs()
VERB_DATA = load_verbs()
user_quiz_state = {} # user_id: {"correct_answer": int}

# 캐시 설정 (최대 1000개의 최근 번역 결과를 저장하여 속도 향상)

def init_db():
    """DB 초기화 - user_settings 테이블 생성"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS translation_cache (
                original_text TEXT PRIMARY KEY,
                source_lang TEXT,
                target_lang TEXT,
                translated_text TEXT,
                pronunciation TEXT,
                audio_target TEXT,
                usage_count INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                updated_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id      TEXT PRIMARY KEY,
                translation  INTEGER NOT NULL DEFAULT 1,
                pronunciation INTEGER NOT NULL DEFAULT 0,
                voice        INTEGER NOT NULL DEFAULT 0,
                updated_at   TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)
        conn.commit()
    app.logger.info(f'DB 초기화 완료: {DB_PATH}')

def get_user_settings(user_id):
    """DB에서 사용자 설정 조회. 없으면 기본값(통역 ON, 발음/음성 OFF)으로 신규 생성."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute('SELECT * FROM user_settings WHERE user_id = ?', (user_id,)).fetchone()
        if row is None:
            conn.execute('INSERT INTO user_settings (user_id, translation, pronunciation, voice) VALUES (?, 1, 0, 0)', (user_id,))
            conn.commit()
            return {'translation': True, 'pronunciation': False, 'voice': False}
        return {'translation': bool(row['translation']), 'pronunciation': bool(row['pronunciation']), 'voice': bool(row['voice'])}

def set_user_setting(user_id, key, value):
    """DB에서 특정 설정 키 값을 업데이트."""
    allowed_keys = {'translation', 'pronunciation', 'voice'}
    if key not in allowed_keys:
        raise ValueError(f'Unknown setting key: {key}')
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('INSERT OR IGNORE INTO user_settings (user_id) VALUES (?)', (user_id,))
        conn.execute(f"UPDATE user_settings SET {key} = ?, updated_at = datetime('now','localtime') WHERE user_id = ?", (1 if value else 0, user_id))
        conn.commit()

def generate_tts_audio(text, voice='nova'):
    unique_id = uuid.uuid4().hex
    aac_filename = f'temp_{unique_id}.aac'
    m4a_filename = f'tts_{unique_id}.m4a'
    aac_filepath = os.path.join('static', aac_filename)
    m4a_filepath = os.path.join('static', m4a_filename)
    if not os.path.exists('static'):
        os.makedirs('static')
    response = client.audio.speech.create(model='tts-1', voice=voice, input=text, response_format='aac', speed=0.85)
    response.stream_to_file(aac_filepath)
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([exe, '-y', '-i', aac_filepath, '-c:a', 'copy', m4a_filepath], check=True)
    if os.path.exists(aac_filepath):
        try:
            os.remove(aac_filepath)
        except:
            pass
    try:
        audio = MP4(m4a_filepath)
        duration_ms = int(audio.info.length * 1000)
    except Exception:
        duration_ms = 3000
    return (m4a_filename, duration_ms)

def get_jp_font(size):
    """일본어 전용 폰트 로드"""
    font_paths = ['/System/Library/Fonts/AppleSDGothicNeo.ttc', '/System/Library/Fonts/Supplemental/AppleGothic.ttf', 'C:/Windows/Fonts/meiryo.ttc', 'C:/Windows/Fonts/YuGothM.ttc', 'C:/Windows/Fonts/msgothic.ttc', '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc']
    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()

def get_kr_font(size):
    """한국어 전용 폰트 로드"""
    font_paths = ['/System/Library/Fonts/AppleSDGothicNeo.ttc', '/System/Library/Fonts/Supplemental/AppleGothic.ttf', 'C:/Windows/Fonts/malgun.ttf', 'C:/Windows/Fonts/malgunbd.ttf', 'C:/Windows/Fonts/gulim.ttc', 'C:/Windows/Fonts/batang.ttc', '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc']
    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()

def generate_picture_card(korean_word):
    """한국어 단어를 받아 DALL-E 이미지 + 일본어/발음 합성 이미지 생성"""
    trans_response = client.chat.completions.create(model='gpt-4o-mini', messages=[{'role': 'system', 'content': 'Translate the given Korean word to Japanese. Output EXACTLY two lines:\nLine 1: The Japanese word (use kanji if commonly written in kanji)\nLine 2: The hiragana reading\nNo other text, no punctuation, no explanation.'}, {'role': 'user', 'content': korean_word}])
    content = trans_response.choices[0].message.content.strip()
    lines = content.split('\n')
    japanese_word = lines[0].strip()
    hiragana = lines[1].strip() if len(lines) > 1 else japanese_word
    korean_pron = japanese_to_korean_pronunciation(hiragana)
    app.logger.info(f'그림 카드 생성: {korean_word} → {japanese_word} ({hiragana}) [{korean_pron}]')
    image_response = client.images.generate(model='dall-e-3', prompt=f'A cute, colorful, high-quality illustration of a {korean_word}. Clean and simple style, white or light solid background. IMPORTANT: The image must contain ABSOLUTELY NO text, NO letters, NO words, NO characters, NO writing, NO signs, NO labels, NO watermarks of any kind. Pure illustration only.', size='1024x1024', quality='standard', n=1)
    temp_url = image_response.data[0].url
    img_data = http_requests.get(temp_url).content
    ai_image = Image.open(io.BytesIO(img_data)).convert('RGB')
    text_area_height = 220
    combined_width = ai_image.width
    combined_height = ai_image.height + text_area_height
    combined = Image.new('RGB', (combined_width, combined_height), '#FFFFFF')
    combined.paste(ai_image, (0, 0))
    draw = ImageDraw.Draw(combined)
    font_jp = get_jp_font(64)
    font_pron = get_kr_font(48)
    if japanese_word != hiragana:
        jp_display = f'{japanese_word}（{hiragana}）'
    else:
        jp_display = japanese_word
    jp_bbox = draw.textbbox((0, 0), jp_display, font=font_jp)
    jp_text_width = jp_bbox[2] - jp_bbox[0]
    jp_x = (combined_width - jp_text_width) // 2
    jp_y = ai_image.height + 30
    draw.text((jp_x, jp_y), jp_display, fill='#1a1a2e', font=font_jp)
    pron_display = f'({korean_pron})'
    pron_bbox = draw.textbbox((0, 0), pron_display, font=font_pron)
    pron_text_width = pron_bbox[2] - pron_bbox[0]
    pron_x = (combined_width - pron_text_width) // 2
    pron_y = jp_y + 80
    draw.text((pron_x, pron_y), pron_display, fill='#e94560', font=font_pron)
    line_y = ai_image.height + 10
    draw.line([(50, line_y), (combined_width - 50, line_y)], fill='#cccccc', width=2)
    if not os.path.exists('static'):
        os.makedirs('static')
    filename = f'{korean_word}.png'
    filepath = os.path.join('static', filename)
    combined.save(filepath, 'PNG', quality=95)
    return filename

def generate_picture_card_jp(japanese_word):
    """일본어 단어를 받아 DALL-E 이미지 + 한국어 번역 합성 이미지 생성"""
    trans_response = client.chat.completions.create(model='gpt-4o-mini', messages=[{'role': 'system', 'content': 'Translate the given Japanese word to Korean. Output EXACTLY one line:\nThe Korean translation of the word.\nNo other text, no punctuation, no explanation.'}, {'role': 'user', 'content': japanese_word}])
    korean_word = trans_response.choices[0].message.content.strip()
    has_kanji = bool(re.search('[\\u4e00-\\u9faf]', japanese_word))
    hiragana = japanese_word
    if has_kanji:
        reading_response = client.chat.completions.create(model='gpt-4o-mini', messages=[{'role': 'system', 'content': 'Output ONLY the hiragana reading of the given Japanese word. No other text.'}, {'role': 'user', 'content': japanese_word}])
        hiragana = reading_response.choices[0].message.content.strip()
    korean_pron = japanese_to_korean_pronunciation(hiragana)
    app.logger.info(f'그림 카드(JP) 생성: {japanese_word} ({hiragana}) → {korean_word} [{korean_pron}]')
    image_response = client.images.generate(model='dall-e-3', prompt=f'A cute, colorful, high-quality illustration of a {korean_word}. Clean and simple style, white or light solid background. IMPORTANT: The image must contain ABSOLUTELY NO text, NO letters, NO words, NO characters, NO writing, NO signs, NO labels, NO watermarks of any kind. Pure illustration only.', size='1024x1024', quality='standard', n=1)
    temp_url = image_response.data[0].url
    img_data = http_requests.get(temp_url).content
    ai_image = Image.open(io.BytesIO(img_data)).convert('RGB')
    text_area_height = 280
    combined_width = ai_image.width
    combined_height = ai_image.height + text_area_height
    combined = Image.new('RGB', (combined_width, combined_height), '#FFFFFF')
    combined.paste(ai_image, (0, 0))
    draw = ImageDraw.Draw(combined)
    font_jp = get_jp_font(60)
    font_kr = get_kr_font(56)
    font_pron = get_kr_font(40)
    line_y = ai_image.height + 10
    draw.line([(50, line_y), (combined_width - 50, line_y)], fill='#cccccc', width=2)
    if has_kanji and japanese_word != hiragana:
        jp_display = f'{japanese_word}（{hiragana}）'
    else:
        jp_display = japanese_word
    jp_bbox = draw.textbbox((0, 0), jp_display, font=font_jp)
    jp_text_width = jp_bbox[2] - jp_bbox[0]
    jp_x = (combined_width - jp_text_width) // 2
    jp_y = ai_image.height + 25
    draw.text((jp_x, jp_y), jp_display, fill='#1a1a2e', font=font_jp)
    pron_display = f'({korean_pron})'
    pron_bbox = draw.textbbox((0, 0), pron_display, font=font_pron)
    pron_text_width = pron_bbox[2] - pron_bbox[0]
    pron_x = (combined_width - pron_text_width) // 2
    pron_y = jp_y + 70
    draw.text((pron_x, pron_y), pron_display, fill='#888888', font=font_pron)
    kr_bbox = draw.textbbox((0, 0), korean_word, font=font_kr)
    kr_text_width = kr_bbox[2] - kr_bbox[0]
    kr_x = (combined_width - kr_text_width) // 2
    kr_y = pron_y + 55
    draw.text((kr_x, kr_y), korean_word, fill='#e94560', font=font_kr)
    if not os.path.exists('static'):
        os.makedirs('static')
    filename = f'{japanese_word}.png'
    filepath = os.path.join('static', filename)
    combined.save(filepath, 'PNG', quality=95)
    return filename

@lru_cache(maxsize=1000)
def get_translation_from_api(text, source_lang, target_lang):
    if source_lang == '한국어':
        instructions = '\nYou are a professional translator.\nTask: Translate Korean to Japanese.\n\nRules:\n1. Output ONLY the natural Japanese translation of the input, preserving the EXACT same line breaks, blank lines, and indentation/spacing structure as the original input.\n2. CRITICAL: Do NOT output any explanations, English text, phonetic pronunciations, or extra lines. Just the translated Japanese text.\n3. CRITICAL: The translated Japanese text MUST NOT contain any Korean characters (Hangul). Ensure a complete translation to Japanese.\n\nExample Structure:\nInput: 그래\n잘 했어\nOutput: よかった\nよくやったね\n'
        response = client.chat.completions.create(model='gpt-5.1-chat-latest', messages=[{'role': 'system', 'content': instructions.strip()}, {'role': 'user', 'content': text}])
        translated_japanese = response.choices[0].message.content.strip()
        if len(translated_japanese.splitlines()) > 3:
            return (translated_japanese, None, None)
        hangul_pronunciation = japanese_to_korean_pronunciation(translated_japanese)
        audio_target = translated_japanese if len(text.splitlines()) == 1 else None
        return (translated_japanese, hangul_pronunciation, audio_target)
    else:
        instructions = '\nYou are a professional translator.\nTask: Translate Japanese to Korean.\n\nRules:\n1. Output ONLY the natural Korean translation of the input, preserving the EXACT same line breaks, blank lines, and indentation/spacing structure as the original input.\n2. CRITICAL: Do NOT output any explanations, English text, phonetic pronunciations, or extra lines. Just the translated Korean text.\n3. CRITICAL: The translated Korean text MUST NOT contain any Japanese characters (Hiragana, Katakana, or Kanji). Ensure a complete translation to Korean.\n'
        response = client.chat.completions.create(model='gpt-5.1-chat-latest', messages=[{'role': 'system', 'content': instructions.strip()}, {'role': 'user', 'content': text}])
        translated_korean = response.choices[0].message.content.strip()
        audio_target = translated_korean if len(text.splitlines()) == 1 else None
        return (translated_korean, None, audio_target)

def get_ai_response(text, trigger_lang):
    """
    AI 설명 모드: 사용자의 질문에 대해 인공지능이 설명하고 번역을 제공함.
    trigger_lang: 'KR' (한국어 우선), 'JP' (일본어 우선)
    """
    if trigger_lang == 'KR':
        system_prompt = """
You are a helpful AI assistant. 
When the user asks a question (starting with a hashtag), provide a clear and concise explanation in Korean.
Immediately following the Korean explanation, provide a natural Japanese translation of that explanation.
Format:
Line 1+: Korean explanation
[Separator]
Line 1+: Japanese translation
Keep it concise and friendly.
"""
    else:
        system_prompt = """
You are a helpful AI assistant. 
When the user asks a question (starting with a hashtag), provide a clear and concise explanation in Japanese.
Immediately following the Japanese explanation, provide a natural Korean translation of that explanation.
Format:
Line 1+: Japanese explanation
[Separator]
Line 1+: Korean translation
Keep it concise and friendly.
"""

    response = client.chat.completions.create(
        model="gpt-5.1-chat-latest",
        messages=[
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": text}
        ]
    )
    return response.choices[0].message.content.strip()


def normalize_text(text):
    text = text.strip()
    text = re.sub(r'\s{2,}', ' ', text)
    return text

def get_cached_translation(normalized_text, source_lang, target_lang):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            'SELECT * FROM translation_cache WHERE original_text = ? AND source_lang = ? AND target_lang = ?',
            (normalized_text, source_lang, target_lang)
        ).fetchone()
        if row:
            conn.execute(
                "UPDATE translation_cache SET usage_count = usage_count + 1, updated_at = datetime('now','localtime') WHERE original_text = ?",
                (normalized_text,)
            )
            conn.commit()
            return row['translated_text'], row['pronunciation'], row['audio_target']
    return None

def save_translation_cache(normalized_text, source_lang, target_lang, translated_text, pronunciation, audio_target):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            INSERT INTO translation_cache (original_text, source_lang, target_lang, translated_text, pronunciation, audio_target, usage_count)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        ''', (normalized_text, source_lang, target_lang, translated_text, pronunciation, audio_target))
        conn.commit()


def translate_text(text, user_id):
    source_lang = detect_language(text)
    target_lang = '일본어' if source_lang == '한국어' else '한국어'
    
    is_single_line = len(text.splitlines()) == 1
    normalized_text = normalize_text(text) if is_single_line else text
    
    # 시간대별 일본어 인사말 예외 처리
    clean_korean = normalized_text.replace('.', '').replace('!', '').replace('?', '').replace('~', '').strip()
    if is_single_line and target_lang == '일본어' and clean_korean == '안녕하세요':
        from datetime import datetime
        current_hour = datetime.now().hour
        if 5 <= current_hour < 12:
            translated_text, pron_text, audio_target = 'おはようございます', '오하요-고자이마스', 'おはようございます'
        elif 12 <= current_hour < 18:
            translated_text, pron_text, audio_target = 'こんにちは', '콘니치와', 'こんにちは'
        else:
            translated_text, pron_text, audio_target = 'こんばんは', '콤방와', 'こんばんは'
        app.logger.info(f'시간대별 인사말 적용: {translated_text}')
    else:
        cached = get_cached_translation(normalized_text, source_lang, target_lang) if is_single_line else None
        
        if cached:
            translated_text, pron_text, audio_target = cached
            app.logger.info(f'DB Cache Hit: {normalized_text}')
        else:
            translated_text, pron_text, audio_target = get_translation_from_api(text, source_lang, target_lang)
            if is_single_line and translated_text:
                try:
                    save_translation_cache(normalized_text, source_lang, target_lang, translated_text, pron_text, audio_target)
                except Exception as e:
                    app.logger.error(f'Failed to save to translation_cache: {e}')
    
    settings = get_user_settings(user_id)
    if (is_single_line or settings.get('pronunciation', False)) and pron_text:
        display_text = f'{translated_text}\n{pron_text}'
    else:
        display_text = translated_text
        
    app.logger.info(f'번역 결과: {display_text}')
    return (display_text, audio_target)



def detect_language(text):
    # 한글과 일본어(히라가나/가타카나/한자) 글자 수 비교
    kr_count = len(re.findall(r"[\uac00-\ud7a3]", text))
    jp_count = len(re.findall(r"[\u3040-\u30ff\u4e00-\u9faf]", text))
    
    if kr_count >= jp_count and kr_count > 0:
        return '한국어'
    else:
        return '일본어'

    # /callback 및 웹 라우팅들은 routes.py로 분리되었습니다.

# 메시지 이벤트 핸들러 추가
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    import unicodedata
    import re
    user_input = unicodedata.normalize('NFC', event.message.text).strip()
    user_input = re.sub('[ \\t\\u3000]+', ' ', user_input)
    user_input = user_input.replace('＃', '#')
    user_id = event.source.user_id
    app.logger.info(f"Received message from {user_id}: {user_input!r}  hex={user_input.encode('utf-8').hex()}")
    setting_commands = {'#발음': ('pronunciation', '発音表示 / 발음 표시'), '#은성': ('voice', '音声機能 / 음성 기능'), '#통역': ('translation', '通訳機能 / 통역 기능')}
    for cmd, (key, label) in setting_commands.items():
        if user_input.startswith(cmd):
            arg = user_input[len(cmd):].strip().lower()
            settings = get_user_settings(user_id)
            if arg == 'on':
                if settings[key]:
                    reply_text = f'{label}: 이미 ON ✅ / すでにON입니다'
                else:
                    set_user_setting(user_id, key, True)
                    reply_text = f'{label}: ON ✅'
            elif arg == 'off':
                if not settings[key]:
                    reply_text = f'{label}: 이미 OFF ❌ / すでにOFF입니다'
                else:
                    set_user_setting(user_id, key, False)
                    reply_text = f'{label}: OFF ❌'
            else:
                status = 'ON ✅' if settings[key] else 'OFF ❌'
                reply_text = f'{label}: 현재 {status}\n사용법: {cmd} on / {cmd} off'
            line_bot_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text=reply_text)]))
            return
    ai_triggers_kr = ['#인공지능']
    ai_triggers_jp = ['#じんこうちの우', '#人工知能']
    target_trigger_lang = None
    clean_input = user_input
    for trigger in ai_triggers_kr:
        if user_input.startswith(trigger):
            target_trigger_lang = 'KR'
            clean_input = user_input[len(trigger):].strip()
            break
    if not target_trigger_lang:
        for trigger in ai_triggers_jp:
            if user_input.startswith(trigger):
                target_trigger_lang = 'JP'
                clean_input = user_input[len(trigger):].strip()
                break
    if target_trigger_lang:
        if not clean_input:
            clean_input = '인공지능에 대해 설명해줘' if target_trigger_lang == 'KR' else '人工知能について説明して'
        try:
            ai_reply = get_ai_response(clean_input, target_trigger_lang)
            line_bot_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text=ai_reply)]))
        except Exception as e:
            app.logger.error(f'Error in AI mode: {e}')
            line_bot_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text='인공지능 모드 처리 중 오류가 발생했습니다.')]))
        return
    if user_input in ['#학습', '#がくしゅう', '#学習']:
        if not DIALOG_DATA:
            line_bot_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text='학습 데이터를 불러올 수 없습니다.')]))
            return
        sample_size = min(10, len(DIALOG_DATA))
        candidates = random.sample(DIALOG_DATA, sample_size)
        target = random.choice(candidates)
        all_pronunciations = [d['pronunciation'] for d in DIALOG_DATA if d['pronunciation'] != target['pronunciation']]
        distractors = random.sample(all_pronunciations, 2)
        choices = [target['pronunciation']] + distractors
        random.shuffle(choices)
        correct_idx = choices.index(target['pronunciation']) + 1
        user_quiz_state[user_id] = {'correct_answer': correct_idx}
        reply_text = f"{target['sentence']}\n"
        for i, choice in enumerate(choices, 1):
            reply_text += f'{i}. ({choice})\n'
        line_bot_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text=reply_text.strip())]))
        return
    if user_input == '#퀴즈':
        if not VERB_DATA:
            line_bot_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text='퀴즈 데이터를 불러올 수 없습니다.')]))
            return
        target = random.choice(VERB_DATA)
        all_answers = [v['answer'] for v in VERB_DATA if v['answer'] != target['answer']]
        distractors = random.sample(all_answers, 2)
        choices = [target['answer']] + distractors
        random.shuffle(choices)
        correct_idx = choices.index(target['answer']) + 1
        user_quiz_state[user_id] = {'correct_answer': correct_idx}
        reply_text = f"{target['word']}\n"
        for i, choice in enumerate(choices, 1):
            reply_text += f'{i}. {choice}\n'
        line_bot_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text=reply_text.strip())]))
        return
    if user_id in user_quiz_state and user_input.isdigit():
        correct_answer = user_quiz_state[user_id]['correct_answer']
        if int(user_input) == correct_answer:
            reply = 'せいかい(正解) 정답!!'
        else:
            reply = 'ごとう(誤答) 오답!!'
        user_quiz_state.pop(user_id, None)
        line_bot_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text=reply)]))
        return
    if user_input.startswith('#그림'):
        word = user_input[3:].strip()
        if not word:
            line_bot_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text='사용법: #그림 고양이\n단어를 입력해주세요!')]))
            return
        try:
            cached_filename = f'{word}.png'
            cached_filepath = os.path.join('static', cached_filename)
            if os.path.exists(cached_filepath):
                app.logger.info(f'캐시된 이미지 사용: {cached_filename}')
                filename = cached_filename
            else:
                try:
                    line_bot_api.show_loading_animation(ShowLoadingAnimationRequest(chat_id=user_id, loading_seconds=30))
                    app.logger.info('로딩 애니메이션 표시 성공')
                except Exception as loading_err:
                    app.logger.warning(f'로딩 애니메이션 표시 실패 (무시): {loading_err}')
                filename = generate_picture_card(word)
            image_url = f'{request.host_url}static/{quote(filename)}'
            if image_url.startswith('http://'):
                image_url = image_url.replace('http://', 'https://', 1)
            line_bot_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[ImageMessage(original_content_url=image_url, preview_image_url=image_url)]))
        except Exception as e:
            app.logger.error(f'그림 카드 생성 오류: {e}')
            line_bot_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text='그림 생성 중 오류가 발생했어요. 😢')]))
        return
    jp_picture_triggers = ['#図', '#はかる']
    jp_picture_word = None
    for trigger in jp_picture_triggers:
        if user_input.startswith(trigger):
            jp_picture_word = user_input[len(trigger):].strip()
            break
    if jp_picture_word is not None:
        if not jp_picture_word:
            line_bot_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text='使い方: #図 くじら\n単語を入力してください！')]))
            return
        try:
            cached_filename = f'{jp_picture_word}.png'
            cached_filepath = os.path.join('static', cached_filename)
            if os.path.exists(cached_filepath):
                app.logger.info(f'캐시된 이미지 사용(JP): {cached_filename}')
                filename = cached_filename
            else:
                try:
                    line_bot_api.show_loading_animation(ShowLoadingAnimationRequest(chat_id=user_id, loading_seconds=30))
                except Exception as loading_err:
                    app.logger.warning(f'로딩 애니메이션 표시 실패 (무시): {loading_err}')
                filename = generate_picture_card_jp(jp_picture_word)
            image_url = f'{request.host_url}static/{quote(filename)}'
            if image_url.startswith('http://'):
                image_url = image_url.replace('http://', 'https://', 1)
            line_bot_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[ImageMessage(original_content_url=image_url, preview_image_url=image_url)]))
        except Exception as e:
            app.logger.error(f'그림 카드(JP) 생성 오류: {e}')
            line_bot_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text='画像生成中にエラーが発生しました。😢')]))
        return
    if re.fullmatch('[a-zA-Z\\s]+', user_input):
        app.logger.info('Input is English only.')
        return
    if user_input == '#예약':
        buttons_template = ButtonsTemplate(text='어떤 플랜으로 예약하시겠어요?', actions=[URIAction(label='베이직 예약하기', uri='https://liff.line.me/2009473953-5Fzd6NXy?plan=basic'), URIAction(label='프리미엄 예약하기', uri='https://liff.line.me/2009473953-5Fzd6NXy?plan=premium')])
        template_message = TemplateMessage(alt_text='예약 안내', template=buttons_template)
        line_bot_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[template_message]))
        return
    settings = get_user_settings(user_id)
    if not settings['translation']:
        return
    try:
        display_text, audio_target = translate_text(user_input, user_id)
        messages = [TextMessage(text=display_text)]
        if audio_target and settings['voice']:
            try:
                detected_source = detect_language(user_input)
                voice_choice = 'nova' if detected_source == '한국어' else 'onyx'
                filename, duration_ms = generate_tts_audio(audio_target, voice=voice_choice)
                audio_url = f'{request.host_url}static/{filename}'
                if audio_url.startswith('http://'):
                    audio_url = audio_url.replace('http://', 'https://', 1)
                messages.append(AudioMessage(original_content_url=audio_url, duration=duration_ms))
            except Exception as e:
                app.logger.error(f'TTS 생성 중 오류: {e}')
        reply_message_request = ReplyMessageRequest(reply_token=event.reply_token, messages=messages)
        line_bot_api.reply_message(reply_message_request)
    except Exception as e:
        app.logger.exception(f'Error during translation occurred: {e}')
        reply_message_request = ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text='번역 중 오류가 발생 했어요.')])
        line_bot_api.reply_message(reply_message_request)

# DB 초기화
init_db()

# 외부로 분리된 앱 라우트들을 초기화합니다.
from routes import init_routes
init_routes(app, handler)

if __name__ == "__main__":
    # 443 포트로 HTTPS 서비스 (리눅스나 맥에서는 sudo python3 app.py 필요)
    cert_path = os.path.join(os.path.dirname(__file__), "cert2", "cert.pem")
    key_path = os.path.join(os.path.dirname(__file__), "cert2", "key.pem")
    app.run(host="0.0.0.0", port=443, ssl_context=(cert_path, key_path), debug=False)
