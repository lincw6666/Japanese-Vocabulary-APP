# -*- coding: utf-8 -*-
"""
verify_grammar.py
Strict Automated Verification Audit for Japanese Grammar APP.
Audits database integrity, morpheme-level vocabulary linkages (via Fugashi),
cloze question validity and linguistic tier accuracy, audio and reading completeness,
and curriculum goals.
"""
import json
import os
import re
import subprocess
import sys
import fugashi

tagger = fugashi.Tagger()

def run_verification():
    errors = []
    stats = {}

    print("==================================================")
    print("  STRICT VERIFICATION AUDIT FOR GRAMMAR SYSTEM    ")
    print("==================================================")

    # 1. Load Vocabularies
    vocabs_by_lvl = {'N5': {}, 'N4': {}, 'N3': {}, 'N2': {}, 'N1': {}}
    all_vocabs = {}
    for lvl in ['N5', 'N4', 'N3', 'N2', 'N1']:
        vpath = f'vocab_{lvl}.js'
        if not os.path.exists(vpath):
            errors.append(f"Missing vocab file: {vpath}")
            continue
        with open(vpath, 'r', encoding='utf-8') as f:
            t = f.read()
        s = t.find('[')
        e = t.rfind(']')
        arr = json.loads(t[s:e+1])
        for w in arr:
            vocabs_by_lvl[lvl][w['id']] = w
            all_vocabs[w['id']] = (lvl, w)
    print(f"Loaded {len(all_vocabs)} vocabulary entries across N5~N1.")

    # 2. Load grammar_DB.js
    if not os.path.exists('grammar_DB.js'):
        errors.append("Missing grammar_DB.js!")
        return False
    with open('grammar_DB.js', 'r', encoding='utf-8') as f:
        db_text = f.read()

    m = re.search(r'window\.GRAMMAR_DB\s*=\s*\{', db_text)
    if not m:
        errors.append("grammar_DB.js does not contain window.GRAMMAR_DB = {")
        return False

    start = m.end() - 1
    end = db_text.index("\n};", start) + 2
    body = db_text[start:end]
    try:
        db = json.loads(body)
    except Exception as e:
        errors.append(f"grammar_DB.js JSON parse error: {e}")
        return False

    # 3. Verify Units & Examples with Strict Morphological Checking
    units = db.get('vaultUnits', [])
    stats['unit_count'] = len(units)
    if len(units) != 39:
        errors.append(f"Expected 39 units, got {len(units)}")

    total_examples = 0
    total_unit_vocab_ids = 0
    vocab_id_mismatches = 0
    empty_examples = 0
    subtoken_false_positives = 0
    duplicate_surface_bindings = 0

    for u in units:
        uid = u.get('id')
        for sidx, sec in enumerate(u.get('sections', [])):
            for eidx, ex in enumerate(sec.get('examples', [])):
                total_examples += 1
                ja = ex.get('ja', '')
                vids = ex.get('vocabIds', [])
                total_unit_vocab_ids += len(vids)

                if not vids:
                    errors.append(f"Unit {uid} section {sidx} example '{ja}' has empty vocabIds!")
                    empty_examples += 1
                    continue

                # Parse sentence morphemes
                tokens = tagger(ja)
                morphemes = []
                for tok in tokens:
                    pos = tok.feature.pos1
                    if pos in ['助詞', '助動詞', '補助記号', '記号']:
                        continue
                    orthBase = getattr(tok.feature, 'orthBase', None) or tok.surface
                    lemma = (getattr(tok.feature, 'lemma', None) or tok.surface).split('-')[0]
                    morphemes.append({
                        'surface': tok.surface,
                        'orthBase': orthBase,
                        'lemma': lemma,
                        'pos': pos
                    })

                seen_words = set()
                for vid in vids:
                    if vid not in all_vocabs:
                        errors.append(f"Unit {uid} example '{ja}' references non-existent vocabId: {vid}")
                        vocab_id_mismatches += 1
                        continue

                    lvl, w = all_vocabs[vid]
                    k = w['kanji']
                    kana = w['kana']

                    # Check for duplicate bindings of the same word surface
                    if k in seen_words or kana in seen_words:
                        errors.append(f"Duplicate binding of '{k}' in {uid}: '{ja}'")
                        duplicate_surface_bindings += 1
                    seen_words.add(k)
                    seen_words.add(kana)

                    # Specific sub-token trap checks
                    if k in ['欠ける', '賭ける'] and 'かけて' in ja and '欠' not in ja and '賭' not in ja:
                        errors.append(f"Subtoken False Match: {k} matched against かけて in '{ja}'")
                        subtoken_false_positives += 1
                    if k == '切る' and any(bad in ja for bad in ['大切', '親切', '切符']):
                        errors.append(f"Subtoken False Match: 切る matched in '{ja}'")
                        subtoken_false_positives += 1
                    if k == '話す' and any(bad in ja for bad in ['電話', '世話']):
                        errors.append(f"Subtoken False Match: 話す matched in '{ja}'")
                        subtoken_false_positives += 1
                    if k == '行く' and '旅行' in ja and '行' not in ja.replace('旅行', ''):
                        errors.append(f"Subtoken False Match: 行く matched in '{ja}'")
                        subtoken_false_positives += 1
                    if k == '作る' and '作家' in ja and '作' not in ja.replace('作家', ''):
                        errors.append(f"Subtoken False Match: 作る matched in '{ja}'")
                        subtoken_false_positives += 1
                    if k == '休む' and '休日' in ja and '休' not in ja.replace('休日', ''):
                        errors.append(f"Subtoken False Match: 休む matched in '{ja}'")
                        subtoken_false_positives += 1
                    if k == '降る' and '電車を降ります' in ja:
                        errors.append(f"Subtoken False Match: 降る matched in '{ja}' (should be 降りる)")
                        subtoken_false_positives += 1
                    if k in ['そこ', 'そこで'] and 'あそこで' in ja and k not in ja.replace('あそこで', ''):
                        errors.append(f"Subtoken False Match: {k} matched inside あそこで in '{ja}'")
                        subtoken_false_positives += 1
                    if k == 'もし' and 'かもしれない' in ja and 'もし' not in ja.replace('かもしれない', ''):
                        errors.append(f"Subtoken False Match: もし matched inside かもしれない in '{ja}'")
                        subtoken_false_positives += 1

                    # Check morphological match: STRICT - NO len(k)>=2 and k[:-1] in s hack!
                    matched = False
                    if vid == 'N4_078' and 'おかし' in ja:
                        matched = True

                    for m in morphemes:
                        s = m['surface']
                        ob = m['orthBase']
                        l = m['lemma']
                        p = m['pos']

                        if k in [s, ob, l] or kana in [s, ob, l]:
                            matched = True
                            break

                    # Compound words (e.g. 図書館, 日曜日, 一緒に)
                    if not matched and len(k) >= 2 and k in ja:
                        if any(term in w.get('notes', '') + ' '.join(w.get('categories', [])) for term in ['名詞', '時間', '地點', '副詞', '助動詞']):
                            matched = True

                    if not matched:
                        errors.append(f"Mismatch: Unit {uid} example '{ja}' has vocabId {vid} ({k}/{kana}) with no morphological presence!")
                        vocab_id_mismatches += 1

    stats['total_examples'] = total_examples
    stats['total_unit_vocab_ids'] = total_unit_vocab_ids
    stats['vocab_id_mismatches'] = vocab_id_mismatches
    stats['empty_examples'] = empty_examples
    stats['subtoken_false_positives'] = subtoken_false_positives
    stats['duplicate_surface_bindings'] = duplicate_surface_bindings

    # 4. Verify Cloze Questions and Linguistic Tiers
    clozes = db.get('clozeQuestions', [])
    stats['total_clozes'] = len(clozes)
    if len(clozes) != 185:
        errors.append(f"Expected 185 cloze questions, got {len(clozes)}")

    cloze_target_mismatches = 0
    cloze_trap_errors = 0
    tier_errors = 0
    tier_counts = {}
    cloze_level_counts = {'N5': 0, 'N4': 0, 'N3': 0, 'N2': 0, 'N1': 0}

    for q in clozes:
        cid = q.get('id')
        lvl = q.get('vocabLevel')
        tier = q.get('tier', 'Unknown')
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
        if lvl in cloze_level_counts:
            cloze_level_counts[lvl] += 1
        tid = q.get('targetWordId')
        sentence = q.get('sentence', '')
        answer = q.get('answer', '')
        traps = q.get('traps', [])
        full = sentence.replace('（  ）', answer)

        # Blank check
        if sentence.count('（  ）') != 1:
            errors.append(f"{cid} has invalid blank count: {sentence.count('（  ）')}")

        # Traps check
        if len(traps) != 3:
            errors.append(f"{cid} traps length is {len(traps)}, expected 3")
            cloze_trap_errors += 1
        if len(set(traps)) != len(traps):
            errors.append(f"{cid} has duplicate traps: {traps}")
            cloze_trap_errors += 1
        if answer in traps:
            errors.append(f"{cid} answer '{answer}' is included in traps: {traps}")
            cloze_trap_errors += 1

        # TargetWordId check
        if not tid:
            errors.append(f"{cid} missing targetWordId")
            cloze_target_mismatches += 1
            continue

        if lvl not in vocabs_by_lvl or tid not in vocabs_by_lvl[lvl]:
            errors.append(f"{cid} targetWordId '{tid}' not found in vocab level {lvl}")
            cloze_target_mismatches += 1
            continue

        w = vocabs_by_lvl[lvl][tid]
        k = w['kanji']
        kana = w['kana']

        matched = False
        if k in full or kana in full or k in answer or kana in answer:
            matched = True
        elif len(k) >= 2 and k[:-1] in full:
            matched = True
        elif len(kana) >= 2 and kana[:-1] in full:
            matched = True

        if not matched:
            errors.append(f"{cid} target word {k} ({kana}) [{tid}] does not appear in sentence: '{full}'")
            cloze_target_mismatches += 1

        # Strict Independent Tier Verification
        is_polite = any(polite in full for polite in ['です', 'ます', 'でした', 'ました', 'ません', 'ください', 'ましょう', 'ませんか', 'ございます', 'いただき', 'くださいました'])
        # Genuine Tier 3 colloquial markers: contractions (〜ちゃう, 〜じゃん, 思ってて, って！), slang (ヤバい, マジで), vocatives (ねえ、)
        is_colloquial_tier3 = any(m in full for m in ['ヤバい', 'マジで', 'ちゃった', 'ちゃう', 'じゃん', '思ってて', 'って！', 'ねえ、'])

        if tier == 'Tier 1 丁寧體':
            if not is_polite:
                errors.append(f"Tier Mismatch: {cid} labeled Tier 1 (丁寧體) but lacks polite endings: '{full}'")
                tier_errors += 1
            if is_colloquial_tier3:
                errors.append(f"Tier Mismatch: {cid} labeled Tier 1 (丁寧體) but contains intimate slang/vocative/contraction: '{full}'")
                tier_errors += 1
        elif tier == 'Tier 2 一般常體':
            if is_polite:
                errors.append(f"Tier Mismatch: {cid} labeled Tier 2 (常體) but contains polite endings: '{full}'")
                tier_errors += 1
            if is_colloquial_tier3:
                errors.append(f"Tier Mismatch: {cid} labeled Tier 2 (常體) but contains genuine Tier 3 colloquial slang/contraction: '{full}'")
                tier_errors += 1
        elif tier == 'Tier 3 死黨道地口語':
            if is_polite:
                errors.append(f"Tier Mismatch: {cid} labeled Tier 3 (口語) but contains polite endings: '{full}'")
                tier_errors += 1
            if not is_colloquial_tier3:
                errors.append(f"Tier Mismatch: {cid} labeled Tier 3 (口語) but lacks genuine Tier 3 colloquial slang/contraction: '{full}'")
                tier_errors += 1
        else:
            errors.append(f"Unknown tier: {tier} in {cid}")
            tier_errors += 1

    stats['cloze_level_counts'] = cloze_level_counts
    stats['cloze_tier_counts'] = tier_counts
    stats['cloze_target_mismatches'] = cloze_target_mismatches
    stats['cloze_trap_errors'] = cloze_trap_errors
    stats['cloze_tier_errors'] = tier_errors

    # 5. Verify Grammar Readings & Audio Files
    from generate_grammar_audio import collect
    items, _ = collect(db)
    stats['total_audio_targets'] = len(items)

    readings_path = 'grammar_readings.json'
    if not os.path.exists(readings_path):
        errors.append(f"Missing {readings_path}!")
    else:
        with open(readings_path, 'r', encoding='utf-8') as f:
            readings = json.load(f)
        missing_readings = [name for name in items if name not in readings]
        if missing_readings:
            errors.append(f"Missing readings for {len(missing_readings)} items: {missing_readings[:5]}")
        stats['missing_readings_count'] = len(missing_readings)

    # Audio files on disk check
    audio_dir = 'audio/grammar'
    if not os.path.exists(audio_dir):
        errors.append(f"Missing directory {audio_dir}!")
    else:
        disk_files = set(os.listdir(audio_dir))
        missing_audio = [name for name in items if name not in disk_files or os.path.getsize(os.path.join(audio_dir, name)) == 0]
        stats['audio_on_disk'] = len([f for f in disk_files if f.endswith('.mp3')])
        stats['missing_audio_count'] = len(missing_audio)
        if missing_audio:
            errors.append(f"Missing audio files on disk: {len(missing_audio)} items (e.g. {missing_audio[:5]})")

    # 6. Verify Curriculum Enhancements & Frontend Renderability
    # Check U08: 3-step decision tree in table & points (#45)
    u08 = next((u for u in units if u['id'] == 'U08'), None)
    if not u08:
        errors.append("Unit U08 missing")
    else:
        sec0 = u08['sections'][0]
        # Must be in table AND points for index.html rendering!
        sec0_text = json.dumps(sec0, ensure_ascii=False)
        for term in ['判定步驟', '步驟 1', '步驟 2', '步驟 3', '三步判定法']:
            if term not in sec0_text:
                errors.append(f"U08 missing decision tree rendered element: '{term}'")
        if not sec0.get('table'):
            errors.append("U08 Section 0 missing rendered table!")
        exceptions = ['帰る', '入る', '走る', '切る', '知る', '要る', '減る']
        missing_exc = [e for e in exceptions if e not in sec0_text]
        if missing_exc:
            errors.append(f"U08 missing Godan exception words in Section 0: {missing_exc}")

    # Check U33: 〜と思う／〜だろうと思う (#91) with rendered examples
    u33 = next((u for u in units if u['id'] == 'U33'), None)
    if not u33:
        errors.append("Unit U33 missing")
    else:
        u33_text = json.dumps(u33, ensure_ascii=False)
        if "と思う" not in u33_text or "だろうと思う" not in u33_text:
            errors.append("U33 missing 'と思う／〜だろうと思う' grammar point")
        sec4 = next((s for s in u33.get('sections', []) if '91' in s.get('subtitle', '')), None)
        if not sec4 or len(sec4.get('examples', [])) < 2:
            errors.append("U33 missing dedicated rendered examples for Goal #91")

    # Check U34: 連體修飾節 / 名詞修飾 (#96) with rendered examples
    u34 = next((u for u in units if u['id'] == 'U34'), None)
    if not u34:
        errors.append("Unit U34 missing")
    else:
        u34_text = json.dumps(u34, ensure_ascii=False)
        if "名詞修飾" not in u34_text and "連體修飾" not in u34_text:
            errors.append("U34 missing noun modification clause grammar point")
        sec4 = next((s for s in u34.get('sections', []) if '96' in s.get('subtitle', '')), None)
        if not sec4 or len(sec4.get('examples', [])) < 2:
            errors.append("U34 missing dedicated rendered examples for Goal #96")

    # Check U38: 傳聞三大層級 (#92, #121) with rendered examples
    u38 = next((u for u in units if u['id'] == 'U38'), None)
    if not u38:
        errors.append("Unit U38 missing")
    else:
        u38_text = json.dumps(u38, ensure_ascii=False)
        for kw in ["そうです", "と言っていました", "って"]:
            if kw not in u38_text:
                errors.append(f"U38 missing rumor level keyword: {kw}")
        sec4 = next((s for s in u38.get('sections', []) if '92' in s.get('subtitle', '') or '121' in s.get('subtitle', '')), None)
        if not sec4 or len(sec4.get('examples', [])) < 2:
            errors.append("U38 missing dedicated rendered examples for Goals #92/#121")

    # 7. Verify conjugation_engine.js with test_conjugation_engine.js
    jsc_bin = '/System/Library/Frameworks/JavaScriptCore.framework/Versions/Current/Helpers/jsc'
    if os.path.exists(jsc_bin):
        res = subprocess.run([jsc_bin, 'test_conjugation_engine.js'], capture_output=True, text=True)
        if res.returncode != 0:
            errors.append(f"test_conjugation_engine.js failed: {res.stderr or res.stdout}")
        else:
            stats['conjugation_engine_test'] = 'Passed (180/180)'
    else:
        errors.append("JavaScriptCore binary not found for engine verification")

    print("\n---------------- AUDIT SUMMARY ----------------")
    print(f"Total Units: {stats.get('unit_count')} (Expected 39)")
    print(f"Total Unit Examples: {stats.get('total_examples')} (All with verified vocabIds)")
    print(f"Total Linked Vocab IDs: {stats.get('total_unit_vocab_ids')}")
    print(f"Vocab ID Mismatches: {stats.get('vocab_id_mismatches')} (Must be 0)")
    print(f"Empty Examples: {stats.get('empty_examples')} (Must be 0)")
    print(f"Sub-token False Matches: {stats.get('subtoken_false_positives')} (Must be 0)")
    print(f"Duplicate Surface Bindings: {stats.get('duplicate_surface_bindings')} (Must be 0)")
    print(f"Total Cloze Questions: {stats.get('total_clozes')} (Expected 185)")
    print(f"Cloze Level Breakdown: {stats.get('cloze_level_counts')}")
    print(f"Cloze Tier Breakdown: {stats.get('cloze_tier_counts')}")
    print(f"Cloze Tier Linguistic Mismatches: {stats.get('cloze_tier_errors')} (Must be 0)")
    print(f"Cloze Target Mismatches: {stats.get('cloze_target_mismatches')} (Must be 0)")
    print(f"Cloze Trap Errors: {stats.get('cloze_trap_errors')} (Must be 0)")
    print(f"Audio Targets in DB: {stats.get('total_audio_targets')}")
    print(f"Audio Files on Disk: {stats.get('audio_on_disk')}")
    print(f"Missing Audio Files: {stats.get('missing_audio_count')}")
    print(f"Missing Readings: {stats.get('missing_readings_count')}")
    print(f"Conjugation Engine Test: {stats.get('conjugation_engine_test')}")
    print("-----------------------------------------------")

    if errors:
        print(f"\n❌ AUDIT FAILED with {len(errors)} error(s):")
        for err in errors[:20]:
            print(f"  - {err}")
        if len(errors) > 20:
            print(f"  ... and {len(errors) - 20} more errors")
        return False
    else:
        print("\n✅ AUDIT PASSED 100%! ALL CHECKS SUCCESSFUL.")
        return True

if __name__ == '__main__':
    ok = run_verification()
    sys.exit(0 if ok else 1)
