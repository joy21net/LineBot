#!/usr/bin/env python3
"""Transform edu.html to support Korean/Japanese language switching."""

import re

# Read the file
with open('templates/edu.html', 'r', encoding='utf-8') as f:
    content = f.read()

# ============================================================
# STEP 1: Replace Google Translate mechanism with custom setLang
# ============================================================

old_translate = '''<!-- GOOGLE TRANSLATE WIDGET & TOGGLE -->
<div class="lang-toggle-container notranslate">
  <button id="lang-ko" class="lang-btn active" onclick="changeLanguage('ko')">한국어</button>
  <button id="lang-ja" class="lang-btn" onclick="changeLanguage('ja')">日本語</button>
</div>
<div id="google_translate_element" style="display:none;"></div>
<script type="text/javascript">
  function googleTranslateElementInit() {
    new google.translate.TranslateElement({
      pageLanguage: 'ko',
      includedLanguages: 'ko,ja',
      autoDisplay: false,
      layout: google.translate.TranslateElement.InlineLayout.SIMPLE
    }, 'google_translate_element');
  }

  function changeLanguage(langCode) {
    document.querySelectorAll('.lang-btn').forEach(btn => btn.classList.remove('active'));
    document.getElementById(`lang-${langCode}`).classList.add('active');
    
    let attempts = 0;
    function triggerChange() {
      var selectField = document.querySelector(".goog-te-combo");
      if (selectField) {
        selectField.value = langCode;
        selectField.dispatchEvent(new Event('change'));
      } else if (attempts < 10) {
        attempts++;
        setTimeout(triggerChange, 500);
      }
    }
    triggerChange();
  }
</script>
<script type="text/javascript" src="https://translate.google.com/translate_a/element.js?cb=googleTranslateElementInit"></script>'''

new_translate = '''<!-- LANGUAGE TOGGLE -->
<div class="lang-toggle-container">
  <button id="lang-ko" class="lang-btn active" onclick="setLang('ko')">한국어</button>
  <button id="lang-ja" class="lang-btn" onclick="setLang('ja')">日本語</button>
</div>'''

content = content.replace(old_translate, new_translate)

# Also remove Google Translate CSS overrides
old_css = '''  /* ===== GOOGLE TRANSLATE OVERRIDES ===== */
  body { top: 0 !important; }
  .goog-te-banner-frame { display: none !important; }
  .goog-tooltip { display: none !important; }
  .goog-text-highlight { background-color: transparent !important; box-shadow: none !important; }
  #goog-gt-tt, .goog-te-balloon-frame { display: none !important; }
  
  /* Language Toggle */'''

new_css = '''  /* Language Toggle */'''
content = content.replace(old_css, new_css)

old_css2 = '''  .skiptranslate.goog-te-gadget {
    display: none !important;
  }'''
content = content.replace(old_css2, '')

# ============================================================
# STEP 2: Translation dictionary - Korean -> Japanese
# ============================================================

translations = [
    # Slide 1: Title
    ('📋 기획안 · 2025', '📋 企画案 · 2025'),
    ('AI 언어', 'AI 言語'),
    ('교환 플랫폼', '交換プラットフォーム'),
    ('드라매치 + 듀오링고의 장점을 결합한', 'Dr.Match + Duolingoの長所を融合した'),
    ('AI 기반 맞춤형 언어 교환 학습 서비스', 'AIベースのカスタマイズ言語交換学習サービス'),
    ('#언어교환', '#言語交換'),
    ('#AI피드백', '#AIフィードバック'),
    ('#문화맥락변환', '#文化コンテキスト変換'),
    ('#원어민매칭', '#ネイティブマッチング'),
    ('#발음분석', '#発音分析'),
    
    # Slide 2: Problem definition
    ('// 01 · 문제 정의', '// 01 · 問題定義'),
    ('기존 서비스의 <span style="color:var(--primary)">한계</span>', '既存サービスの<span style="color:var(--primary)">限界</span>'),
    ('원어민 매칭만 있고 학습 보조 없음', 'ネイティブマッチングのみで学習サポートなし'),
    ('파트너와 연결은 됐지만 무슨 말을 해야 할지 몰라 어색하게 끝남', 'パートナーと繋がったが何を話せばいいかわからず気まずく終了'),
    ('→ Drmatch, Tandem 등', '→ Drmatch, Tandem等'),
    ('커리큘럼은 있지만 실전 회화 없음', 'カリキュラムはあるが実践会話なし'),
    ('체계적으로 공부하지만 실제 원어민과 대화할 기회가 없어 응용이 어려움', '体系的に学習するが実際にネイティブと会話する機会がなく応用が困難'),
    ('→ Duolingo, Busuu 등', '→ Duolingo, Busuu等'),
    ('발음 피드백의 부재', '発音フィードバックの欠如'),
    ('제대로 말해도 인식 못 하거나, 틀렸다는 것만 알 뿐 어떻게 틀렸는지 모름', '正しく話しても認識できなかったり、間違いだけわかり何が違うかわからない'),
    ('→ Duolingo 음성 인식 한계', '→ Duolingo音声認識の限界'),
    ('문화 맥락 번역 부재', '文化コンテキスト翻訳の欠如'),
    ('한국식 직역으로 일본어를 말하면 어색함. 문화적 뉘앙스 변환이 필요함', '韓国式直訳で日本語を話すと不自然。文化的ニュアンス変換が必要'),
    ('→ 일반 번역 앱의 한계', '→ 一般翻訳アプリの限界'),

    # Slide 3: Core concept
    ('// 02 · 핵심 개념', '// 02 · コアコンセプト'),
    ('두 앱의 <span style="color:var(--secondary)">최강 결합</span>', '2つのアプリの<span style="color:var(--secondary)">最強融合</span>'),
    ('언어 교환', '言語交換'),
    ('원어민 실시간 대화', 'ネイティブリアルタイム会話'),
    ('자연스러운 피드백', '自然なフィードバック'),
    ('체계적 학습', '体系的学習'),
    ('수준별 커리큘럼', 'レベル別カリキュラム'),
    ('진도 추적 & 복습', '進捗追跡＆復習'),
    ('최강 학습 효과', '最強学習効果'),
    ('실전 대화 × AI 피드백', '実践会話 × AIフィードバック'),
    ('문화 맥락 변환', '文化コンテキスト変換'),
    ('관계 형성 + 언어 습득', '関係構築 + 言語習得'),

    # Slide 4: Features
    ('// 03 · 핵심 기능', '// 03 · コア機能'),
    ('6가지 <span style="color:var(--accent)">핵심 기능</span>', '6つの<span style="color:var(--accent)">コア機能</span>'),
    ('레벨 테스트 & 학습 로드맵', 'レベルテスト＆学習ロードマップ'),
    ('듣기/읽기/말하기/쓰기 진단', 'リスニング/リーディング/スピーキング/ライティング診断'),
    ('AI 추천 학습 경로 자동 생성', 'AI推薦学習パス自動生成'),
    ('맞춤형 원어민 매칭', 'カスタマイズネイティブマッチング'),
    ('관심사 / 레벨 / 목적 기반', '興味/レベル/目的ベース'),
    ('1:1 또는 소규모 그룹', '1:1または少人数グループ'),
    ('미션형 커리큘럼', 'ミッション型カリキュラム'),
    ('"자기소개 3분" 등 실전 미션', '「自己紹介3分」等の実践ミッション'),
    ('AI 스크립트 자동 제안', 'AIスクリプト自動提案'),
    ('문화 맥락 변환 AI', '文化コンテキスト変換AI'),
    ('한국어 → 일본 문화식 자연 표현', '韓国語→日本文化式自然表現'),
    ('완곡/공손 표현 자동 제안', '婉曲/丁寧表現自動提案'),
    ('정밀 발음 분석', '精密発音分析'),
    ('자음/모음/억양 단위 분석', '子音/母音/抑揚単位分析'),
    ('구체적 개선 피드백 제공', '具体的改善フィードバック提供'),
    ('선택형 복습 시스템', '選択型復習システム'),
    ('대화 기반 퀴즈 자동 생성', '会話ベースクイズ自動生成'),
    ('SRS 반복 학습 스케줄러', 'SRS反復学習スケジューラー'),

    # Slide 5: Competition
    ('// 04 · 경쟁 분석', '// 04 · 競合分析'),
    ('경쟁사 대비 <span style="color:var(--secondary)">차별점</span>', '競合他社との<span style="color:var(--secondary)">差別化</span>'),
    ('>기능<', '>機能<'),
    ('>우리 앱<', '>当アプリ<'),
    ('>번역 앱<', '>翻訳アプリ<'),
    ('>원어민 실시간 매칭<', '>ネイティブリアルタイムマッチング<'),
    ('>체계적 커리큘럼<', '>体系的カリキュラム<'),
    ('>문화 맥락 변환<', '>文化コンテキスト変換<'),
    ('>정밀 발음 피드백<', '>精密発音フィードバック<'),
    ('>실전 대화 기반 복습<', '>実践会話ベース復習<'),
    ('>관계 형성 & 친구 만들기<', '>関係構築＆友達作り<'),

    # Slide 6: UX Flow
    ('// 05 · UX 설계', '// 05 · UX設計'),
    ('학습 <span style="color:var(--accent)">여정 흐름</span>', '学習<span style="color:var(--accent)">ジャーニーフロー</span>'),
    ('가입 &<br>레벨 테스트', '登録＆<br>レベルテスト'),
    ('수준별 진단', 'レベル別診断'),
    ('AI 학습<br>로드맵 생성', 'AI学習<br>ロードマップ生成'),
    ('맞춤형 경로', 'カスタマイズパス'),
    ('주제 사전<br>학습', 'テーマ事前<br>学習'),
    ('카드 & 선택형', 'カード＆選択式'),
    ('원어민과<br>실전 회화', 'ネイティブと<br>実践会話'),
    ('AI 실시간 개입', 'AIリアルタイム介入'),
    ('자동 피드백<br>& 복습 퀴즈', '自動フィードバック<br>＆復習クイズ'),
    ('대화 기반 학습', '会話ベース学習'),
    ('레벨업 &<br>친구 형성', 'レベルアップ＆<br>友達形成'),
    ('장기 관계 유지', '長期関係維持'),

    # Slide 7: AI Feedback
    ('// 06 · AI 실시간 개입', '// 06 · AIリアルタイム介入'),
    ('대화 중 <span style="color:var(--secondary)">자동 학습 전환</span>', '会話中<span style="color:var(--secondary)">自動学習切替</span>'),
    ('Yuki (일본인)', 'Yuki (日本人)'),
    ('● 온라인', '● オンライン'),
    ('Yuki가 말함:', 'Yukiの発言:'),
    ('🤖 AI 번역:', '🤖 AI翻訳:'),
    ('직역: "어제 몸 상태가 조금 안 좋아서 회사를 쉬었습니다"', '直訳:「昨日ちょっと体調が悪くて会社を休みました」'),
    ('💡 쉬운 표현: "어제 아파서 회사에 못 갔어요"', '💡 簡単表現:「昨日具合が悪くて会社に行けませんでした」'),
    ('// 자동 퀴즈 생성', '// 自動クイズ生成'),
    ('"어제 아파서 회사에 못 갔어요"의<br>자연스러운 일본어는?', '「昨日具合が悪くて会社に行けませんでした」の<br>自然な日本語は？'),

    # Slide 8: Pronunciation
    ('// 07 · 발음 분석 시스템', '// 07 · 発音分析システム'),
    ('Duolingo를 <span style="color:var(--primary)">넘는</span> 정밀 피드백', 'Duolingoを<span style="color:var(--primary)">超える</span>精密フィードバック'),
    ('❌ 기존 앱 (Duolingo)', '❌ 既存アプリ (Duolingo)'),
    ('다시 시도하세요', 'もう一度お試しください'),
    ('무엇이 틀렸는지 알 수 없음', '何が間違っているかわからない'),
    ('발음 개선 방향 제시 없음', '発音改善の方向性提示なし'),
    ('인식률 낮아 좌절감 증가', '認識率が低く挫折感増加'),
    ('✅ 우리 앱 정밀 분석', '✅ 当アプリ精密分析'),
    ('"あ"가 너무 짧습니다 — 길게 발음하세요', '「あ」が短すぎます — 長く発音してください'),
    ('"な"에 힘이 너무 들어갔습니다', '「な」に力が入りすぎています'),
    ('"た" 발음은 자연스럽습니다!', '「た」の発音は自然です！'),

    # Slide 9: Revenue
    ('// 08 · 비즈니스 모델', '// 08 · ビジネスモデル'),
    ('다양한 <span style="color:var(--accent)">수익 구조</span>', '多様な<span style="color:var(--accent)">収益構造</span>'),
    ('프리미엄 구독', 'プレミアムサブスクリプション'),
    ('무제한 AI 피드백, 무제한 매칭, 심화 커리큘럼 이용권', '無制限AIフィードバック、無制限マッチング、上級カリキュラム利用権'),
    ('B2C · 월정액', 'B2C · 月額定額'),
    ('AI 분석 리포트', 'AI分析レポート'),
    ('발음 상세 분석, 문화 표현 레포트, 학습 패턴 인사이트', '発音詳細分析、文化表現レポート、学習パターンインサイト'),
    ('AI 프리미엄', 'AIプレミアム'),
    ('전문 강사 AI 세션', '専門講師AIセッション'),
    ('특정 분야(비즈니스/여행/드라마) 전문 AI 강사와 집중 세션', '特定分野（ビジネス/旅行/ドラマ）専門AI講師との集中セッション'),
    ('AI 강사', 'AI講師'),
    ('기업 라이선스', '企業ライセンス'),
    ('일본 진출 기업, 교환학생 프로그램 등 B2B 단체 계약', '日本進出企業、交換留学プログラム等B2B団体契約'),
    ('학교/학원 연계', '学校/塾連携'),
    ('어학원, 대학교 교양 과목 연계 학습 도구 공급', '語学学校、大学教養科目連携学習ツール供給'),
    ('교육기관', '教育機関'),
    ('회화 세션 포인트', '会話セッションポイント'),
    ('세션 추가 구매, 우선 매칭 포인트, 특별 파트너 연결권', 'セッション追加購入、優先マッチングポイント、特別パートナー接続権'),
    ('In-App 결제', 'In-App決済'),

    # Slide 10: AI Teacher
    ('🤖 AI TEACHER · 확장 아이디어', '🤖 AI TEACHER · 拡張アイデア'),
    ('>디지털<', '>デジタル<'),
    ('>선생님<', '>先生<'),
    ('연예인처럼 매력적인 AI 아바타가', '芸能人のように魅力的なAIアバターが'),
    ('반 프로그램 + 반 AI', '半プログラム + 半AI'),
    ('양방향 실시간 학습 튜터', '双方向リアルタイム学習チューター'),
    ('#디지털휴먼', '#デジタルヒューマン'),
    ('#양방향대화', '#双方向対話'),
    ('#게임형학습', '#ゲーム型学習'),
    ('#가드레일AI', '#ガードレールAI'),
    ('#70ms반응속도', '#70ms反応速度'),

    # Slide 11: Tech structure
    ('// 09 · AI 선생님 기술 구조', '// 09 · AI先生技術構造'),
    ('<span style="color:var(--secondary)">4가지 핵심 기술</span>의 결합', '<span style="color:var(--secondary)">4つのコア技術</span>の融合'),
    ('시각 — 디지털 휴먼 아바타', '視覚 — デジタルヒューマンアバター'),
    ('연예인처럼 매력적이고 자연스러운 AI 아바타. 텍스트를 입력하면 입 모양과 표정이 실시간으로 자연스럽게 움직임.', '芸能人のように魅力的で自然なAIアバター。テキストを入力すると口の形や表情がリアルタイムで自然に動く。'),
    ('두뇌 — LLM + RAG', '頭脳 — LLM + RAG'),
    ('커리큘럼 문서 안에서만 대화하도록 RAG로 제한. 엉뚱한 질문도 받아주되 2문장 내로 학습으로 자연스럽게 유도.', 'カリキュラム文書内でのみ会話するようRAGで制限。突飛な質問も受け入れつつ2文以内で学習に自然に誘導。'),
    ('청각 — 감정 TTS & STT', '聴覚 — 感情TTS＆STT'),
    ('아이의 불분명한 발음도 인식하는 고성능 음성인식. 딱딱한 기계음이 아닌 감정이 담긴 목소리로 칭찬과 격려.', '子供の不明瞭な発音も認識する高性能音声認識。硬い機械音ではなく感情のこもった声で褒めて励ます。'),
    ('트리거 — 프로그램 개입 이벤트', 'トリガー — プログラム介入イベント'),
    ('AI가 "게임 해볼까?" 하는 순간, 앱 화면에 플래시 카드·퀴즈 UI가 팝업. 커리큘럼과 AI 대화를 실시간으로 동기화.', 'AIが「ゲームしてみよう？」と言う瞬間、アプリ画面にフラッシュカード・クイズUIがポップアップ。カリキュラムとAI会話をリアルタイムで同期化。'),

    # Slide 12: Game content
    ('// 10 · 게임형 학습 콘텐츠', '// 10 · ゲーム型学習コンテンツ'),
    ('눈으로 보고 손으로 하는 <span style="color:var(--accent)">학습 게임</span>', '目で見て手で触れる<span style="color:var(--accent)">学習ゲーム</span>'),
    ('그림 카드 퀴즈', '絵カードクイズ'),
    ('AI 선생님이 그림 카드를 보여주며 힌트를 줌. "이것이 뭐였지?" — 매번 다른 표현으로 자연스러운 칭찬/격려.', 'AI先生が絵カードを見せてヒントを出す。「これは何だっけ？」— 毎回違う表現で自然な褒め/励まし。'),
    ('✓ 잘했어요! 고양이 맞아요~', '✓ よくできました！猫で正解です〜'),
    ('상황별 롤플레이', '場面別ロールプレイ'),
    ('카페 주문·여행·쇼핑 등 실생활 시나리오. AI 선생님이 점원·친구 역할로 자연스러운 대화 유도. 공백의 공포 해결.', 'カフェ注文・旅行・ショッピング等の実生活シナリオ。AI先生が店員・友達役で自然な会話を誘導。沈黙の恐怖を解消。'),
    ('🧑‍🏫 커피 한 잔 주세요?', '🧑‍🏫 コーヒー1杯ください？'),
    ('아, 거의 맞아요! 💡', 'あ、ほぼ正解です！💡'),
    ('실시간 성장 시각화', 'リアルタイム成長ビジュアライゼーション'),
    ('AI 교정 유형을 문법·단어·자연스러움·문화로 분류해 시각화. "성장하는 느낌"이 학습 동기를 지속적으로 높임.', 'AI校正タイプを文法・単語・自然さ・文化に分類して可視化。「成長する実感」が学習モチベーションを持続的に向上。'),
    ('>문법<', '>文法<'),
    ('>발음<', '>発音<'),
    ('>문화<', '>文化<'),

    # Slide 13: Latency
    ('// 11 · 핵심 기술 과제', '// 11 · コア技術課題'),
    ('초저지연 <span style="color:var(--secondary)">실시간 반응</span> 시스템', '超低遅延<span style="color:var(--secondary)">リアルタイム反応</span>システム'),
    ('ms 이내 목표 응답', 'ms以内目標応答'),
    ('일반 챗봇', '一般チャットボット'),
    ('기존 음성AI', '既存音声AI'),
    ('우리 목표', '当社目標'),
    ('아이가 말을 끝낸 후 2~3초 이상 딜레이 발생 시', '子供が話し終えてから2〜3秒以上の遅延が発生すると'),
    ('집중력이 깨져 학습 효과 급감 — 1초 이내 최적화가 핵심', '集中力が途切れ学習効果が急減 — 1秒以内の最適化が核心'),
    ('음성 입력', '音声入力'),
    ('실시간 음성→텍스트', 'リアルタイム音声→テキスト'),
    ('AI 응답 생성', 'AI応答生成'),
    ('감정 음성 합성', '感情音声合成'),
    ('아바타 립싱크 렌더링', 'アバターリップシンクレンダリング'),
    ('화면 출력 + 게임 트리거', '画面出力 + ゲームトリガー'),

    # Slide 14: Conclusion
    ('// CONCLUSION · 결론', '// CONCLUSION · 結論'),
    ('실전 대화가', '実践会話が'),
    ('곧 <span>교재</span>가 된다', 'そのまま<span>教材</span>になる'),
    ('시장 차별화', '市場差別化'),
    ('학습 효과', '学習効果'),
    ('사용자 몰입', 'ユーザー没入'),
    ('구현 가능성', '実現可能性'),
    ('그 나라 언어를 배우려면 연애를 해라', 'その国の言語を学びたければ恋愛をしろ'),

    # Navigation
    ('← 이전', '← 前へ'),
    ('다음 →', '次へ →'),
]

# ============================================================
# STEP 3: Wrap text in data-ko/data-ja spans
# ============================================================

# For each translation pair, wrap the Korean text with data attributes
# We need to be careful not to replace inside HTML attributes
for ko, ja in translations:
    # Handle cases where the Korean text contains HTML tags (like <span>, <br>)
    # These are typically innerHTML of elements
    
    # Escape for use in attribute (double quotes -> &quot;)
    ko_attr = ko.replace('"', '&quot;')
    ja_attr = ja.replace('"', '&quot;')
    
    # Check if it's a tag-boundary replacement (e.g., ">text<")
    if ko.startswith('>') and ko.endswith('<'):
        inner_ko = ko[1:-1]
        inner_ja = ja[1:-1]
        old = f'>{inner_ko}<'
        new = f'><span data-ko="{inner_ko}" data-ja="{inner_ja}"></span><'
        content = content.replace(old, new, 1)  # Replace first occurrence only
    else:
        # Regular text replacement - wrap in span with data attributes
        replacement = f'<span data-ko="{ko_attr}" data-ja="{ja_attr}"></span>'
        content = content.replace(ko, replacement, 1)

# Special handling for title elements that have mixed content
# Slide 1 title "한국" and "일본" are inside span tags with classes
content = content.replace(
    '<span class="kr">한국</span>',
    '<span class="kr"><span data-ko="韓国" data-ja="韓国">韓国</span></span>'
)
# Actually, let me fix the Korean text display. The data-ko/data-ja pattern in linbot_v5 
# shows Korean text by default via the applyLang on init.
# So elements should start empty and get filled by applyLang().

# Actually the pattern in linbot_v5 is: <span data-ko="Korean" data-ja="Japanese"></span>
# The span starts empty and gets filled by applyLang() on init.
# But that means on first load nothing would show until JS runs.
# To avoid a flash of empty content, let's put the Korean text as default content.

# Let me fix the replacements - the spans should have Korean as default inner text
# Re-read and fix
with open('templates/edu.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Apply step 1 again
content = content.replace(old_translate, new_translate)
content = content.replace(old_css, new_css)
content = content.replace(old_css2, '')

# Now apply translations properly - Korean text as default inner content
for ko, ja in translations:
    ko_attr = ko.replace('"', '&quot;')
    ja_attr = ja.replace('"', '&quot;')
    
    if ko.startswith('>') and ko.endswith('<'):
        inner_ko = ko[1:-1]
        inner_ja = ja[1:-1]
        old_text = f'>{inner_ko}<'
        new_text = f'><span data-ko="{inner_ko}" data-ja="{inner_ja}">{inner_ko}</span><'
        content = content.replace(old_text, new_text, 1)
    else:
        replacement = f'<span data-ko="{ko_attr}" data-ja="{ja_attr}">{ko}</span>'
        count = content.count(ko)
        if count >= 1:
            content = content.replace(ko, replacement, 1)

# ============================================================
# STEP 4: Add setLang/applyLang functions to the script section
# ============================================================

setlang_code = '''
  // Language switching
  let lang = 'ko';
  
  function setLang(l) {
    lang = l;
    document.querySelectorAll('.lang-btn').forEach(b => b.classList.toggle('active', 
      (l === 'ko' && b.textContent.trim() === '한국어') || (l === 'ja' && b.textContent.trim() === '日本語')
    ));
    applyLang();
  }

  function applyLang() {
    document.querySelectorAll('[data-ko][data-ja]').forEach(el => {
      const txt = el.getAttribute('data-' + lang);
      if (txt !== null) el.innerHTML = txt;
    });
  }

  // Apply language on init
  applyLang();
'''

# Insert before "// Init" in the script
content = content.replace(
    '  // Init\n  updateNav();\n  triggerAnimations(1);',
    setlang_code + '\n  // Init\n  updateNav();\n  triggerAnimations(1);'
)

# ============================================================
# STEP 5: Write the modified file
# ============================================================

with open('templates/edu.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ edu.html has been transformed with Korean/Japanese language switching!")
print(f"   Total translation pairs applied: {len(translations)}")
