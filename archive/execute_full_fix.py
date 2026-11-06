# -*- coding: utf-8 -*-
"""
execute_full_fix.py
Applies all fixes required by grammar_review_report_v2.md:
1. Strict morpheme-level vocabIds matching for all examples in U01~U39 using fugashi.
2. Enrich U08 with 3-Step Decision Tree (三步判定樹與步驟 1/2/3).
3. Enrich U33 with Section 4 (〜と思う／〜だろうと思う, Goal #91) + examples.
4. Enrich U34 with Section 4 (名詞修飾節／連體修飾, Goal #96) + examples.
5. Enrich U38 with Section 4 (傳聞三大層級, Goals #92/#121) + examples.
6. Fix U18 and U31 specific examples to prevent false matches.
7. Balance and accurately label Tiers (Tier 1, Tier 2, Tier 3) across Cloze questions.
"""
import json
import re
import fugashi

tagger = fugashi.Tagger()

# 1. Load Vocabularies
vocabs = {}
vocabs_by_lvl = {'N5': {}, 'N4': {}, 'N3': {}, 'N2': {}, 'N1': {}}
for lvl in ['N5', 'N4', 'N3', 'N2', 'N1']:
    with open(f'vocab_{lvl}.js', 'r', encoding='utf-8') as f:
        text = f.read()
    s = text.find('[')
    e = text.rfind(']')
    arr = json.loads(text[s:e+1])
    for w in arr:
        vocabs[w['id']] = (lvl, w)
        vocabs_by_lvl[lvl][w['id']] = w

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

# 3. Enhance U08 with 3-Step Decision Tree (Goal #45)
u08 = next(u for u in db['vaultUnits'] if u['id'] == 'U08')
u08['sections'][0] = {
    "subtitle": "🏛️ 前置知識：動詞三大隊伍分類與 3 步判定樹（學習目標 #45）",
    "mindset": "面對任何一個未知日語動詞辭書形，只需透過 3 步判定樹（三步判定法）即可 100% 正確分類！",
    "decisionTree": {
        "title": "動詞三步判定法流程（3-Step Decision Tree）",
        "step1": "【步驟 1：檢查是否為第三類不規則動詞】先看是否為「する」或「来る（くる）」，或者是「名詞＋する」（如：勉強する）。若是 ➔ 直接歸入第三類（III 類 / 不規則動詞）。",
        "step2": "【步驟 2：檢查字尾是否為「る」】若不是「る」結尾（例如：書く、話す、待つ、死ぬ、呼ぶ、飲む、買う）➔ 100% 絕對是第一類動詞（I 類 / 五段動詞）！",
        "step3": "【步驟 3：字尾是「る」時，看「る」的前一個假名發音】如果「る」的前一個音落在「あ段、う段、お段」（如：ある、終わる、取る）➔ 100% 是第一類（五段）；如果落在「い段」或「え段」（如：起きる、食べる、見る）➔ 99% 屬於第二類動詞（II 類 / 一段動詞）！",
        "exceptions": "⚠️ 7 大必考例外動詞（外表像一段，骨子裡是五段）：『帰る(かえる)』、『入る(はいる)』、『走る(はしる)』、『切る(きる)』、『知る(しる)』、『要る(いる)』、『減る(へる)』。這 7 個字尾雖然是「いる／える」，但變形時走五段路線（帰らない、入ります、走った、切れば）。"
    },
    "points": [
        "第一類（五段動詞 / I 類）：字尾落在 50 音的「う 段」。變形時會在「あ・い・う・え・お」五個音階間跳躍。",
        "第二類（一段動詞 / II 類）：字尾一定是「る」，且「る」的前一個音為 i 或 e 的發音（例：食べる、見る）。變形時最簡單，幾乎都是直接去「る」。",
        "第三類（不規則動詞 / III 類）：只有兩個——する（做）與 来る（くる/來）。"
    ],
    "warnings": [
        "⚠️ 7 大一段外表五段心必考例外：帰る、入る、走る、切る、知る、要る、減る…變形必須依五段法則！"
    ]
}

# 4. Enhance U33 with Section 4 (Goal #91)
u33 = next(u for u in db['vaultUnits'] if u['id'] == 'U33')
if len(u33['sections']) == 3:
    u33['sections'].append({
        "subtitle": "💭 4. 感想・想法與推測：〜と思う／〜だろうと思う（學習目標 #91）",
        "mindset": "表達第一人稱當下的思考、意見或推斷。委婉推測可用「〜だろうと思う」。",
        "formula": "意見想法：[普通體] ＋ と思います / 推測判斷：[普通體] ＋ だろうと思います",
        "points": [
            "第一人稱「我覺得…」：[普通體] ＋ と思う / と思います（名詞/な形容詞現在肯定保留「だ」：雨だと思う）。",
            "委婉推測「我想大概…吧」：[普通體] ＋ だろうと思う（名詞/な形容詞直接加 だろう：合格するだろうと思う）。"
        ],
        "examples": [
            {
                "ja": "明日はいい天気になると思います。",
                "zh": "我覺得明天會變成好天氣。（學習目標 #91：意見發表）",
                "vocabIds": []
            },
            {
                "ja": "彼は会議に遅れるだろうと思います。",
                "zh": "我想他大概會開會遲到吧。（學習目標 #91：委婉推測）",
                "vocabIds": []
            }
        ]
    })

# 5. Enhance U34 with Section 4 (Goal #96)
u34 = next(u for u in db['vaultUnits'] if u['id'] == 'U34')
if len(u34['sections']) == 3:
    u34['sections'].append({
        "subtitle": "🔗 4. 名詞修飾節（連體修飾子句）：修飾名詞的接續原則（學習目標 #96）",
        "mindset": "日語修飾名詞時，整個修飾子句永遠放在名詞前面，且子句動詞必須普通體化。子句主詞助詞「が」常代換為「の」。",
        "formula": "[修飾子句（動詞普通體/形容詞/名詞＋の）] ＋ [被修飾名詞]",
        "points": [
            "修飾名詞絕對不可用「ます形」，必須用「普通體」（辞書形、た形、ない形、ている形）。",
            "修飾節內部的主詞，助詞「が」可以自然變換為「の」（私が買った本 ➔ 私の買った本）。"
        ],
        "examples": [
            {
                "ja": "これは私が昨日買った本です。",
                "zh": "這是我昨天買的書。（動詞過去常體修飾名詞，學習目標 #96）",
                "vocabIds": []
            },
            {
                "ja": "あそこで眼鏡をかけている人は田中さんです。",
                "zh": "在那裡戴著眼鏡的人是田中先生。（動詞進行式修飾名詞，學習目標 #96）",
                "vocabIds": []
            }
        ]
    })

# 6. Enhance U38 with Section 4 (Goals #92 & #121)
u38 = next(u for u in db['vaultUnits'] if u['id'] == 'U38')
if len(u38['sections']) == 3:
    u38['sections'].append({
        "subtitle": "📢 4. 傳聞三大層級實戰對決：そうです vs と言っていました vs って（學習目標 #92、#121）",
        "mindset": "轉述他人情報時，根據社交場合與訊息來源可靠度，精確選擇三大傳聞層級！",
        "formula": "1. 權威客觀：[普通體] ＋ そうです / 2. 轉述發言：[普通體] ＋ と言っていました / 3. 道地口語：[普通體] ＋ って",
        "points": [
            "正式報導／權威情報：[普通體] ＋ そうです（天氣預報、新聞、書面報導）。",
            "轉述特定人物原話：[普通體] ＋ と言っていました（某人之前親口說過…，學習目標 #92）。",
            "死黨親友道地極口語：[普通體] ＋ って（聽說…喔！日常縮略轉述，學習目標 #121）。"
        ],
        "examples": [
            {
                "ja": "部長は明日出張すると言っていました。",
                "zh": "部長之前說過明天要出差。（轉述特定發言，學習目標 #92）",
                "vocabIds": []
            },
            {
                "ja": "明日は午後から雨が降るって！",
                "zh": "聽說明天下午開始會下雨喔！（死黨道地口語傳聞，學習目標 #121）",
                "vocabIds": []
            }
        ]
    })

# 7. Fix U18 and U31 specific examples
u18 = next(u for u in db['vaultUnits'] if u['id'] == 'U18')
u18['sections'][0]['examples'][1]['ja'] = "ロビーに田中先生がいますよ。"
u18['sections'][0]['examples'][1]['zh'] = "大廳有田中老師在喔。"

u31 = next(u for u in db['vaultUnits'] if u['id'] == 'U31')
u31['sections'][1]['examples'][1]['ja'] = "会社で日曜日に仕事をさせられました。"
u31['sections'][1]['examples'][1]['zh'] = "在公司星期日被迫做了工作。"

# 8. Morpheme-level strict vocabId matcher
def get_strict_vocab_ids(ja):
    tokens = tagger(ja)
    targets = []
    for w in tokens:
        pos = w.feature.pos1
        if pos in ['助詞', '助動詞', '補助記号', '記号']:
            continue
        orthBase = getattr(w.feature, 'orthBase', None) or w.surface
        lemma = (getattr(w.feature, 'lemma', None) or w.surface).split('-')[0]
        targets.append({
            'surface': w.surface,
            'orthBase': orthBase,
            'lemma': lemma,
            'pos': pos
        })

    matched = []
    seen = set()

    # special handling
    if 'おかし' in ja and 'N4_078' in vocabs:
        matched.append(('N4_078', 'おかしい', 'N4', 40))
        seen.add('N4_078')

    for vid, (lvl, w) in vocabs.items():
        k = w['kanji']
        kana = w['kana']
        notes = w.get('notes', '')
        cats = w.get('categories', [])
        all_desc = notes + ' ' + ' '.join(cats)
        has_hiragana_ending = ('\u3040' <= k[-1] <= '\u309f') if len(k) > 0 else False
        is_inflecting_verb = ('動詞' in all_desc) and has_hiragana_ending
        is_adj_i = ('い形容詞' in all_desc or ('形容詞' in all_desc and 'な形容詞' not in all_desc)) and k.endswith('い')
        is_adj_na = 'な形容詞' in notes
        has_kanji = (k != kana)

        hit = False
        for t in targets:
            s = t['surface']
            ob = t['orthBase']
            l = t['lemma']
            p = t['pos']

            if is_inflecting_verb:
                if p == '動詞':
                    if k in [ob, l] or kana in [ob, l] or s in [k, kana]:
                        hit = True
            elif is_adj_i:
                if p in ['形容詞']:
                    if k in [ob, l] or kana in [ob, l] or s in [k, kana]:
                        hit = True
            elif is_adj_na:
                if p in ['形状詞', '名詞']:
                    if k in [ob, l] or kana in [ob, l] or k == s:
                        hit = True
            else:
                # Nouns (including suru-nouns), adverbs, pronouns
                if p in ['名詞', '代名詞', '副詞', '連体詞', '感動詞']:
                    if has_kanji:
                        if k in [s, ob, l]:
                            hit = True
                    else:
                        if kana in [s, ob, l]:
                            hit = True
            if hit:
                break

        if hit and vid not in seen:
            seen.add(vid)
            lvl_score = {'N5': 5, 'N4': 4, 'N3': 3, 'N2': 2, 'N1': 1}[lvl]
            matched.append((vid, k, lvl, len(k) * 10 + lvl_score))

    matched.sort(key=lambda x: -x[3])
    return [m[0] for m in matched[:4]]

# Update all vaultUnits examples with strict vocabIds
for u in db['vaultUnits']:
    for sec in u['sections']:
        for ex in sec.get('examples', []):
            ex['vocabIds'] = get_strict_vocab_ids(ex['ja'])

# 9. Update Cloze Questions Tiers to accurately reflect linguistic styles
# CLOZE_126~CLOZE_185
for q in db['clozeQuestions']:
    cid = q['id']
    if int(cid.replace('CLOZE_', '')) >= 126:
        s = q['sentence'].replace('（  ）', q['answer'])
        # Determine authentic tier
        if s.endswith('って！') or s.endswith('よ。') or s.endswith('ね。') or s.endswith('よ！') or s.endswith('ったよ。') or 'って！' in s:
            q['tier'] = 'Tier 3 死黨道地口語'
        elif s.endswith('だ。') or s.endswith('いる。') or s.endswith('ある。') or s.endswith('た。') or s.endswith('ない。') or s.endswith('れる。') or s.endswith('一変した。') or s.endswith('させられた。') or s.endswith('重要だ。'):
            q['tier'] = 'Tier 2 一般常體'
        else:
            q['tier'] = 'Tier 1 丁寧體'

print("Updated Cloze tiers.")

# Save updated grammar_DB.js
new_json = json.dumps(db, ensure_ascii=False, indent=2)
fixed_content = header + "window.GRAMMAR_DB = " + new_json + ";\n\n" + iife

with open('grammar_DB.js', 'w', encoding='utf-8') as f:
    f.write(fixed_content)

print("Saved updated grammar_DB.js successfully!")
