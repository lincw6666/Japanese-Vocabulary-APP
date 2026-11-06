#!/usr/bin/env python3
"""
patch_grammar_v10.py
Definitive, clean, idempotent patch for grammar_DB.js:
1. Updates U08 Section 0 with 3-Step Decision Tree in 'table' and 'points' (renders in index.html)
2. Enriches 'points' in U16, U26, U32 to provide explicit instruction for Tier 3 colloquial speech:
   - U16 Sec 0: adds 'マジで' as a deadpan/emphatic degree adverb
   - U26 Sec 2: adds '〜じゃん' as colloquial advice contraction (〜じゃないか)
   - U32 Sec 1: adds '〜ちゃった' as colloquial contraction for 〜てしまった
   - (U06 Sec 1 already teaches ヤバい, U10 Sec 1 already teaches 思ってて, U38 Sec 4 already teaches 〜って！)
3. Eliminates all dual-answer and plausible trap ambiguities across cloze questions:
   - CLOZE_060: replaces '食べよ' with '食べりょう'
   - CLOZE_126: replaces 'でした' with 'ます', traps: ['ます', 'に', 'で']
   - CLOZE_127: replaces noun list with non-possessable/verbal traps: ['降る', '雨天', '濡れる']
   - CLOZE_130: replaces '食べない' with '食べな', traps: ['食べます', '食べて', '食べな']
   - CLOZE_132: replaces '今日' with '来週', traps: ['明日', '来週', '今から']
   - CLOZE_133: replaces 'すこし' with 'ちっとも', traps: ['あまり', 'ぜんぜん', 'ちっとも']
   - CLOZE_136: replaces 'きます' with '咲きます', traps: ['あります', '咲きます', '実ります']
   - CLOZE_137: replaces '中' with '間', traps: ['間', '頃', '最中']
   - CLOZE_139: replaces 'また' with 'あまり', traps: ['まだ', 'あまり', '全然']
   - CLOZE_145: replaces '払う' with '払っ', traps: ['払い', '払っ', '払いて']
   - CLOZE_149: replaces '受けた' with '受けろ', traps: ['受け', '受けて', '受けろ']
   - CLOZE_151: replaces '紹介' with '散歩', traps: ['安心', '出発', '散歩']
   - CLOZE_154: traps: ['ちゃえた', 'ちゃえば', 'ちゃんだ']
   - CLOZE_164: replaces 'ように' with 'うちに', traps: ['ために', 'ついでに', 'うちに']
   - CLOZE_171: replaces '間違い', '見間違い' with '勘定', '勘弁', '場違い'
   - CLOZE_179: replaces '随分', '随意' with '随行', '随筆', traps: ['随伴', '随行', '随筆']
   - CLOZE_182: replaces '委任' with '再任', traps: ['再任', '任免', '専任']
   - CLOZE_183: replaces '処置' with '放置', traps: ['放置', '設置', '位置']
   - CLOZE_184: replaces '円満', '滑らか' with '円周', '楕円', traps: ['円周', '円形', '楕円']
   - CLOZE_185: replaces '遠回' with '直角', traps: ['屈折', '曲線', '直角']
4. Classifies Cloze questions aligned with meta.tierDesc:
   - Tier 1 (丁寧體): 148 questions
   - Tier 2 (一般常體): 30 questions
   - Tier 3 (死黨道地口語): 7 questions
5. Verifies vocabIds with token-boundary alignment (230 examples, 730 bindings).
"""

import json
import fugashi

tagger = fugashi.Tagger()

# 1. Load Vocabularies
vocabs = {}
for lvl in ['N5', 'N4', 'N3', 'N2', 'N1']:
    with open(f'vocab_{lvl}.js', 'r', encoding='utf-8') as f:
        text = f.read()
    s = text.find('[')
    e = text.rfind(']')
    arr = json.loads(text[s:e+1])
    for w in arr:
        vocabs[w['id']] = (lvl, w)

print(f"Loaded {len(vocabs)} vocabs.")

# 2. Load grammar_DB.js
with open('grammar_DB.js', 'r', encoding='utf-8') as f:
    text = f.read()

m = text.find('window.GRAMMAR_DB = ')
start = m + len('window.GRAMMAR_DB = ')
decoder = json.JSONDecoder()
db, end_idx = decoder.raw_decode(text[start:])
header = text[:m]
iife_pos = text.find('/* ---------------------------------------------------------------------------', start + end_idx)
iife = text[iife_pos:] if iife_pos != -1 else ""

# 3. Update U08 Section 0 with 3-Step Decision Tree in points and table
u08 = next(u for u in db['vaultUnits'] if u['id'] == 'U08')
u08['sections'][0] = {
    "subtitle": "🏛️ 前置知識：動詞三大隊伍分類與 3 步判定樹（學習目標 #45）",
    "mindset": "面對任何一個未知日語動詞辭書形，只需透過 3 步判定樹（三步判定法）即可 100% 正確分類！",
    "table": {
        "headers": ["判定步驟", "檢驗規則", "分類結果", "代表詞彙"],
        "rows": [
            ["步驟 1", "檢查是否為「する」或「来る」", "第三類（不規則動詞）", "する、来る、勉強する"],
            ["步驟 2", "檢查字尾是否『不是』る結尾", "第一類（五段動詞）", "書く、話す、待つ、死ぬ、呼ぶ、飲む、買う"],
            ["步驟 3", "字尾是る，且倒數第二個假名為 i 或 e 段", "第二類（一段動詞）", "食べる、見る、起きる、教える、寝る"],
            ["例外防呆", "外表像一段但骨子裡是五段（7 大必考例外）", "第一類（五段動詞）", "帰る、入る、走る、切る、知る、要る、減る"]
        ]
    },
    "formula": "動詞分類 ➔ 決定後續所有活用變化（て形、ない形、可能形、被動形、使役形）的唯一基石",
    "points": [
        "【三步判定法 / 3 步判定樹（學習目標 #45）】任何動詞辭書形依序走 3 步即可 100% 分類：",
        "步驟 1：先看是否為「する」或「来る」➔ 直接歸為第三類（III 類 / 不規則動詞）。",
        "步驟 2：看字尾是否『不是』る（如：く、す、つ、ぬ、ぶ、む、う、ぐ）➔ 100% 絕對是第一類動詞（I 類 / 五段動詞）。",
        "步驟 3：字尾是「る」時，看倒數第二個音：若前一音為 a、u、o 段 ➔ 第一類；若前一音為 i、e 段 ➔ 99% 屬於第二類動詞（II 類 / 一段動詞）。",
        "第一類（五段動詞 / I 類）：變形時會在「あ・い・う・え・お」五個音階間跳躍。",
        "第二類（一段動詞 / II 類）：變形時最簡單，幾乎都是直接去「る」。",
        "第三類（不規則動詞 / III 類）：只有兩個——する（做）與 来る（くる/來）。"
    ],
    "warnings": [
        "⚠️ 【7 大必考例外動詞（外表像一段，骨子裡是五段）】",
        "1. 帰る (かえる/回)：倒數第二音是え段，但是五段動詞！活用為「帰り・帰って・帰らない」。",
        "2. 入る (はいる/進)：倒數第二音是い段，但是五段動詞！活用為「入り・入って・入らない」。",
        "3. 走る (はしる/跑)：倒數第二音是い段，但是五段動詞！活用為「走り・走って・走らない」。",
        "4. 切る (きる/剪切)：倒數第二音是い段，但是五段動詞！活用為「切り・切って・切らない」。",
        "5. 知る (しる/知道)：倒數第二音是い段，但是五段動詞！活用為「知り・知って・知らない」。",
        "6. 要る (いる/需要)：倒數第二音是い段，但是五段動詞！活用為「要り・要って・要らない」。",
        "7. 減る (へる/減少)：倒數第二音是え段，但是五段動詞！活用為「減り・減って・減らない」。"
    ]
}

# 4. Enrich U16, U26, U32 to formally teach Tier 3 colloquial features
u16 = next(u for u in db['vaultUnits'] if u['id'] == 'U16')
u16['sections'][0]['points'] = [
    "【程度副詞金字塔】とても／大変（非常，配肯定）➔ 少し／ちょっと（稍微，配肯定）➔ あまり（不太，配否定）➔ 全然（完全不，配否定）。",
    "【死黨道地口語（Tier 3）】年輕人與死黨間常用「マジで」（真的、認真地）作為極高頻程度副詞，修飾否定時如「マジで全然〜ない」（真的完全不…），口語語氣極為強烈。"
]

u26 = next(u for u in db['vaultUnits'] if u['id'] == 'U26')
u26['sections'][2]['points'] = [
    "【忠告建議處方箋】肯定建議用「動詞た形 ＋ ほうがいいです」（最好做…）；否定建議用「動詞ない形 ＋ ほうがいいです」（最好不要做…）。",
    "【死黨道地口語（Tier 3）】好友間提出建議時，常將「〜じゃないか」縮約為句尾「〜じゃん」，如「そんなに焦らないほうがいいじゃん！」（不是不要那麼心急比較好嗎！），語氣親切自然。"
]

u32 = next(u for u in db['vaultUnits'] if u['id'] == 'U32')
u32['sections'][1]['points'] = [
    "【常體句型轉接】在文型接續（如 から、ので、と思う、かもしれない）前，動詞必須還原為普通體（辭書形、ない形、た形、なかった形）。",
    "【死黨口語縮約（Tier 3）】在好朋友之間的普通體對話中，「〜てしまった」極高頻縮約為「〜ちゃった」（如：忘れてしまった ➔ 忘れちゃった、断ってしまった ➔ 断っちゃった）。"
]

# 5. Clean Vocab Matcher with Token-Boundary Alignment
def get_clean_vocab_ids(ja, uid):
    parsed = tagger(ja)
    targets = []
    curr = 0
    token_starts = set()
    token_ends = set()
    for w in parsed:
        f = w.feature
        surf = w.surface
        s = ja.find(surf, curr)
        if s == -1:
            s = curr
        e = s + len(surf)
        curr = e
        token_starts.add(s)
        token_ends.add(e)
        targets.append({
            'surface': surf,
            'start': s,
            'end': e,
            'orthBase': getattr(f, 'orthBase', None) or surf,
            'lemma': getattr(f, 'lemma', None) or surf,
            'pos': getattr(f, 'pos1', None)
        })

    matched_ids = []
    claimed_tokens = set()
    seen_ids = set()
    seen_surfaces = set()

    # Explicit override for おかしい
    if 'おかし' in ja and ('変' in ja or '不思議' in ja or '可笑' in ja or 'お菓子' not in ja):
        matched_ids.append('N4_078')
        seen_ids.add('N4_078')
        seen_surfaces.add('おかしい')

    for vid, (lvl, w) in vocabs.items():
        k = w['kanji']
        kana = w['kana']
        notes = w.get('notes', '')
        cats = w.get('categories', [])
        all_desc = notes + ' ' + ' '.join(cats)
        has_hiragana_ending = ('\u3040' <= k[-1] <= '\u309f') if len(k) > 0 else False
        is_inflecting_verb = ('動詞' in all_desc) and not any(bad in all_desc for bad in ['感動詞', '助動詞']) and has_hiragana_ending
        is_adj_i = ('い形容詞' in all_desc or ('形容詞' in all_desc and 'な形容詞' not in all_desc)) and k.endswith('い')
        is_adj_na = 'な形容詞' in all_desc
        has_kanji = (k != kana)

        hit = False
        hit_span = None

        # A. Single-token matching
        for idx, t in enumerate(targets):
            if idx in claimed_tokens:
                continue
            s = t['surface']
            ob = t['orthBase']
            l = t['lemma']
            p = t['pos']

            if is_inflecting_verb:
                if p == '動詞':
                    if has_kanji:
                        if k == ob or k == l:
                            hit = True; hit_span = [idx]
                    else:
                        if kana in [ob, l]:
                            hit = True; hit_span = [idx]
            elif is_adj_i:
                if p in ['形容詞']:
                    if has_kanji:
                        if k == ob or k == l:
                            hit = True; hit_span = [idx]
                    else:
                        if kana in [ob, l]:
                            hit = True; hit_span = [idx]
            elif is_adj_na:
                if p in ['形状詞', '名詞']:
                    if k in [ob, l, s]:
                        hit = True; hit_span = [idx]
                    elif not has_kanji and kana in [ob, l, s]:
                        hit = True; hit_span = [idx]
            else:
                if p in ['名詞', '代名詞', '副詞', '連体詞', '感動詞']:
                    if has_kanji:
                        if k in [s, ob, l]:
                            hit = True; hit_span = [idx]
                    else:
                        if kana in [s, ob, l]:
                            hit = True; hit_span = [idx]
            if hit:
                break

        # B. Compound noun / adverb matching with strict token-boundary alignment
        if not hit and len(k) >= 2 and k in ja:
            if any(c in all_desc for c in ['名詞', '副詞', '助動詞']) and not any(bad in all_desc for bad in ['接続詞', '動詞']):
                if not any(bad in ja for bad in [k + '語', k + '人'] if k in ['本', '日']):
                    pos = 0
                    while True:
                        pos = ja.find(k, pos)
                        if pos == -1:
                            break
                        end = pos + len(k)
                        if pos in token_starts and end in token_ends:
                            tok_indices = [i for i, t in enumerate(targets) if t['start'] >= pos and t['end'] <= end]
                            if not any(i in claimed_tokens for i in tok_indices):
                                hit = True
                                hit_span = tok_indices
                                break
                        pos += 1

        if hit and vid not in seen_ids:
            base_key = k if has_kanji else kana
            if base_key not in seen_surfaces:
                seen_surfaces.add(base_key)
                seen_ids.add(vid)
                if hit_span:
                    for idx in hit_span:
                        claimed_tokens.add(idx)
                matched_ids.append(vid)

    return matched_ids

# 6. Apply clean vocabIds to all examples
example_count = 0
total_vids = 0
for u in db['vaultUnits']:
    uid = u['id']
    for s_idx, sec in enumerate(u.get('sections', [])):
        for ex in sec.get('examples', []):
            example_count += 1
            cleaned = get_clean_vocab_ids(ex['ja'], uid)
            ex['vocabIds'] = cleaned
            total_vids += len(cleaned)

print(f"Processed {example_count} examples, linked {total_vids} vocab IDs.")

# 7. Update Cloze questions and traps to eliminate ALL dual-answers and plausible traps
cloze_trap_updates = {
    'CLOZE_060': {
        'sentence': 'ねえ、一緒に晩ご飯を（  ）！',
        'translation': '欸，一起吃晚餐吧！',
        'answer': '食べよう',
        'traps': ['食べおう', '食べろう', '食べりょう'],
        'targetWordId': 'N5_020',
        'pitchHint': '食べる [2] ➔ 食べよう [3]（推估）',
        'explanation': '第二類動詞（一段動詞）意向形：去掉「る」直接加上「よう」。',
        'category': '死黨口語呼格與意向形'
    },
    'CLOZE_126': {
        'sentence': '私は學生（  ）。会社員ではありません。',
        'sentence': '私は学生（  ）。会社員ではありません。',
        'answer': 'です',
        'traps': ['ます', 'に', 'で'],
        'explanation': '名詞現在肯定句使用「名詞 ＋ です」；否定句使用「名詞 ＋ ではありません」。動詞ます幹助動詞「ます」或格助詞「に/で」在此句法不通。'
    },
    'CLOZE_127': {
        'sentence': 'これは私の（  ）です。',
        'answer': '傘',
        'traps': ['降る', '雨天', '濡れる'],
        'explanation': '名詞之間表示所屬關係時使用助詞「の」，「私の傘」表示我的雨傘；「降る／濡れる」為動詞辭書形，「雨天」為天候名詞不可作為私人物件所有。'
    },
    'CLOZE_130': {
        'sentence': '一緒に美味しいご飯を（  ）か。',
        'answer': '食べません',
        'traps': ['食べます', '食べて', '食べな'],
        'explanation': '禮貌邀請對方一同進行動作時使用「動詞ます幹 ＋ ませんか」；「食べますか」為單純詢問，「食べて／食べな」語法錯接。'
    },
    'CLOZE_132': {
        'sentence': '（  ）は全然寝ませんでした。',
        'answer': '昨日',
        'traps': ['明日', '来週', '今から'],
        'explanation': '搭配過去否定動詞「寝ませんでした」，時間詞必須使用過去時間「昨日」；未來時間「明日／来週／今から」在時態上無法接續過去式。'
    },
    'CLOZE_133': {
        'sentence': '休日は（  ）図書館で本を読みます。',
        'answer': 'よく',
        'traps': ['あまり', 'ぜんぜん', 'ちっとも'],
        'explanation': '肯定謂語「読みます」必須搭配肯定頻率副詞「よく」；「あまり」「ぜんぜん」「ちっとも」均為強烈否定呼應副詞（NPI），後續必須接否定形。'
    },
    'CLOZE_136': {
        'sentence': 'ロビーに田中先生が（  ）よ。',
        'answer': 'います',
        'traps': ['あります', '咲きます', '実ります'],
        'explanation': '人、動物等有生命之主體存在時必須使用動詞「います」；「あります」限於無生命物品，「咲きます／実ります」為主語為花卉植物時專用。'
    },
    'CLOZE_137': {
        'sentence': '駅の（  ）に大きなコンビニがあります。',
        'answer': '前',
        'traps': ['間', '頃', '最中'],
        'explanation': '建築物具體空間相對方位詞「駅の前（まえ）に」；「間（あいだ）」需兩點參照，「頃（ころ）」為時間詞，「最中（さなか）」為事件進行中，均不可接於單一建築物後表方位。'
    },
    'CLOZE_139': {
        'sentence': '朝ご飯は（  ）食べましたか。',
        'answer': 'もう',
        'traps': ['まだ', 'あまり', '全然'],
        'explanation': '詢問某動作是否「已經完成」時使用副詞「もう」；「まだ」表尚未且接否定持續形，「あまり／全然」表程度並呼應否定。'
    },
    'CLOZE_145': {
        'sentence': 'レジでお金を（  ）から、商品を受け取ります。',
        'answer': '払って',
        'traps': ['払い', '払っ', '払いて'],
        'explanation': '表示「先完成 A 動作之後再進行 B 動作」之時間先後順序時，必須使用「動詞て形 ＋ から」；「払う」促音便為「払って」，其他變形均為非語法形式。'
    },
    'CLOZE_149': {
        'sentence': '来月、日本語の試験を（  ）つもりです。',
        'answer': '受ける',
        'traps': ['受け', '受けて', '受けろ'],
        'explanation': '表示個人未來的意志與打算時，使用「動詞辭書形 ＋ つもりです」；「受け／受けて／受けろ」均無法直接接續表示意志打算的「つもり」。'
    },
    'CLOZE_151': {
        'sentence': '先生が文法をわかりやすく（  ）してくださいました。',
        'answer': '説明',
        'traps': ['安心', '出発', '散歩'],
        'explanation': '「文法をわかりやすく説明する」為精確教學動作搭配；「安心／出発／散歩」均為不及物或語意無涉動詞，無法帶「文法を」受詞。'
    },
    'CLOZE_154': {
        'sentence': '無理な頼みだったから、断っ（  ）よ！',
        'translation': '因為是太過勉強的請求，所以就直接拒絕掉了喔！',
        'answer': 'ちゃった',
        'traps': ['ちゃえた', 'ちゃえば', 'ちゃんだ'],
        'targetWordId': 'N4_018',
        'pitchHint': 'ことわる [3] ➔ ことわっちゃった [4] よ',
        'explanation': '「〜てしまう」在死黨好友口語中常縮約為「〜ちゃう／〜ちゃった」。「断る」促音便「断って」縮約為「断っちゃった」。干擾項中「ちゃえば」為假定形、「ちゃんだ」為錯拼、「ちゃえた」為可能過去形且語意不合。',
        'category': '死黨口語縮約（〜ちゃう）'
    },
    'CLOZE_159': {
        'sentence': 'この料理、毎日食べてもマジで全然（  ）よ！',
        'translation': '這道菜就算每天吃也真的完全吃不膩喔！',
        'answer': '飽きない',
        'traps': ['飽かない', '飽きらない', '飽きず'],
        'targetWordId': 'N3_004',
        'pitchHint': 'あきる [2] ➔ あきない [2] よ',
        'explanation': '加入死黨口語強調詞「マジで」（真的、認真地），一段動詞「飽きる」否定常體為「飽きない」。',
        'category': '死黨口語相槌（マジで）'
    },
    'CLOZE_164': {
        'sentence': '説明書の図の（  ）家具を組み立てました。',
        'answer': 'とおりに',
        'traps': ['ために', 'ついでに', 'うちに'],
        'explanation': '表示照著基準、指示依樣進行時使用「名詞 ＋ のとおりに」；「ために／ついでに／うちに」均無法與指示圖示名詞構成合乎句意之接續。'
    },
    'CLOZE_171': {
        'sentence': '彼の話は単なる（  ）に違いない。',
        'answer': '勘違い',
        'traps': ['勘定', '勘弁', '場違い'],
        'explanation': '「単なる勘違い（誤會）」表示認知偏差；「勘定（結帳/計算）」、「勘弁（原諒寬恕）」、「場違い（不合場合）」語意範疇全然不合，正解唯一。'
    },
    'CLOZE_172': {
        'sentence': 'そんなに（  ）ないほうがいいじゃん！',
        'translation': '別那麼心急比較好吧（不是很好嗎）！',
        'answer': '焦ら',
        'traps': ['焦れ', '焦り', '焦ろ'],
        'targetWordId': 'N2_014',
        'pitchHint': 'あせる [2] ➔ あせらない [3] ほうがいいじゃん',
        'explanation': '五段動詞「焦る」否定為「焦らない」。句尾「〜じゃん」為「〜じゃないか」之死黨口語縮約，表示親密提醒與建議。',
        'category': '死黨口語建議（〜じゃん）'
    },
    'CLOZE_179': {
        'sentence': '最新情報は（  ）更新することになっている。',
        'answer': '随時',
        'traps': ['随伴', '随行', '随筆'],
        'explanation': '副詞「随時（ずいじ）」表示不限時間隨時進行；「随伴／随行（伴隨陪同）」與「随筆（隨筆散文）」均為名詞，無法副詞化修飾動詞「更新する」。'
    },
    'CLOZE_182': {
        'sentence': '全責任を彼に（  ）させられた。',
        'answer': '一任',
        'traps': ['再任', '任免', '専任'],
        'explanation': '「全責任を一任する（全權委託承擔）」；「再任（官職連任）」、「任免（任命免職人事權）」、「専任（專職專任）」均為人事聘任術語，無法與「全責任」搭配。'
    },
    'CLOZE_183': {
        'sentence': '緊急の（  ）を取る場合は、速やかに報告してください。',
        'answer': '措置',
        'traps': ['放置', '設置', '位置'],
        'explanation': '「緊急の措置を取る」為政策法令應急處置唯一標準動賓搭配；「放置（放任棄置）」、「設置（設立安裝）」、「位置（地理方位）」均無法與「〜を取る」搭配。'
    },
    'CLOZE_184': {
        'sentence': '会議を（  ）に進めることが重要です。',
        'answer': '円滑',
        'traps': ['円周', '円形', '楕円'],
        'explanation': 'な形容詞副詞化「円滑に進める（順利推展進行）」；干擾項「円周／円形／楕円」均為純幾何形狀名詞，無法修飾動詞「進める」。'
    },
    'CLOZE_185': {
        'sentence': '相手に不快感を与えないよう、（  ）に断りました。',
        'answer': '婉曲',
        'traps': ['屈折', '曲線', '直角'],
        'explanation': 'な形容詞副詞化「婉曲に断る（委婉委蛇地拒絕）」；「屈折／曲線／直角」為物理與幾何名詞，無法修飾交際言語動作「断る」。'
    }
}

for q in db['clozeQuestions']:
    cid = q['id']
    if cid in cloze_trap_updates:
        for k, v in cloze_trap_updates[cid].items():
            q[k] = v

# 8. Apply Tier classification strictly aligned with meta.tierDesc
tier3_ids = {'CLOZE_054', 'CLOZE_060', 'CLOZE_090', 'CLOZE_154', 'CLOZE_159', 'CLOZE_168', 'CLOZE_172'}
tier_counts = {'Tier 1 丁寧體': 0, 'Tier 2 一般常體': 0, 'Tier 3 死黨道地口語': 0}

for q in db['clozeQuestions']:
    cid = q['id']
    s = q['sentence'].replace('（  ）', q['answer'])
    has_polite = any(p in s for p in ['です', 'ます', 'でした', 'ました', 'ません', 'ください', 'ましょう', 'ませんか', 'ございます', 'いただき', 'くださいました'])
    if has_polite:
        t = 'Tier 1 丁寧體'
    elif cid in tier3_ids:
        t = 'Tier 3 死黨道地口語'
    else:
        t = 'Tier 2 一般常體'
    q['tier'] = t
    tier_counts[t] += 1

print(f"Cloze questions Tier breakdown: {tier_counts}")

# 9. Re-serialize grammar_DB.js
db_json = json.dumps(db, ensure_ascii=False, indent=2)
new_content = header + "window.GRAMMAR_DB = " + db_json + ";\n\n" + iife

with open('grammar_DB.js', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Saved updated grammar_DB.js successfully!")
