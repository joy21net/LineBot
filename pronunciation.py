import re
import pykakasi
import num2words
from jamo import h2j, j2hcj

def japanese_to_korean_pronunciation(japanese_text):
    # 히라가나, 가타카나 매핑표 (기본)
    kana_map = {
        'あ': '아', 'い': '이', 'う': '우', 'え': '에', 'お': '오',
        'か': '카', 'き': '키', 'く': '쿠', 'け': '케', 'こ': '코',
        'が': '가', 'ぎ': '기', 'ぐ': '구', 'げ': '게', 'ご': '고',
        'さ': '사', 'し': '시', 'す': '스', 'せ': '세', 'そ': '소',
        'ざ': '자', 'じ': '지', 'ず': '즈', 'ぜ': '제', 'ぞ': '조',
        'た': '타', 'ち': '치', 'つ': '츠', 'て': '테', 'と': '토',
        'だ': '다', 'ぢ': '지', 'づ': '즈', 'で': '데', 'ど': '도',
        'な': '나', 'に': '니', 'ぬ': '누', 'ね': '네', 'の': '노',
        'は': '하', 'ひ': '히', 'ふ': '후', 'へ': '헤', 'ほ': '호',
        'ば': '바', 'び': '비', 'ぶ': '부', 'べ': '베', 'ぼ': '보',
        'ぱ': '파', 'ぴ': '피', 'ぷ': '푸', 'ぺ': '페', 'ぽ': '포',
        'ま': '마', 'み': '미', 'む': '무', 'め': '메', 'も': '모',
        'や': '야', 'ゆ': '유', 'よ': '요',
        'ら': '라', 'り': '리', 'る': '루', 'れ': '레', 'ろ': '로',
        'わ': '와', 'を': '오', 'ん': '응',
        'ア': '아', 'イ': '이', 'ウ': '우', 'エ': '에', 'オ': '오',
        'カ': '카', 'キ': '키', 'ク': '쿠', 'ケ': '케', 'コ': '코',
        'ガ': '가', 'ギ': '기', 'グ': '구', 'ゲ': '게', 'ゴ': '고',
        'サ': '사', 'シ': '시', 'ス': '스', 'セ': '세', 'ソ': '소',
        'ザ': '자', 'ジ': '지', 'ズ': '즈', 'ゼ': '제', 'ゾ': '조',
        'タ': '타', 'チ': '치', 'ツ': '츠', 'テ': '테', 'ト': '토',
        'ダ': '다', 'ヂ': '지', 'ヅ': '즈', 'デ': '데', 'ド': '도',
        'ナ': '나', 'ニ': '니', 'ヌ': '누', 'ネ': '네', 'ノ': '노',
        'ハ': '하', 'ヒ': '히', 'フ': '후', 'ヘ': '헤', 'ホ': '호',
        'バ': '바', 'ビ': '비', 'ブ': '부', 'ベ': '베', 'ボ': '보',
        'パ': '파', 'ピ': '피', 'プ': '푸', 'ペ': '페', 'ポ': '포',
        'マ': '마', 'ミ': '미', 'ム': '무', 'メ': '메', 'モ': '모',
        'ヤ': '야', 'ユ': '유', 'ヨ': '요',
        'ラ': '라', 'リ': '리', 'ル': '루', 'レ': '레', 'ロ': '로',
        'ワ': '와', 'ヲ': '오', 'ン': '응',
        'きゃ': '캬', 'きゅ': '큐', 'きょ': '쿄',
        'ぎゃ': '갸', 'ぎゅ': '규', 'ぎょ': '교',
        'しゃ': '샤', 'しゅ': '슈', 'しょ': '쇼',
        'じゃ': '자', 'じゅ': '주', 'じょ': '조',
        'ちゃ': '차', 'ちゅ': '추', 'ちょ': '초',
        'にゃ': '냐', 'にゅ': '뉴', 'にょ': '뇨',
        'ひゃ': '햐', 'ひゅ': '휴', 'ひょ': '효',
        'びゃ': '뱌', 'びゅ': '뷰', 'びょ': ' হিন্দুদের',
        'ぴゃ': '퍄', 'ぴゅ': '퓨', 'ぴょ': '표',
        'みゃ': '먀', 'みゅ': '뮤', 'みょ': '묘',
        'りゃ': '랴', 'りゅ': '류', 'りょ': '료',
        'キャ': '캬', 'キュ': '큐', 'キョ': '쿄',
        'ギャ': '갸', 'ギュ': '규', 'ギョ': '교',
        'シャ': '샤', 'シュ': '슈', 'ショ': '쇼',
        'ジャ': '자', 'ジュ': '주', 'ジョ': '조',
        'チャ': '차', 'チュ': '추', 'チョ': '초',
        'ニャ': '냐', 'ニュ': '뉴', 'ニョ': '뇨',
        'ヒャ': '햐', 'ヒュ': '휴', 'ヒョ': '효',
        'ビャ': '뱌', 'ビュ': '뷰', 'ビョ': '뵤',
        'ピャ': '퍄', 'ピュ': '퓨', 'ピョ': '표',
        'ミャ': '먀', 'ミュ': '뮤', 'ミョ': '묘',
        'リャ': '랴', 'リュ': '류', 'リョ': '료',
        'ー': '', 'っ': 'ㅅ', 'ッ': 'ㅅ' # 장음 생략, 촉음 받침 처리
    }
    
    # 예외 (기본 치환)
    exceptions = {
        'よくやったね': '요쿠얏타네'
    }

    # 연속된 숫자(Arabic)를 일본어 읽기로 변환 (예: 123 -> 百二十三)
    # pykakasi가 한자를 가타카나로 바꿔주므로 한자 표기로 변경하는 것이 깔끔함
    def replace_number_with_words(match):
        num_str = match.group(0)
        try:
            return num2words.num2words(int(num_str), lang='ja')
        except:
            return num_str

    japanese_text = re.sub(r'\d+', replace_number_with_words, japanese_text)

    # pykakasi를 사용하여 한자/히라가나를 모두 가타카나로 변환
    kks = pykakasi.kakasi()
    conv_result = kks.convert(japanese_text)
    
    # 변환된 가타카나 문자열 생성 (한자 -> 카타카나)
    kana_text: str = str("".join([item['kana'] for item in conv_result]))

    result: list[str] = []
    i = 0
    while i < len(kana_text):
        char = kana_text[i]
        
        # 촉음(っ/ッ) 처리 -> 뒤에 오는 글자의 초성에 따라 받침 결정
        if char == 'っ' or char == 'ッ':
            if i + 1 < len(kana_text):
                next_char = kana_text[i+1]
                # 요음 처리까지 감안하여 2글자/1글자 매칭 확인
                next_sound = ''
                if i + 2 < len(kana_text):
                    two_chars = kana_text[i+1] + kana_text[i+2]
                    if two_chars in kana_map:
                        next_sound = kana_map[two_chars]
                    elif next_char in kana_map:
                        next_sound = kana_map[next_char]
                elif next_char in kana_map:
                    next_sound = kana_map[next_char]
                
                # 다음 발음의 첫 글자(초성)에 따라 받침 결정 (간단한 룰)
                # 사, 시, 스, 세, 소, 자, 지... -> ㅅ 받침
                # 타, 치, 츠, 테, 토, 다, 지... -> ㅅ 받침
                # 카, 키, 쿠, 케, 코, 가, 기... -> ㄱ 받침
                # 파, 피, 푸, 페, 포, 바, 비... -> ㅂ 받침
                if next_sound:
                    first_korean_char = next_sound[0]
                    jamo_str = j2hcj(h2j(first_korean_char))
                    cho = jamo_str[0] if len(jamo_str) > 0 else ''
                    
                    if cho in ['ㅋ', 'ㄲ', 'ㄱ']:
                        result.append('ㄱ')
                    elif cho in ['ㅍ', 'ㅃ', 'ㅂ']:
                        result.append('ㅂ')
                    else: # ㅌ, ㄸ, ㄷ, ㅅ, ㅆ, ㅊ, ㅉ, ㅈ
                        result.append('ㅅ')
                else:
                    result.append('ㅅ') # 기본값
            else:
                 result.append('ㅅ') # 맨 끝에 올 경우
            i += 1
            continue

        # 작은 ャ, ュ, ョ, ゃ, ゅ, ょ 예외 처리 (앞 글자와 결합해야 하는데 사전(kana_map)에 없는 패턴 대비)
        # 하지만 이미 kana_map에 きゃ(캬) 등 2글자 조합이 다 들어있으므로, 2글자 매칭을 우선 확인합니다.

        # 2글자 매칭 (요음: きゃ, キャ 등)
        if i < len(kana_text) - 1:
            two_chars = kana_text[i] + kana_text[i+1]
            if two_chars in kana_map:
                char_korean = kana_map[two_chars]
                
                # 이전 글자가 촉음으로 인해 단독 자음(ㄱ, ㅂ, ㅅ) 형태라면 앞 글자의 받침으로 합치기
                if result and result[-1] in ['ㄱ', 'ㅂ', 'ㅅ']:
                    jong = result.pop()
                    if result:
                        prev_char = result[-1]
                        # 앞 글자에 받침 합성 (jamo 라이브러리 활용)
                        prev_jamo = j2hcj(h2j(prev_char))
                        if len(prev_jamo) == 2: # 초, 중성만 있는 상태에서 합침
                            # 한국어 유니코드 조립 (안전한 방식)
                            try:
                                cho_idx = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ'].index(prev_jamo[0])
                                jung_idx = ['ㅏ', 'ㅐ', 'ㅑ', 'ㅒ', 'ㅓ', 'ㅔ', 'ㅕ', 'ㅖ', 'ㅗ', 'ㅘ', 'ㅙ', 'ㅚ', 'ㅛ', 'ㅜ', 'ㅝ', 'ㅞ', 'ㅟ', 'ㅠ', 'ㅡ', 'ㅢ', 'ㅣ'].index(prev_jamo[1])
                                jong_idx = ['', 'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ', 'ㄻ', 'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ'].index(jong)
                                combined = chr(0xAC00 + (cho_idx * 21 * 28) + (jung_idx * 28) + jong_idx)
                                result[-1] = combined
                            except:
                                result.append(jong)
                        else:
                            result.append(jong)
                
                result.append(char_korean)
                i += 2
                continue
                
        # 1글자 매칭
        if char in kana_map:
            char_korean = kana_map[char]
            
            # 장음 기호 처리 앞 모음 연장. 장음은 한국어 표기법상 생략하므로 무시
            if result and result[-1] in ['ㄱ', 'ㅂ', 'ㅅ']:
                jong = result.pop()
                if result:
                    prev_char = result[-1]
                    prev_jamo = j2hcj(h2j(prev_char))
                    if len(prev_jamo) == 2:
                        try:
                            cho_idx = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ'].index(prev_jamo[0])
                            jung_idx = ['ㅏ', 'ㅐ', 'ㅑ', 'ㅒ', 'ㅓ', 'ㅔ', 'ㅕ', 'ㅖ', 'ㅗ', 'ㅘ', 'ㅙ', 'ㅚ', 'ㅛ', 'ㅜ', 'ㅝ', 'ㅞ', 'ㅟ', 'ㅠ', 'ㅡ', 'ㅢ', 'ㅣ'].index(prev_jamo[1])
                            jong_idx = ['', 'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ', 'ㄻ', 'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ'].index(jong)
                            combined = chr(0xAC00 + (cho_idx * 21 * 28) + (jung_idx * 28) + jong_idx)
                            result[-1] = combined
                        except:
                           result.append(jong)
                    else:
                        result.append(jong)

            result.append(char_korean)
            i += 1
        elif '一' <= char <= '龥':
            result.append(str(char))
            i += 1
        else:
            result.append(str(char))
            i += 1

    return "".join(result)

