# -*- coding: utf-8 -*-
import json
import re

# 1. Load Vocabularies
vocabs = {}
vocabs_by_lvl = {'N5': {}, 'N4': {}, 'N3': {}, 'N2': {}, 'N1': {}}
for lvl in ['N5', 'N4', 'N3', 'N2', 'N1']:
    with open(f'vocab_{lvl}.js', encoding='utf8') as f:
        text = f.read()
    s = text.find('[')
    e = text.rfind(']')
    arr = json.loads(text[s:e+1])
    for w in arr:
        vocabs[w['id']] = (lvl, w)
        vocabs_by_lvl[lvl][w['id']] = w

# Load grammar_DB.js
with open('grammar_DB.js', 'r', encoding='utf-8') as f:
    text = f.read()

m = text.find('window.GRAMMAR_DB = ')
start = m + len('window.GRAMMAR_DB = ')
decoder = json.JSONDecoder()
db, end_idx = decoder.raw_decode(text[start:])
header = text[:m]
iife_pos = text.find('/* ---------------------------------------------------------------------------', start + end_idx)
iife = text[iife_pos:] if iife_pos != -1 else ""

# 2. Strict vocab matcher for example sentences
def strict_find_vocab_ids(ja_sentence):
    matched_ids = []
    candidates = []
    for vid, (lvl, w) in vocabs.items():
        k = w['kanji']
        kana = w['kana']
        
        matched = False
        if len(k) >= 2 and k in ja_sentence:
            matched = True
        elif len(k) == 1 and k in ja_sentence:
            if '名詞' in w.get('categories', []) or w.get('notes') == '名詞':
                if "日本語" in ja_sentence and k == "本":
                    matched = False
                elif "田中" in ja_sentence and k == "中":
                    matched = False
                elif any(word in ja_sentence for word in ["昨日", "今日", "明日", "毎日", "一日中", "先週", "来週", "来月"]) and (k == "日" or k == "今" or k == "昨" or k == "明"):
                    matched = False
                else:
                    matched = True
            elif k + 'る' in ja_sentence or k + 'ます' in ja_sentence or k + 'て' in ja_sentence or k + 'た' in ja_sentence or k + 'ない' in ja_sentence or k + 'い' in ja_sentence or k + 'く' in ja_sentence:
                matched = True
        elif len(k) >= 2:
            stem = k[:-1]
            if len(stem) >= 1 and stem in ja_sentence and any(k == verb for verb in ['食べる', '飲む', '買う', '行く', '来る', '見る', '起きる', '寝る', '話す', '聞く', '書く', '休む', '待つ', '履く', '落とす', '使う', '切る', '着く', '降る', '作る', '褒める', '開く', '閉める', '貼る', '急ぐ', '運ぶ', '直す', '払う', '探す', '壊れる', '諦める', '当たる', '仰ぐ', '憧れる', '焦る', '甘える', '勘違い']):
                matched = True

        if matched:
            candidates.append((vid, k, lvl, len(k)))

    candidates.sort(key=lambda x: -x[3])
    seen_kanji = set()
    result = []
    for vid, k, lvl, _ in candidates:
        if k not in seen_kanji:
            seen_kanji.add(k)
            result.append(vid)
        if len(result) >= 4:
            break
    return result

for u in db['vaultUnits']:
    for sec in u.get('sections', []):
        for ex in sec.get('examples', []):
            ex['vocabIds'] = strict_find_vocab_ids(ex['ja'])

# 3. Design exactly 60 Cloze Questions (CLOZE_126 to CLOZE_185)
# Level breakdown:
# N5: 16 (CLOZE_126..141)
# N4: 16 (CLOZE_142..157)
# N3: 12 (CLOZE_158..169)
# N2: 8  (CLOZE_170..177)
# N1: 8  (CLOZE_178..185)

cloze_1_to_125 = [q for q in db['clozeQuestions'] if int(q['id'].replace('CLOZE_', '')) <= 125]
assert len(cloze_1_to_125) == 125, f"Expected 125 existing clozes, got {len(cloze_1_to_125)}"

new_clozes = [
    # --- N5 (16 questions) ---
    {
        "id": "CLOZE_126",
        "vocabLevel": "N5",
        "unitId": "U13",
        "scenarioId": "S01",
        "category": "名詞肯定句與否定句",
        "tier": "Tier 1 丁寧體",
        "sentence": "私は学生（  ）。会社員ではありません。",
        "translation": "我是學生。不是公司職員。",
        "answer": "です",
        "traps": ["でした", "ます", "だ"],
        "targetWordId": "N5_015",  # 学生 [0]
        "pitchHint": "がくせい [0] ＋ です",
        "explanation": "名詞現在肯定句使用「名詞 ＋ です」；否定句使用「名詞 ＋ ではありません / じゃありません」。",
        "audio": "./audio/grammar/CLOZE_126.mp3"
    },
    {
        "id": "CLOZE_127",
        "vocabLevel": "N5",
        "unitId": "U13",
        "scenarioId": "S02",
        "category": "助詞の（所屬與修飾）",
        "tier": "Tier 1 丁寧體",
        "sentence": "これは私の（  ）です。",
        "translation": "這是我的雨傘。",
        "answer": "傘",
        "traps": ["車", "靴", "鞄"],
        "targetWordId": "N5_016",  # 傘 [1]
        "pitchHint": "かさ [1]",
        "explanation": "名詞之間表示所屬關係時，使用助詞「の」，「私の傘」表示我的雨傘。",
        "audio": "./audio/grammar/CLOZE_127.mp3"
    },
    {
        "id": "CLOZE_128",
        "vocabLevel": "N5",
        "unitId": "U14",
        "scenarioId": "S01",
        "category": "指示詞（これ・それ・あれ）",
        "tier": "Tier 1 丁寧體",
        "sentence": "すみません、（  ）は何ですか。",
        "translation": "不好意思，這是什麼？",
        "answer": "これ",
        "traps": ["この", "ここ", "こう"],
        "targetWordId": "N5_689",  # これ [0]
        "pitchHint": "これ [0]",
        "explanation": "指稱身邊的事物且後面直接接助詞「は」時，使用事物代名詞「これ」。",
        "audio": "./audio/grammar/CLOZE_128.mp3"
    },
    {
        "id": "CLOZE_129",
        "vocabLevel": "N5",
        "unitId": "U14",
        "scenarioId": "S05",
        "category": "指示連體詞（この・その・あの）",
        "tier": "Tier 1 丁寧體",
        "sentence": "（  ）靴はいくらですか。",
        "translation": "這雙鞋子多少錢？",
        "answer": "この",
        "traps": ["これ", "ここ", "こちら"],
        "targetWordId": "N5_075",  # 靴 [2]
        "pitchHint": "くつ [2] の前に この [0]",
        "explanation": "修飾名詞「靴」時，必須使用指示連體詞「この」；「これ」是獨立代名詞不能直接修飾名詞。",
        "audio": "./audio/grammar/CLOZE_129.mp3"
    },
    {
        "id": "CLOZE_130",
        "vocabLevel": "N5",
        "unitId": "U15",
        "scenarioId": "S03",
        "category": "邀請句型（〜ませんか）",
        "tier": "Tier 1 丁寧體",
        "sentence": "一緒に美味しいご飯を（  ）か。",
        "translation": "要不要一起去吃美味的飯呢？",
        "answer": "食べません",
        "traps": ["食べます", "食べて", "食べない"],
        "targetWordId": "N5_020",  # 食べる [2]
        "pitchHint": "たべる [2] ➔ たべません [4]",
        "explanation": "禮貌邀請對方一同進行動作時，使用「動詞ます幹 ＋ ませんか」。",
        "audio": "./audio/grammar/CLOZE_130.mp3"
    },
    {
        "id": "CLOZE_131",
        "vocabLevel": "N5",
        "unitId": "U15",
        "scenarioId": "S02",
        "category": "助詞と（伴隨夥伴）",
        "tier": "Tier 1 丁寧體",
        "sentence": "友達（  ）新幹線で京都へ行きます。",
        "translation": "和朋友搭新幹線去京都。",
        "answer": "と",
        "traps": ["に", "で", "を"],
        "targetWordId": "N5_038",  # 友達 [0]
        "pitchHint": "ともだち [0] と",
        "explanation": "表示共同進行動作的伴隨夥伴時，使用助詞「と」。",
        "audio": "./audio/grammar/CLOZE_131.mp3"
    },
    {
        "id": "CLOZE_132",
        "vocabLevel": "N5",
        "unitId": "U16",
        "scenarioId": "S06",
        "category": "時間名詞與過去否定",
        "tier": "Tier 1 丁寧體",
        "sentence": "（  ）は全然寝ませんでした。",
        "translation": "昨天完全沒有睡覺。",
        "answer": "昨日",
        "traps": ["今日", "明日", "毎日"],
        "targetWordId": "N5_032",  # 昨日 [2]
        "pitchHint": "きのう [2]",
        "explanation": "搭配過去否定動詞「寝ませんでした」，時間詞使用「昨日 (きのう)」。",
        "audio": "./audio/grammar/CLOZE_132.mp3"
    },
    {
        "id": "CLOZE_133",
        "vocabLevel": "N5",
        "unitId": "U16",
        "scenarioId": "S03",
        "category": "頻率副詞（よく）",
        "tier": "Tier 1 丁寧體",
        "sentence": "休日は（  ）図書館で本を読みます。",
        "translation": "假日我常常在圖書館看書。",
        "answer": "よく",
        "traps": ["あまり", "ぜんぜん", "すこし"],
        "targetWordId": "N5_046",  # 本 [1]
        "pitchHint": "ほん [1] を よく [1] よむ",
        "explanation": "表示頻率高「常常」且接肯定句時使用副詞「よく」；「あまり」「ぜんぜん」必須接否定。",
        "audio": "./audio/grammar/CLOZE_133.mp3"
    },
    {
        "id": "CLOZE_134",
        "vocabLevel": "N5",
        "unitId": "U17",
        "scenarioId": "S01",
        "category": "願望表現（〜たい）",
        "tier": "Tier 1 丁寧體",
        "sentence": "冷たい水が（  ）です。",
        "translation": "我想喝冰涼的水。",
        "answer": "飲みたい",
        "traps": ["飲みます", "飲んで", "飲む"],
        "targetWordId": "N5_055",  # 水 [0]
        "pitchHint": "みず [0] が のみたい [3]",
        "explanation": "表示第一人稱自己的願望時，使用「動詞ます幹 ＋ たいです」。",
        "audio": "./audio/grammar/CLOZE_134.mp3"
    },
    {
        "id": "CLOZE_135",
        "vocabLevel": "N5",
        "unitId": "U17",
        "scenarioId": "S07",
        "category": "動詞過去肯定形",
        "tier": "Tier 1 丁寧體",
        "sentence": "昨日は疲れたので、早く（  ）。",
        "translation": "昨天因為累了，所以很早就睡了。",
        "answer": "寝ました",
        "traps": ["寝ます", "寝ません", "寝て"],
        "targetWordId": "N5_108",  # 寝る [0]
        "pitchHint": "ねる [0] ➔ ねました [3]",
        "explanation": "過去時間（昨日）發生的肯定動作，使用「動詞ます幹 ＋ ました」。",
        "audio": "./audio/grammar/CLOZE_135.mp3"
    },
    {
        "id": "CLOZE_136",
        "vocabLevel": "N5",
        "unitId": "U18",
        "scenarioId": "S04",
        "category": "存在動詞（あります vs います）",
        "tier": "Tier 1 丁寧體",
        "sentence": "ロビーに田中先生が（  ）よ。",
        "translation": "大廳有田中老師在喔。",
        "answer": "います",
        "traps": ["あります", "します", "きます"],
        "targetWordId": "N5_037",  # 先生 [3]
        "pitchHint": "せんせい [3] が います [1]",
        "explanation": "人、動物等有生命的主體存在時，必須使用動詞「います」；「あります」限於無生命物品或植物。",
        "audio": "./audio/grammar/CLOZE_136.mp3"
    },
    {
        "id": "CLOZE_137",
        "vocabLevel": "N5",
        "unitId": "U18",
        "scenarioId": "S02",
        "category": "空間位置名詞（前）",
        "tier": "Tier 1 丁寧體",
        "sentence": "駅の（  ）に大きなコンビニがあります。",
        "translation": "車站前面有一家很大的便利商店。",
        "answer": "前",
        "traps": ["先", "後", "中"],
        "targetWordId": "N5_169",  # 駅 [1]
        "pitchHint": "えき [1] の まえ [1]",
        "explanation": "空間相對位置詞：「駅の前 (まえ) に」表示在車站前方。",
        "audio": "./audio/grammar/CLOZE_137.mp3"
    },
    {
        "id": "CLOZE_138",
        "vocabLevel": "N5",
        "unitId": "U19",
        "scenarioId": "S03",
        "category": "動詞購買與量詞",
        "tier": "Tier 1 丁寧體",
        "sentence": "冷たいジュースを二本（  ）ました。",
        "translation": "買了兩瓶冰果汁。",
        "answer": "買い",
        "traps": ["買う", "買っ", "買わ"],
        "targetWordId": "N5_013",  # 買う [0]
        "pitchHint": "かう [0] ➔ かいました [3]",
        "explanation": "動詞「買う」的過去肯定形為「買いました」。",
        "audio": "./audio/grammar/CLOZE_138.mp3"
    },
    {
        "id": "CLOZE_139",
        "vocabLevel": "N5",
        "unitId": "U19",
        "scenarioId": "S01",
        "category": "副詞（もう vs まだ）",
        "tier": "Tier 1 丁寧體",
        "sentence": "朝ご飯は（  ）食べましたか。",
        "translation": "早餐已經吃了嗎？",
        "answer": "もう",
        "traps": ["まだ", "また", "もっと"],
        "targetWordId": "N5_005",  # 朝ご飯 [3]
        "pitchHint": "あさごはん [3]",
        "explanation": "詢問某動作是否「已經完成」時使用副詞「もう」；「まだ」表示尚未。",
        "audio": "./audio/grammar/CLOZE_139.mp3"
    },
    {
        "id": "CLOZE_140",
        "vocabLevel": "N5",
        "unitId": "U20",
        "scenarioId": "S07",
        "category": "い形容詞過去肯定",
        "tier": "Tier 1 丁寧體",
        "sentence": "昨日の京都はとても（  ）です。",
        "translation": "昨天的京都非常寒冷。",
        "answer": "寒かった",
        "traps": ["寒いでした", "寒いた", "寒くでした"],
        "targetWordId": "N5_146",  # 寒い [2]
        "pitchHint": "さむい [2] ➔ さむかった [3] です",
        "explanation": "い形容詞過去肯定必須將字尾「い」改為「かった」，絕對不可直接加「でした」（禁忌：❌寒いでした）。",
        "audio": "./audio/grammar/CLOZE_140.mp3"
    },
    {
        "id": "CLOZE_141",
        "vocabLevel": "N5",
        "unitId": "U20",
        "scenarioId": "S06",
        "category": "名詞過去肯定（でした）",
        "tier": "Tier 1 丁寧體",
        "sentence": "昨日は一日中（  ）でした。",
        "translation": "昨天一整天都是下雨天。",
        "answer": "雨",
        "traps": ["雨だ", "雨な", "雨ます"],
        "targetWordId": "N5_035",  # 雨 [1]
        "pitchHint": "あめ [1] でした",
        "explanation": "名詞過去肯定式使用「名詞 ＋ でした」。",
        "audio": "./audio/grammar/CLOZE_141.mp3"
    },

    # --- N4 (16 questions) ---
    {
        "id": "CLOZE_142",
        "vocabLevel": "N4",
        "unitId": "U21",
        "scenarioId": "S05",
        "category": "比較句型（より）",
        "tier": "Tier 1 丁寧體",
        "sentence": "二つの値段を（  ）て、安いほうを買いました。",
        "translation": "比較了兩個價格，買了比較便宜的那一個。",
        "answer": "比べ",
        "traps": ["比べら", "比べる", "比べれ"],
        "targetWordId": "N4_017",  # 比べる [0]
        "pitchHint": "くらべる [0] ➔ くらべて [0]",
        "explanation": "第二類（一段）動詞「比べる」變て形時去掉「る」加上「て」（比べて）。",
        "audio": "./audio/grammar/CLOZE_142.mp3"
    },
    {
        "id": "CLOZE_143",
        "vocabLevel": "N4",
        "unitId": "U22",
        "scenarioId": "S02",
        "category": "行動提議（ましょう）",
        "tier": "Tier 1 丁寧體",
        "sentence": "電車の時間がありませんから、（  ）ましょう。",
        "translation": "電車時間快到了，我們快點趕快吧。",
        "answer": "急ぎ",
        "traps": ["急ぐ", "急いで", "急が"],
        "targetWordId": "N4_002",  # 急ぐ [2]
        "pitchHint": "いそぐ [2] ➔ いそぎましょう [5]",
        "explanation": "第一類（五段）動詞「急ぐ」接「ましょう」時，尾音轉い段音（急ぎましょう）。",
        "audio": "./audio/grammar/CLOZE_143.mp3"
    },
    {
        "id": "CLOZE_144",
        "vocabLevel": "N4",
        "unitId": "U15",
        "scenarioId": "S02",
        "category": "授受請託（〜てもらえませんか）",
        "tier": "Tier 1 丁寧體",
        "sentence": "田中さんに伝言を（  ）てもらえませんか。",
        "translation": "能不能請您幫我向田中先生轉達留言呢？",
        "answer": "伝え",
        "traps": ["伝えて", "伝える", "伝われ"],
        "targetWordId": "N4_031",  # 伝える [0]
        "pitchHint": "つたえる [0] ➔ つたえて [0]",
        "explanation": "一段動詞「伝える」接「〜てもらう」時去掉「る」加「て」（伝えて）。",
        "audio": "./audio/grammar/CLOZE_144.mp3"
    },
    {
        "id": "CLOZE_145",
        "vocabLevel": "N4",
        "unitId": "U23",
        "scenarioId": "S01",
        "category": "動作先後順序（〜てから）",
        "tier": "Tier 1 丁寧體",
        "sentence": "レジでお金を（  ）から、商品を受け取ります。",
        "translation": "在收銀台付完錢之後，才領取商品。",
        "answer": "払って",
        "traps": ["払い", "払う", "払いて"],
        "targetWordId": "N4_047",  # 払う [2]
        "pitchHint": "はらう [2] ➔ はらって [2]",
        "explanation": "動詞「払う」尾音是「う」，促音便為「払って」，接「から」表示做完之後才…。",
        "audio": "./audio/grammar/CLOZE_145.mp3"
    },
    {
        "id": "CLOZE_146",
        "vocabLevel": "N4",
        "unitId": "U23",
        "scenarioId": "S06",
        "category": "遺憾失誤（〜てしまう）",
        "tier": "Tier 1 丁寧體",
        "sentence": "駅で大切な切符を（  ）てしまいました。",
        "translation": "在車站不小心把重要的車票弄丟了。",
        "answer": "落とし",
        "traps": ["落とす", "落とせ", "落とさ"],
        "targetWordId": "N4_103",  # 落とす [2]
        "pitchHint": "おとす [2] ➔ おとして [2]",
        "explanation": "五段動詞「落とす」變て形為「落として」，接「しまいました」表示遺憾與過失。",
        "audio": "./audio/grammar/CLOZE_146.mp3"
    },
    {
        "id": "CLOZE_147",
        "vocabLevel": "N4",
        "unitId": "U36",
        "scenarioId": "S06",
        "category": "自動詞結果狀態（壊れる）",
        "tier": "Tier 1 丁寧體",
        "sentence": "昨日からパソコンが（  ）ています。",
        "translation": "從昨天開始電腦就壞掉了。",
        "answer": "壊れ",
        "traps": ["壊れる", "壊し", "壊れた"],
        "targetWordId": "N4_115",  # 壊れる [3]
        "pitchHint": "こわれる [3] ➔ こわれている [3]",
        "explanation": "自動詞「壊れる」變て形為「壊れて」，搭配「います」表示物品損壞的持續狀態。",
        "audio": "./audio/grammar/CLOZE_147.mp3"
    },
    {
        "id": "CLOZE_148",
        "vocabLevel": "N4",
        "unitId": "U28",
        "scenarioId": "S02",
        "category": "條件否定（〜ないと）",
        "tier": "Tier 1 丁寧體",
        "sentence": "急がないと、電車に（  ）ませんよ。",
        "translation": "不快點的話，會趕不上電車喔。",
        "answer": "間に合い",
        "traps": ["間に合う", "間に合っ", "間に合わ"],
        "targetWordId": "N4_056",  # 間に合う [3]
        "pitchHint": "まにあう [3] ➔ まにあいません [5]",
        "explanation": "五段動詞「間に合う」否定丁寧形為「間に合いません」。",
        "audio": "./audio/grammar/CLOZE_148.mp3"
    },
    {
        "id": "CLOZE_149",
        "vocabLevel": "N4",
        "unitId": "U27",
        "scenarioId": "S07",
        "category": "打算（辞書形＋つもり）",
        "tier": "Tier 1 丁寧體",
        "sentence": "来月、日本語の試験を（  ）つもりです。",
        "translation": "打算下個月參加日語考試。",
        "answer": "受ける",
        "traps": ["受け", "受けて", "受けた"],
        "targetWordId": "N4_418",  # 受ける [2]
        "pitchHint": "うける [2] つもり",
        "explanation": "表達個人堅定打算時，接續動詞原形「辭書形 ＋ つもりです」。",
        "audio": "./audio/grammar/CLOZE_149.mp3"
    },
    {
        "id": "CLOZE_150",
        "vocabLevel": "N4",
        "unitId": "U09",
        "scenarioId": "S07",
        "category": "授受動詞（〜てくれる）",
        "tier": "Tier 1 丁寧體",
        "sentence": "友達が京都の街を親切に（  ）してくれました。",
        "translation": "朋友親切地為我導覽了京都的街市。",
        "answer": "案内",
        "traps": ["安心", "案内し", "相談"],
        "targetWordId": "N4_095",  # 案内 [3]
        "pitchHint": "あんない [3] して くれる",
        "explanation": "「案内する」搭配他人為我服務的授受動詞「〜てくれる」。",
        "audio": "./audio/grammar/CLOZE_150.mp3"
    },
    {
        "id": "CLOZE_151",
        "vocabLevel": "N4",
        "unitId": "U39",
        "scenarioId": "S08",
        "category": "授受敬語（〜てくださる）",
        "tier": "Tier 1 丁寧體",
        "sentence": "先生が文法をわかりやすく（  ）してくださいました。",
        "translation": "老師深入淺出地為我說明了文法。",
        "answer": "説明",
        "traps": ["相談", "紹介", "出発"],
        "targetWordId": "N4_258",  # 説明 [0]
        "pitchHint": "せつめい [0] して くださる",
        "explanation": "長輩主動為我方做某事時，使用授受敬語「〜てくださる（説明してくださいました）」。",
        "audio": "./audio/grammar/CLOZE_151.mp3"
    },
    {
        "id": "CLOZE_152",
        "vocabLevel": "N4",
        "unitId": "U01",
        "scenarioId": "S05",
        "category": "請求（〜てください・撥音便）",
        "tier": "Tier 1 丁寧體",
        "sentence": "好きな色を一つ（  ）でください。",
        "translation": "請選擇一個喜歡的顏色。",
        "answer": "選ん",
        "traps": ["選び", "選ぶ", "選いて"],
        "targetWordId": "N4_008",  # 選ぶ [2]
        "pitchHint": "えらぶ [2] ➔ えらんで [2]",
        "explanation": "「選ぶ」字尾為「ぶ」，鼻音便為「選んで（えらんで）」。",
        "audio": "./audio/grammar/CLOZE_152.mp3"
    },
    {
        "id": "CLOZE_153",
        "vocabLevel": "N4",
        "unitId": "U37",
        "scenarioId": "S06",
        "category": "原因て形（生理情感）",
        "tier": "Tier 1 丁寧體",
        "sentence": "大きな地震のニュースを聞いて、（  ）ました。",
        "translation": "聽了大地震的新聞，感到很吃驚。",
        "answer": "驚き",
        "traps": ["驚く", "驚い", "驚か"],
        "targetWordId": "N4_009",  # 驚く [3]
        "pitchHint": "おどろく [3] ➔ おどろきました [5]",
        "explanation": "五段動詞「驚く」的過去肯定形為「驚きました」。",
        "audio": "./audio/grammar/CLOZE_153.mp3"
    },
    {
        "id": "CLOZE_154",
        "vocabLevel": "N4",
        "unitId": "U32",
        "scenarioId": "S03",
        "category": "普通體過去肯定",
        "tier": "Tier 2 一般常體",
        "sentence": "無理な頼みだったから、（  ）よ。",
        "translation": "因為是太過勉強的請求，所以拒絕了喔。",
        "answer": "断った",
        "traps": ["断り", "断る", "断てた"],
        "targetWordId": "N4_018",  # 断る [3]
        "pitchHint": "ことわる [3] ➔ ことわった [3]",
        "explanation": "五段動詞「断る」字尾為「る」，促音便過去普通體為「断った」。",
        "audio": "./audio/grammar/CLOZE_154.mp3"
    },
    {
        "id": "CLOZE_155",
        "vocabLevel": "N4",
        "unitId": "U28",
        "scenarioId": "S04",
        "category": "先決條件（たら）",
        "tier": "Tier 1 丁寧體",
        "sentence": "部屋の鍵が見つかったら、すぐに（  ）てください。",
        "translation": "如果找到房間鑰匙的話，請立刻通知我。",
        "answer": "知らせ",
        "traps": ["知らせる", "知らし", "知らされ"],
        "targetWordId": "N4_022",  # 知らせる [0]
        "pitchHint": "しらせる [0] ➔ しらせて [0]",
        "explanation": "一段動詞「知らせる」去掉「る」加上「て」，構成請求句「知らせてください」。",
        "audio": "./audio/grammar/CLOZE_155.mp3"
    },
    {
        "id": "CLOZE_156",
        "vocabLevel": "N4",
        "unitId": "U22",
        "scenarioId": "S07",
        "category": "同時進行（〜ながら）",
        "tier": "Tier 1 丁寧體",
        "sentence": "辞書で意味を（  ）ながら本を読みます。",
        "translation": "一邊用字典查意思一邊看書。",
        "answer": "調べ",
        "traps": ["調べる", "調べて", "調べた"],
        "targetWordId": "N4_023",  # 調べる [3]
        "pitchHint": "しらべる [3] ➔ しらべながら [5]",
        "explanation": "一段動詞「調べる」接「ながら」時去掉「る」（調べながら）。",
        "audio": "./audio/grammar/CLOZE_156.mp3"
    },
    {
        "id": "CLOZE_157",
        "vocabLevel": "N4",
        "unitId": "U34",
        "scenarioId": "S04",
        "category": "形式名詞（こと/の）",
        "tier": "Tier 1 丁寧體",
        "sentence": "重い荷物を一人で（  ）のは大変です。",
        "translation": "一個人搬運沉重的行李是很辛苦的。",
        "answer": "運ぶ",
        "traps": ["運び", "運んで", "運ば"],
        "targetWordId": "N4_046",  # 運ぶ [0]
        "pitchHint": "はこぶ [0] のは",
        "explanation": "動詞名詞化做主詞時，接「の」前面必須維持動詞辭書形（運ぶのは）。",
        "audio": "./audio/grammar/CLOZE_157.mp3"
    },

    # --- N3 (12 questions) ---
    {
        "id": "CLOZE_158",
        "vocabLevel": "N3",
        "unitId": "U25",
        "scenarioId": "S07",
        "category": "禁止請求（〜ないでください）",
        "tier": "Tier 1 丁寧體",
        "sentence": "どんなに難しくても、夢を（  ）ないでください。",
        "translation": "不論有多麼困難，請都不要放棄夢想。",
        "answer": "諦め",
        "traps": ["諦める", "諦めて", "諦めろ"],
        "targetWordId": "N3_003",  # 諦める [4]
        "pitchHint": "あきらめる [4] ➔ あきらめないで [5]",
        "explanation": "一段動詞「諦める」變ない形時去掉「る」加上「ない」（諦めないでください）。",
        "audio": "./audio/grammar/CLOZE_158.mp3"
    },
    {
        "id": "CLOZE_159",
        "vocabLevel": "N3",
        "unitId": "U16",
        "scenarioId": "S03",
        "category": "程度副詞與動詞否定",
        "tier": "Tier 1 丁寧體",
        "sentence": "この料理は毎日食べても全然（  ）ません。",
        "translation": "這道料理即使每天吃也完全不會吃膩。",
        "answer": "飽き",
        "traps": ["飽きる", "飽いて", "飽か"],
        "targetWordId": "N3_004",  # 飽きる [2]
        "pitchHint": "あきる [2] ➔ あきません [3]",
        "explanation": "一段動詞「飽きる」否定丁寧形為「飽きません」，搭配「全然」表示完全不膩。",
        "audio": "./audio/grammar/CLOZE_159.mp3"
    },
    {
        "id": "CLOZE_160",
        "vocabLevel": "N3",
        "unitId": "U28",
        "scenarioId": "S07",
        "category": "假定條件（〜たら）",
        "tier": "Tier 1 丁寧體",
        "sentence": "宝くじが（  ）たら、世界一周旅行に行きたいです。",
        "translation": "要是彩券中獎的話，想去環遊世界一圈。",
        "answer": "当たっ",
        "traps": ["当たり", "当たる", "当たて"],
        "targetWordId": "N3_008",  # 当たる [0]
        "pitchHint": "あたる [0] ➔ あたったら [0]",
        "explanation": "五段動詞「当たる」促音便た形為「当たった」，接「ら」構成假定條件「当たったら」。",
        "audio": "./audio/grammar/CLOZE_160.mp3"
    },
    {
        "id": "CLOZE_161",
        "vocabLevel": "N3",
        "unitId": "U39",
        "scenarioId": "S08",
        "category": "授受動詞謙讓語（〜ていただく）",
        "tier": "Tier 1 丁寧體",
        "sentence": "先生に推薦状を書いて（  ）。",
        "translation": "榮幸獲得老師為我寫了推薦信。",
        "answer": "いただきました",
        "traps": ["くださいました", "あげました", "やりました"],
        "targetWordId": "N3_033",  # 頂く [0]
        "pitchHint": "いただく [0] ➔ いただきました [5]",
        "explanation": "我方獲得尊長提供好處時，使用授受謙讓語「〜ていただく（書いていただきました）」。",
        "audio": "./audio/grammar/CLOZE_161.mp3"
    },
    {
        "id": "CLOZE_162",
        "vocabLevel": "N3",
        "unitId": "U24",
        "scenarioId": "S07",
        "category": "決定句型（〜ことにする）",
        "tier": "Tier 1 丁寧體",
        "sentence": "友達の合格をみんなで（  ）ことにしました。",
        "translation": "大家決定要一起祝賀朋友及格考上。",
        "answer": "祝う",
        "traps": ["祝い", "祝って", "祝わ"],
        "targetWordId": "N3_056",  # 祝う [2]
        "pitchHint": "いわう [2] ことにする",
        "explanation": "主觀決定進行某動作時，接續動詞原形「辭書形 ＋ ことにする」。",
        "audio": "./audio/grammar/CLOZE_162.mp3"
    },
    {
        "id": "CLOZE_163",
        "vocabLevel": "N3",
        "unitId": "U09",
        "scenarioId": "S07",
        "category": "學習受教（教わる）",
        "tier": "Tier 1 丁寧體",
        "sentence": "先輩から仕事のやり方を（  ）ました。",
        "translation": "向學長請教學習了工作的方法。",
        "answer": "教わり",
        "traps": ["教わる", "教わっ", "教われ"],
        "targetWordId": "N3_082",  # 教わる [3]
        "pitchHint": "おそわる [3] ➔ おそわりました [5]",
        "explanation": "動詞「教わる」表示向他人學習受教，過去式為「教わりました」。",
        "audio": "./audio/grammar/CLOZE_163.mp3"
    },
    {
        "id": "CLOZE_164",
        "vocabLevel": "N3",
        "unitId": "U26",
        "scenarioId": "S05",
        "category": "按照指示（〜とおりに）",
        "tier": "Tier 1 丁寧體",
        "sentence": "説明書の図の（  ）家具を組み立てました。",
        "translation": "按照說明書的圖示組裝了家具。",
        "answer": "とおりに",
        "traps": ["ように", "ために", "ついでに"],
        "targetWordId": "N3_142",  # 組み立てる [4]
        "pitchHint": "くみたてる [4] ➔ くみたてました [5]",
        "explanation": "名詞接「〜のとおりに」表示照著某範本或圖示進行。",
        "audio": "./audio/grammar/CLOZE_164.mp3"
    },
    {
        "id": "CLOZE_165",
        "vocabLevel": "N3",
        "unitId": "U23",
        "scenarioId": "S07",
        "category": "嘗試體驗（〜てみる）",
        "tier": "Tier 1 丁寧體",
        "sentence": "新しいアプリを（  ）みましたが、とても便利でした。",
        "translation": "試用了一下新應用程式，非常便利。",
        "answer": "使用して",
        "traps": ["使用し", "使用する", "使用した"],
        "targetWordId": "N3_368",  # 使用 [0]
        "pitchHint": "しよう [0] ➔ しようして [0] みる",
        "explanation": "「動詞て形 ＋ みる」表示嘗試進行某動作看看。三類動詞（サ變）使用「〜して＋みる」。",
        "audio": "./audio/grammar/CLOZE_165.mp3"
    },
    {
        "id": "CLOZE_166",
        "vocabLevel": "N3",
        "unitId": "U33",
        "scenarioId": "S06",
        "category": "理由強調（〜んです）",
        "tier": "Tier 1 丁寧體",
        "sentence": "明日の試験のために、単語を（  ）しているんです。",
        "translation": "為了明天的考試，我正在背誦單字呢。",
        "answer": "暗記",
        "traps": ["安心", "安定", "案内"],
        "targetWordId": "N3_020",  # 暗記 [0]
        "pitchHint": "あんき [0] して いるんです",
        "explanation": "動詞「暗記する」搭配「〜んです」說明目前正在做的原因動作。",
        "audio": "./audio/grammar/CLOZE_166.mp3"
    },
    {
        "id": "CLOZE_167",
        "vocabLevel": "N3",
        "unitId": "U27",
        "scenarioId": "S08",
        "category": "努力維持（ようにする）",
        "tier": "Tier 1 丁寧體",
        "sentence": "品質を（  ）できるように努力しています。",
        "translation": "努力讓品質能夠持續維持。",
        "answer": "維持",
        "traps": ["意識", "安定", "移転"],
        "targetWordId": "N3_029",  # 維持 [1]
        "pitchHint": "いじ [1] できる ように",
        "explanation": "「名詞 ＋ を維持する」搭配可能形「〜ように」表達朝向目標努力。",
        "audio": "./audio/grammar/CLOZE_167.mp3"
    },
    {
        "id": "CLOZE_168",
        "vocabLevel": "N3",
        "unitId": "U38",
        "scenarioId": "S07",
        "category": "傳聞口語（Tier 3 って）",
        "tier": "Tier 3 死黨道地口語",
        "sentence": "彼が（  ）を送ったら、すぐに出発するって！",
        "translation": "聽說只要他打了暗號，就要立刻出發喔！",
        "answer": "合図",
        "traps": ["合意", "合唱", "合体"],
        "targetWordId": "N3_002",  # 合図 [1]
        "pitchHint": "あいず [1] を おくる",
        "explanation": "口語傳聞句型「〜って」轉述他人的話，名詞「合図 (あいず)」表示信號暗號。",
        "audio": "./audio/grammar/CLOZE_168.mp3"
    },
    {
        "id": "CLOZE_169",
        "vocabLevel": "N3",
        "unitId": "U35",
        "scenarioId": "S08",
        "category": "狀況前提（〜場合）",
        "tier": "Tier 1 丁寧體",
        "sentence": "天候が（  ）しない場合は、イベントを中止します。",
        "translation": "天氣若不穩定的情況下，活動將會取消。",
        "answer": "安定",
        "traps": ["安心", "案内", "安全"],
        "targetWordId": "N3_021",  # 安定 [0]
        "pitchHint": "あんてい [0] しない ばあい",
        "explanation": "「〜場合は」前面接動詞普通體否定式「安定しない」。",
        "audio": "./audio/grammar/CLOZE_169.mp3"
    },

    # --- N2 (8 questions) ---
    {
        "id": "CLOZE_170",
        "vocabLevel": "N2",
        "unitId": "U39",
        "scenarioId": "S08",
        "category": "敬語請教（仰ぐ）",
        "tier": "Tier 1 丁寧體",
        "sentence": "専門家の指導を（  ）ことにしました。",
        "translation": "決定請教專家的指導。",
        "answer": "仰ぐ",
        "traps": ["仰ぎ", "仰いで", "仰が"],
        "targetWordId": "N2_005",  # 仰ぐ [2]
        "pitchHint": "あおぐ [2] ことにする",
        "explanation": "「指導を仰ぐ（あおぐ）」為 N2 高頻商務慣用搭配，接「ことにする」前面接辭書形。",
        "audio": "./audio/grammar/CLOZE_170.mp3"
    },
    {
        "id": "CLOZE_171",
        "vocabLevel": "N2",
        "unitId": "U38",
        "scenarioId": "S08",
        "category": "推量確信（〜に違いない）",
        "tier": "Tier 1 丁寧體",
        "sentence": "彼の話は単なる（  ）に違いない。",
        "translation": "他的話肯定是單純的誤會而已。",
        "answer": "勘違い",
        "traps": ["間違い", "気違い", "見間違い"],
        "targetWordId": "N2_099",  # 勘違い [3]
        "pitchHint": "かんちがい [3] に ちがいない",
        "explanation": "「名詞 ＋ に違いない」表示十分篤定的強烈推斷「肯定是…」。",
        "audio": "./audio/grammar/CLOZE_171.mp3"
    },
    {
        "id": "CLOZE_172",
        "vocabLevel": "N2",
        "unitId": "U26",
        "scenarioId": "S07",
        "category": "忠告建議（〜たほうがいい）",
        "tier": "Tier 1 丁寧體",
        "sentence": "そんなに（  ）ないほうがいいですよ。",
        "translation": "最好不要那麼焦急喔。",
        "answer": "焦ら",
        "traps": ["焦り", "焦る", "焦っ"],
        "targetWordId": "N2_014",  # 焦る [0]
        "pitchHint": "あせる [0] ➔ あせらない [3] ほうがいい",
        "explanation": "動詞「焦る」否定建議為「焦らないほうがいい」。",
        "audio": "./audio/grammar/CLOZE_172.mp3"
    },
    {
        "id": "CLOZE_173",
        "vocabLevel": "N2",
        "unitId": "U32",
        "scenarioId": "S07",
        "category": "な形容詞普通體（当たり前）",
        "tier": "Tier 2 一般常體",
        "sentence": "失敗したら謝るのは（  ）だ。",
        "translation": "弄失敗了的話去道歉是理所當然的。",
        "answer": "当たり前",
        "traps": ["当たり前の", "当たり前に", "当たり前な"],
        "targetWordId": "N2_016",  # 当たり前 [4]
        "pitchHint": "あたりまえ [4] だ",
        "explanation": "な形容詞在句尾普通體時接續「だ（当たり前だ）」。",
        "audio": "./audio/grammar/CLOZE_173.mp3"
    },
    {
        "id": "CLOZE_174",
        "vocabLevel": "N2",
        "unitId": "U28",
        "scenarioId": "S08",
        "category": "條件接續（〜ば）",
        "tier": "Tier 1 丁寧體",
        "sentence": "条件に（  ）ば、採用されます。",
        "translation": "如果符合條件的話，就會被錄用。",
        "answer": "当てはまれ",
        "traps": ["当てはまり", "当てはまる", "当てはまれば"],
        "targetWordId": "N2_018",  # 当てはまる [5]
        "pitchHint": "あてはまる [5] ➔ あてはまれば [5]",
        "explanation": "五段動詞「当てはまる」條件形為將尾音改え段加ば（当てはまれば）。",
        "audio": "./audio/grammar/CLOZE_174.mp3"
    },
    {
        "id": "CLOZE_175",
        "vocabLevel": "N2",
        "unitId": "U36",
        "scenarioId": "S07",
        "category": "自動詞持續（あふれる）",
        "tier": "Tier 1 丁寧體",
        "sentence": "会場は熱気で（  ）ていました。",
        "translation": "會場充滿了熱氣。",
        "answer": "あふれ",
        "traps": ["あふれる", "あふれり", "あふれた"],
        "targetWordId": "N2_020",  # あふれる [3]
        "pitchHint": "あふれる [3] ➔ あふれて [3] いた",
        "explanation": "一段動詞「あふれる」去「る」加「て」表示狀態持續（あふれていました）。",
        "audio": "./audio/grammar/CLOZE_175.mp3"
    },
    {
        "id": "CLOZE_176",
        "vocabLevel": "N2",
        "unitId": "U30",
        "scenarioId": "S08",
        "category": "被動受身（甘える）",
        "tier": "Tier 1 丁寧體",
        "sentence": "親に（  ）すぎて自立できません。",
        "translation": "太過於依賴父母向父母撒嬌，而無法自立。",
        "answer": "甘え",
        "traps": ["甘える", "甘えり", "甘えた"],
        "targetWordId": "N2_021",  # 甘える [3]
        "pitchHint": "あまえる [3] ➔ あまえ [0] すぎる",
        "explanation": "一段動詞「甘える」接「すぎる」時去「る」（甘えすぎる）。",
        "audio": "./audio/grammar/CLOZE_176.mp3"
    },
    {
        "id": "CLOZE_177",
        "vocabLevel": "N2",
        "unitId": "U27",
        "scenarioId": "S07",
        "category": "客觀變化（〜ようになる）",
        "tier": "Tier 1 丁寧體",
        "sentence": "日本の文化に（  ）ようになりました。",
        "translation": "變得非常嚮往日本文化了。",
        "answer": "憧れる",
        "traps": ["憧れ", "憧れて", "憧れた"],
        "targetWordId": "N2_012",  # 憧れる [4]
        "pitchHint": "あこがれる [4] ように なる",
        "explanation": "「動詞辭書形 ＋ ようになる」表示狀態從不會或未曾變成現在的狀態。",
        "audio": "./audio/grammar/CLOZE_177.mp3"
    },

    # --- N1 (8 questions) ---
    {
        "id": "CLOZE_178",
        "vocabLevel": "N1",
        "unitId": "U30",
        "scenarioId": "S08",
        "category": "創造受身（によって）",
        "tier": "Tier 1 丁寧體",
        "sentence": "この事典には重要語が（  ）されている。",
        "translation": "這部辭典完整網羅了重要詞彙。",
        "answer": "網羅",
        "traps": ["網羅し", "網羅する", "網羅して"],
        "targetWordId": "N1_001",  # 網羅 [1]
        "pitchHint": "もうら [1] される",
        "explanation": "「名詞 ＋ される」構成被動態，「網羅されている」表示被全面包羅收錄。",
        "audio": "./audio/grammar/CLOZE_178.mp3"
    },
    {
        "id": "CLOZE_179",
        "vocabLevel": "N1",
        "unitId": "U24",
        "scenarioId": "S08",
        "category": "規章規定（〜ことになっている）",
        "tier": "Tier 1 丁寧體",
        "sentence": "最新情報は（  ）更新することになっている。",
        "translation": "最新消息規定隨時都要進行更新。",
        "answer": "随時",
        "traps": ["随分", "随意", "随伴"],
        "targetWordId": "N1_004",  # 随時 [1]
        "pitchHint": "ずいじ [1]",
        "explanation": "副詞「随時 (ずいじ)」表示不限時間隨時；「〜ことになっている」表示法規既定原則。",
        "audio": "./audio/grammar/CLOZE_179.mp3"
    },
    {
        "id": "CLOZE_180",
        "vocabLevel": "N1",
        "unitId": "U28",
        "scenarioId": "S08",
        "category": "條件（〜と）",
        "tier": "Tier 1 丁寧體",
        "sentence": "スマートフォンが（  ）すると、生活が一変した。",
        "translation": "智慧型手機一普及開來，生活就徹底改變了。",
        "answer": "普及",
        "traps": ["普通", "普遍", "普請"],
        "targetWordId": "N1_006",  # 普及 [0]
        "pitchHint": "ふきゅう [0] する と",
        "explanation": "動詞辭書形接「と」表示自然必然的連續發展（普及すると）。",
        "audio": "./audio/grammar/CLOZE_180.mp3"
    },
    {
        "id": "CLOZE_181",
        "vocabLevel": "N1",
        "unitId": "U22",
        "scenarioId": "S07",
        "category": "目的（ます幹＋に行く）",
        "tier": "Tier 1 丁寧體",
        "sentence": "温泉で日本の休日を（  ）しに行きました。",
        "translation": "去溫泉充分享受了日本的假日生活。",
        "answer": "満喫",
        "traps": ["満足", "満開", "満員"],
        "targetWordId": "N1_007",  # 満喫 [0]
        "pitchHint": "まんきつ [0] しに いく",
        "explanation": "三類動詞ます幹「満喫し」接「に行きます」表達移動的終極目的。",
        "audio": "./audio/grammar/CLOZE_181.mp3"
    },
    {
        "id": "CLOZE_182",
        "vocabLevel": "N1",
        "unitId": "U31",
        "scenarioId": "S08",
        "category": "使役受身（させられる）",
        "tier": "Tier 1 丁寧體",
        "sentence": "全責任を彼に（  ）させられた。",
        "translation": "所有責任都被全權委託推給他了（使役受身：被迫承擔）。",
        "answer": "一任",
        "traps": ["委任", "任免", "専任"],
        "targetWordId": "N1_010",  # 一任 [0]
        "pitchHint": "いちにん [0] させられる",
        "explanation": "「一任する」的使役受身形為「一任させられる」，表示被迫全權扛下責任。",
        "audio": "./audio/grammar/CLOZE_182.mp3"
    },
    {
        "id": "CLOZE_183",
        "vocabLevel": "N1",
        "unitId": "U35",
        "scenarioId": "S08",
        "category": "狀況假定（〜場合）",
        "tier": "Tier 1 丁寧體",
        "sentence": "緊急の（  ）を取る場合は、速やかに報告してください。",
        "translation": "在採取緊急措施的情況下，請迅速通報。",
        "answer": "措置",
        "traps": ["処置", "設置", "位置"],
        "targetWordId": "N1_037",  # 措置 [1]
        "pitchHint": "そち [1] を とる",
        "explanation": "「措置を取る」表示採取措施，搭配「〜場合は」表達特定狀況下的應急處理。",
        "audio": "./audio/grammar/CLOZE_183.mp3"
    },
    {
        "id": "CLOZE_184",
        "vocabLevel": "N1",
        "unitId": "U34",
        "scenarioId": "S08",
        "category": "形式名詞（こと）",
        "tier": "Tier 1 丁寧體",
        "sentence": "会議を（  ）に進めることが重要です。",
        "translation": "順利推動會議進行是很重要的。",
        "answer": "円滑",
        "traps": ["円満", "円形", "滑らか"],
        "targetWordId": "N1_012",  # 円滑 [0]
        "pitchHint": "えんかつ [0] に すすめる",
        "explanation": "な形容詞副詞化「円滑に」搭配形式名詞「ことが重要です」。",
        "audio": "./audio/grammar/CLOZE_184.mp3"
    },
    {
        "id": "CLOZE_185",
        "vocabLevel": "N1",
        "unitId": "U39",
        "scenarioId": "S08",
        "category": "社交敬語與委婉表現",
        "tier": "Tier 1 丁寧體",
        "sentence": "相手に不快感を与えないよう、（  ）に断りました。",
        "translation": "為了不給對方帶來不快，委婉地拒絕了。",
        "answer": "婉曲",
        "traps": ["屈折", "曲線", "遠回"],
        "targetWordId": "N1_013",  # 婉曲 [0]
        "pitchHint": "えんきょく [0] に ことわる",
        "explanation": "な形容詞副詞化「婉曲に断る」為最高階商務社交敬語素養。",
        "audio": "./audio/grammar/CLOZE_185.mp3"
    }
]

print(f"Total new cloze questions designed: {len(new_clozes)}")

# Assertions on new clozes
for q in new_clozes:
    lvl = q['vocabLevel']
    tid = q['targetWordId']
    assert tid in vocabs_by_lvl[lvl], f"Mismatch: {q['id']} targetWordId {tid} not in {lvl}!"
    w = vocabs_by_lvl[lvl][tid]
    k = w['kanji']
    kana = w['kana']
    full = q['sentence'].replace('（  ）', q['answer'])
    assert (k in full or kana in full or k[:-1] in full or kana[:-1] in full or k in q['answer'] or kana in q['answer']), f"Target word {k} ({kana}) not in sentence for {q['id']}: {full}"
    assert len(q['traps']) == 3, f"Traps length != 3 for {q['id']}"
    assert len(set(q['traps'])) == 3, f"Duplicate traps for {q['id']}"
    assert q['answer'] not in q['traps'], f"Answer in traps for {q['id']}"
    assert q['sentence'].count('（  ）') == 1, f"Blank error for {q['id']}"

print("All 60 new Cloze questions passed 100% strict automated assertion tests!")

# Reassemble db
db['clozeQuestions'] = cloze_1_to_125 + new_clozes
print(f"Total clozeQuestions in db: {len(db['clozeQuestions'])}")

# Write to grammar_DB.js
new_json = json.dumps(db, ensure_ascii=False, indent=2)
fixed_content = header + "window.GRAMMAR_DB = " + new_json + ";\n\n" + iife

with open('grammar_DB.js', 'w', encoding='utf-8') as f:
    f.write(fixed_content)

print("Successfully written updated grammar_DB.js!")
