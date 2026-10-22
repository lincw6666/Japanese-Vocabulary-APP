/* =============================================================================
 * conjugation_engine.js —  詞類活用變化引擎 (ConjugationEngine)
 * 掛載位置：window.ConjugationEngine
 *
 * 直接讀取前端 currentVocabList（隨側邊欄 N1~N5 勾選連動）的單字，依詞性說明
 * （第一類動詞 / 第二類動詞 / 第三類動詞 / い形容詞 / な形容詞 / 名詞）自動：
 *   1. classify(word)            ➔ 判斷詞性與活用種類（含沒有標註時的推斷）
 *   2. conjugate(word, formKey)  ➔ 產生活用結果
 *   3. makeQuestion(word, form)  ➔ 產生 1 個正解 ＋ 3 個「智慧邪惡干擾項」的選擇題
 *   4. explain(word, form)       ➔ 變形規則解析 ＋ Pitch Accent 原調值 / 活用後調值移位提醒
 *
 * 動詞 8 大變化：masu / te / ta / nai / vol / pot / ba / sugi
 * 形容詞(い・な)／名詞：pos / neg / past / pastneg / te / adv / sugi
 *   （名詞只出前 5 種 + て形；「副詞化(に)」與「すぎ」對名詞語意不通，已略過）
 * ========================================================================== */
(function (global) {
  'use strict';

  // ---------------------------------------------------------------- 基礎工具
  var ROWS = { // 字尾 ➔ [い段, あ段, お段, え段]
    'う': ['い', 'わ', 'お', 'え'], 'く': ['き', 'か', 'こ', 'け'], 'ぐ': ['ぎ', 'が', 'ご', 'げ'],
    'す': ['し', 'さ', 'そ', 'せ'], 'つ': ['ち', 'た', 'と', 'て'], 'ぬ': ['に', 'な', 'の', 'ね'],
    'ぶ': ['び', 'ば', 'ぼ', 'べ'], 'む': ['み', 'ま', 'も', 'め'], 'る': ['り', 'ら', 'ろ', 'れ']
  };
  var I_ROW = 'いきしちにひみりぎじぢびぴ', E_ROW = 'えけせてねへめれげぜでべぺ';
  // 字尾像第二類、其實是第一類（五段）的例外組
  var GODAN_RU = ['帰る', '入る', '走る', '切る', '知る', '要る', '減る', '限る', '参る', '照る', '練る', '蹴る', '散る', '握る',
    '焦る', '滑る', '喋る', '茂る', '湿る', '黙る', '捻る', '遮る', '翻る', '嘲る', '罵る', '覆る', '耽る', '漲る', '炒る', '混じる', '交じる',
    'かえる', 'はいる', 'はしる', 'きる', 'しる', 'いる', 'へる', 'かぎる', 'まいる'];
  var IRREGULAR_MASU_I = ['いらっしゃる', 'おっしゃる', '下さる', 'くださる', 'なさる', 'ござる']; // る ➔ い
  var NA_END_I = ['綺麗', 'きれい', '嫌い', 'きらい', '有名', 'ゆうめい', '幸い', 'さいわい']; // 字尾是い的な形容詞（綺麗、嫌い、有名…）
  var SUPPLEMENT = [ // 單字庫沒有收錄的不規則動詞，補入以便練習 来る / する 的假名讀音陷阱
    { id: 'GR_KURU', kanji: '来る', kana: 'くる', meaning: '來', accent: 1, notes: '第三類動詞', categories: ['動詞'], synthetic: true, level: 'N5' },
    { id: 'GR_SURU', kanji: 'する', kana: 'する', meaning: '做', accent: 0, notes: '第三類動詞', categories: ['動詞'], synthetic: true, level: 'N5' }
  ];

  var VERB_FORMS = ['masu', 'te', 'ta', 'nai', 'vol', 'pot', 'ba', 'sugi'];
  var ADJ_FORMS = ['pos', 'neg', 'past', 'pastneg', 'te', 'adv', 'sugi'];
  var NOUN_FORMS = ['pos', 'neg', 'past', 'pastneg', 'te'];
  var LABELS = {
    masu: 'ます形', te: 'て形', ta: 'た形', nai: 'ない形', vol: '意向形', pot: '可能形', ba: '條件形(ば)', sugi: '過載形(＋すぎ)',
    pos: '現在肯定', neg: '現在否定', past: '過去肯定', pastneg: '過去否定', adv: '副詞化修飾動詞'
  };
  function formLabel(type, f) {
    if (f === 'te' && type !== 'v1' && type !== 'v2' && type !== 'v3') return type === 'i' ? 'て形中頓串接(くて)' : 'て形中頓串接(で)';
    if (f === 'neg') return type === 'i' ? '現在否定(くない)' : '現在否定(じゃない)';
    if (f === 'past') return type === 'i' ? '過去肯定(かった)' : '過去肯定(だった)';
    if (f === 'pastneg') return type === 'i' ? '過去否定(くなかった)' : '過去否定(じゃなかった)';
    if (f === 'adv') return type === 'i' ? '副詞化修飾動詞(く)' : '副詞化修飾動詞(に)';
    return LABELS[f];
  }
  function formsOf(type) {
    if (type === 'v1' || type === 'v2' || type === 'v3') return VERB_FORMS;
    if (type === 'i' || type === 'na') return ADJ_FORMS;
    if (type === 'noun') return NOUN_FORMS;
    return [];
  }

  function last(s) { return s.charAt(s.length - 1); }
  function cut(s, n) { return s.slice(0, s.length - (n || 1)); }
  function uniq(arr) { var o = [], seen = {}; arr.forEach(function (x) { if (x && !seen[x]) { seen[x] = 1; o.push(x); } }); return o; }
  function shuffle(a, rnd) {
    a = a.slice(); rnd = rnd || Math.random;
    for (var i = a.length - 1; i > 0; i--) { var j = Math.floor(rnd() * (i + 1)); var t = a[i]; a[i] = a[j]; a[j] = t; }
    return a;
  }
  function moras(kana) { // 拍數：小ゃゅょ與小母音不獨立成拍，っ ん ー 各算一拍
    return kana.replace(/[ゃゅょぁぃぅぇぉャュョァィゥェォ]/g, '').length;
  }
  function moraList(kana) {
    var res = [];
    for (var i = 0; i < kana.length; i++) {
      var c = kana.charAt(i);
      if (/[ゃゅょぁぃぅぇぉャュョァィゥェォ]/.test(c) && res.length) res[res.length - 1] += c; else res.push(c);
    }
    return res;
  }
  function hasKanji(s) { return /[\u4e00-\u9fff]/.test(s); }

  // ---------------------------------------------------------------- 詞性判斷
  var memo = {};
  function classify(word) {
    if (!word) return null;
    var key = word.id || word.kanji;
    if (memo[key] !== undefined) return memo[key];
    var res = null;
    try { res = doClassify(word); } catch (e) { res = null; }
    memo[key] = res;
    return res;
  }
  function doClassify(word) {
    var k = (word.kanji || '').trim(), r = (word.kana || '').trim().replace(/\s+/g, '');
    var notes = word.notes || '', cats = word.categories || [];
    if (!k || !r) return null;
    if (/[～〜~/／・（）()「」。、\s]/.test(k)) return null; // 片語、含符號的不處理
    var type = null;
    if (k === 'する' || k === '来る' || k === 'くる' || k === '來る') type = 'v3';
    else if (/第一類動詞/.test(notes)) type = 'v1';
    else if (/第二類動詞/.test(notes)) type = 'v2';
    else if (/な形容詞/.test(notes)) type = 'na';
    else if (/い形容詞/.test(notes)) type = 'i';
    else if (/第三類|する/.test(notes) && !/(動詞是|動詞搭配)/.test(notes)) type = 'v3';
    else if (cats.indexOf('動詞') >= 0) type = inferVerb(k, r);
    else if (cats.indexOf('形容詞') >= 0) type = inferAdj(k, r);
    else if (/名詞/.test(notes) || cats.indexOf('名詞') >= 0) type = 'noun';
    if (!type) return null;
    if (type === 'v1' || type === 'v2') {
      if (!ROWS[last(r)] || last(k) !== last(r)) return null; // 讀音與字尾不吻合就略過
      if (type === 'v2' && last(r) !== 'る') return null;
    }
    if (type === 'i') {
      if (last(r) !== 'い') return null;
      if (last(k) !== 'い') return null;
    }
    if (type === 'v3') {
      var kuru = (k === '来る' || k === 'くる' || k === '來る');
      if (!kuru && k !== 'する' && (last(k) === 'る' || last(k) === 'う' || last(k) === 'く')) {
        // 長得像一般動詞的「第三類」標註（如 来る 以外）→ 不處理
        if (!/^[\u4e00-\u9fffァ-ヴー]+$/.test(k)) return null;
      }
      if (kuru) return { type: 'v3', sub: 'kuru', written: '来る', reading: 'くる', kuruKanji: hasKanji(k) };
      if (k === 'する') return { type: 'v3', sub: 'suru', written: '', reading: '' };
      if (/(.)る$/.test(k) && k.length > 1 && last(k) === 'る') return null;
      return { type: 'v3', sub: 'sunoun', written: k, reading: r };
    }
    var out = { type: type, written: k, reading: r };
    if (type === 'i' && (k === '良い' || k === 'いい' || k === 'よい' || r === 'よい' || r === 'いい')) out.sub = 'ii';
    if (type === 'v1' && (k === 'ある' || k === '有る')) out.sub = 'aru';
    if (type === 'v1' && k === '行く') out.sub = 'iku';
    if (type === 'v1' && IRREGULAR_MASU_I.indexOf(k) >= 0) out.sub = 'masuI';
    if (type === 'na' && last(r) === 'い') out.sub = 'naEndI';
    if (type === 'noun' && last(r) === 'い' && NA_END_I.indexOf(k) >= 0) out.sub = 'naEndI';
    return out;
  }
  function inferVerb(k, r) {
    var c = last(r);
    if (c !== 'る') return ROWS[c] ? 'v1' : null;
    if (GODAN_RU.indexOf(k) >= 0 || GODAN_RU.indexOf(r) >= 0) return 'v1';
    var prev = r.charAt(r.length - 2);
    if (prev && (I_ROW.indexOf(prev) >= 0 || E_ROW.indexOf(prev) >= 0)) return 'v2';
    return 'v1';
  }
  function inferAdj(k, r) {
    if (NA_END_I.indexOf(k) >= 0) return 'na';
    if (last(k) === 'い' && last(r) === 'い' && !/^[\u4e00-\u9fff]{1,3}$/.test(k)) return 'i';
    if (last(k) === 'い' && last(r) === 'い' && /い$/.test(k) && k.length >= 2) return 'i';
    return 'na';
  }

  // ---------------------------------------------------------------- 活用核心
  // 回傳 { written, reading }；来る 另附 kuruRead (き/こ/く) 與 suffix
  function conjugate(word, form) {
    var c = classify(word);
    if (!c) return null;
    var t = c.type, w = c.written, r = c.reading;
    if (t === 'v2') {
      var sw = cut(w), sr = cut(r);
      var m2 = { masu: 'ます', te: 'て', ta: 'た', nai: 'ない', vol: 'よう', pot: 'られる', ba: 'れば', sugi: 'すぎ' };
      return pack(sw + m2[form], sr + m2[form]);
    }
    if (t === 'v1') return conjV1(c, form);
    if (t === 'v3') {
      if (c.sub === 'kuru') {
        var rd = { masu: 'き', te: 'き', ta: 'き', nai: 'こ', vol: 'こ', pot: 'こ', ba: 'く', sugi: 'き' }[form];
        var sf = { masu: 'ます', te: 'て', ta: 'た', nai: 'ない', vol: 'よう', pot: 'られる', ba: 'れば', sugi: 'すぎ' }[form];
        return { written: (c.kuruKanji ? '来' : rd) + sf, reading: rd + sf, kuruRead: rd, kuruSuffix: sf, kuruKanji: c.kuruKanji };
      }
      var sru = { masu: 'します', te: 'して', ta: 'した', nai: 'しない', vol: 'しよう', pot: 'できる', ba: 'すれば', sugi: 'しすぎ' }[form];
      return pack(w + sru, r + sru);
    }
    if (t === 'i') {
      var stem = cut(w), rstem = cut(r);
      if (c.sub === 'ii') { stem = (hasKanji(w) ? '良' : 'よ'); rstem = 'よ'; }
      var ending = { pos: 'い', neg: 'くない', past: 'かった', pastneg: 'くなかった', te: 'くて', adv: 'く', sugi: 'すぎ' }[form];
      if (form === 'pos') return pack(w, r);
      return pack(stem + ending, rstem + ending);
    }
    // na / noun
    var e2 = { pos: 'だ', neg: 'じゃない', past: 'だった', pastneg: 'じゃなかった', te: 'で', adv: 'に', sugi: 'すぎ' }[form];
    return pack(w + e2, r + e2);
  }
  function pack(w, r) { return { written: w, reading: r }; }
  function conjV1(c, form) {
    var w = c.written, r = c.reading, e = last(r), row = ROWS[e], sw = cut(w), sr = cut(r);
    var res;
    switch (form) {
      case 'masu': res = c.sub === 'masuI' ? pack(sw + 'い' + 'ます', sr + 'い' + 'ます') : pack(sw + row[0] + 'ます', sr + row[0] + 'ます'); break;
      case 'te': case 'ta': {
        var ta = form === 'ta', suf;
        if (c.sub === 'iku') suf = ta ? 'った' : 'って';
        else if ('うつる'.indexOf(e) >= 0) suf = ta ? 'った' : 'って';
        else if ('ぬぶむ'.indexOf(e) >= 0) suf = ta ? 'んだ' : 'んで';
        else if (e === 'く') suf = ta ? 'いた' : 'いて';
        else if (e === 'ぐ') suf = ta ? 'いだ' : 'いで';
        else suf = ta ? 'した' : 'して';
        res = pack(sw + suf, sr + suf); break;
      }
      case 'nai':
        if (c.sub === 'aru') res = pack(sw + 'ない', sr + 'ない');
        else res = pack(sw + row[1] + 'ない', sr + row[1] + 'ない');
        break;
      case 'vol': res = pack(sw + row[2] + 'う', sr + row[2] + 'う'); break;
      case 'pot': res = pack(sw + row[3] + 'る', sr + row[3] + 'る'); break;
      case 'ba': res = pack(sw + row[3] + 'ば', sr + row[3] + 'ば'); break;
      case 'sugi': res = pack(sw + row[0] + 'すぎ', sr + row[0] + 'すぎ'); break;
    }
    return res;
  }

  // ---------------------------------------------------------------- 干擾項生成
  // 以下全部回傳「與正解同一書寫格式」的錯誤字串陣列（尚未去重、尚未截成 3 個）
  function distractors(word, form, correctDisp) {
    var c = classify(word), t = c.type, w = c.written, r = c.reading, out = [];
    var base = word.kanji; // 顯示用基底
    function add() { for (var i = 0; i < arguments.length; i++) out.push(arguments[i]); }

    if (t === 'v1') {
      var e = last(r), row = ROWS[e], sw = cut(w), isRu = e === 'る';
      var ids = { masu: 'ます', te: 'て', ta: 'た' };
      if (form === 'te' || form === 'ta') {
        var ta = form === 'ta';
        var sokuon = ta ? 'った' : 'って', hatsu = ta ? 'んだ' : 'んで', ii = ta ? 'いた' : 'いて', iiD = ta ? 'いだ' : 'いで', shi = ta ? 'した' : 'して';
        if (c.sub === 'iku') add(sw + ii, sw + hatsu, sw + row[0] + (ta ? 'た' : 'て')); // 行く 必出：行いて / 行いた
        if (isRu) add(sw + (ta ? 'た' : 'て'), sw + hatsu, sw + row[0] + (ta ? 'た' : 'て')); // 帰て / 帰んで / 帰りて
        if (e === 'う') add(sw + ii, sw + hatsu, sw + row[0] + (ta ? 'た' : 'て'));
        if (e === 'つ') add(sw + row[0] + (ta ? 'た' : 'て'), sw + hatsu, sw + ii);
        if ('ぬぶむ'.indexOf(e) >= 0) add(sw + sokuon, sw + ii, sw + row[0] + (ta ? 'た' : 'て'));
        if (e === 'く') add(sw + sokuon, sw + hatsu, sw + row[0] + (ta ? 'た' : 'て'));
        if (e === 'ぐ') add(sw + ii, sw + sokuon, sw + hatsu);
        if (e === 'す') add(sw + ii, sw + sokuon, sw + hatsu);
        add(sw + sokuon, sw + hatsu, sw + ii, sw + iiD, sw + shi);
      } else if (form === 'masu') {
        add(sw + 'ます', base + 'ます', sw + row[1] + 'ます', sw + row[3] + 'ます', sw + 'て');
      } else if (form === 'nai') {
        if (e === 'う') add(sw + 'あない'); // 買う ➔ 買あない（必出）
        add(sw + row[0] + 'ない', sw + 'ない', base + 'ない', sw + row[3] + 'ない', sw + 'うない');
      } else if (form === 'vol') {
        add(sw + (row[2] === 'お' ? 'あう' : 'おう'), sw + row[3] + 'よう', sw + 'よう', base + 'よう', sw + row[0] + 'よう');
        add(sw + row[2] + 'お', sw + row[1] + 'よう');
        if (e === 'る') add(sw + 'ろう'.replace('ろう', 'るよう'));
      } else if (form === 'pot') {
        add(sw + row[1] + 'れる', sw + 'られる', sw + row[0] + 'れる', sw + row[3], sw + row[0] + 'られる', sw + 'できる');
      } else if (form === 'ba') {
        add(base + 'ば', sw + row[0] + 'ば', sw + row[1] + 'ば', sw + row[3] + 'れば', sw + 'れば');
      } else if (form === 'sugi') {
        add(base + 'すぎ', sw + row[1] + 'すぎ', sw + 'て' + 'すぎ', sw + row[0] + 'ますぎ', sw + row[3] + 'すぎ');
      }
    } else if (t === 'v2') {
      var s = cut(w);
      if (form === 'masu') add(base + 'ます', s + 'ります', s + 'いります', s + 'ませ', s + 'てます');
      if (form === 'te') add(s + 'って', s + 'んで', s + 'いて', s + 'りて', s + 'るて', base + 'て');
      if (form === 'ta') add(s + 'った', s + 'んだ', s + 'いた', s + 'りた', s + 'るた', base + 'た');
      if (form === 'nai') add(s + 'らない', s + 'くない', s + 'ずない', base + 'ない', s + 'なく');
      if (form === 'vol') add(s + 'おう', s + 'ろう', s + 'るよう', s + 'よ', s + 'えよう');
      if (form === 'pot') add(s + 'れる', s + 'させる', s + 'える', s + 'れられる', s + 'られた', s + 'らせる'); // 五段化 / 使役
      if (form === 'ba') add(s + 'るば', s + 'ば', s + 'れ', s + 'ればれ', s + 'らば');
      if (form === 'sugi') add(base + 'すぎ', s + 'ますぎ', s + 'てすぎ', s + 'らすぎ', s + 'いすぎ');
    } else if (t === 'v3') {
      if (c.sub === 'kuru') {
        var cur = conjugate(word, form);
        ['き', 'こ', 'く', 'け'].forEach(function (rd) {
          if (rd !== cur.kuruRead) add(kuruDisp(cur, rd));
        });
      } else {
        var pre = w;
        var bad = {
          masu: ['すます', 'しります', 'さます', 'せます'], te: ['すて', 'しって', 'せて', 'しんで'], ta: ['すた', 'しった', 'せた', 'しんだ'],
          nai: ['すない', 'せない', 'しらない', 'さない'], vol: ['すよう', 'しろう', 'せよう', 'しおう'], pot: ['すれる', 'しられる', 'できられる', 'せられる'],
          ba: ['しれば', 'するば', 'しえば', 'せば'], sugi: ['すすぎ', 'しますぎ', 'するすぎ', 'しすぎる']
        }[form] || [];
        bad.forEach(function (b) { add(pre + b); });
      }
    } else if (t === 'i') {
      var st = c.sub === 'ii' ? (hasKanji(w) ? '良' : 'よ') : cut(w), full = w;
      if (c.sub === 'ii') { // いい 特例：いくない／いかった
        var ib = { neg: ['いくない', 'よいない', 'いいくない', 'よくいない'], past: ['いかった', 'いいかった', 'よいかった', 'よくった'],
          pastneg: ['いくなかった', 'よいなかった', 'いいくなかった', 'よくないかった'], te: ['いくて', 'よいて', 'いいくて', 'よくで'],
          adv: ['いく', 'よいく', 'いいく', 'よに'], pos: ['よくない', 'よかった', 'いくない', 'よく'], sugi: ['いすぎ', 'いいすぎ', 'よいすぎ', 'よくすぎ'] }[form] || [];
        ib.forEach(function (b) { add(b); });
      } else {
        var tbl = {
          pos: [st + 'くない', st + 'かった', st + 'く', st + 'な'],
          neg: [st + 'いない', st + 'ない', st + 'くなかった', st + 'かない', st + 'くなくない'],
          past: [st + 'いかった', st + 'くかった', st + 'かたった', st + 'だった', st + 'くなかった'],
          pastneg: [st + 'いなかった', st + 'くないかった', st + 'なかった', st + 'くない', st + 'かくなかった'],
          te: [st + 'いて', st + 'で', st + 'くで', st + 'くって', st + 'いくて'],
          adv: [st + 'に', st + 'くに', st + 'いに', st + 'で', st + 'くて'],
          sugi: [st + 'いすぎ', st + 'くすぎ', st + 'さすぎ', st + 'なすぎ', full + 'すぎ']
        };
        add.apply(null, tbl[form] || []);
      }
    } else { // na / noun
      var X = w, stI = X;
      if (c.sub === 'naEndI') { // 綺麗、嫌い、有名：自動產生按い形容詞規則變化的錯誤選項
        stI = last(X) === 'い' ? cut(X) : X;
        var wrongI = {
          neg: [X + 'くない', stI + 'くない', stI + 'くない'], past: [X + 'かった', stI + 'かった'], pastneg: [X + 'くなかった', stI + 'くなかった'],
          te: [X + 'くて', stI + 'くて'], adv: [X + 'く', stI + 'く'], sugi: [X + 'いすぎ', stI + 'すぎ'], pos: [X + 'い', stI + 'い']
        }[form] || [];
        wrongI.forEach(function (b) { add(b); });
      }
      var gen = {
        pos: [X + 'い', X + 'な', X + 'く', X + 'です'],
        neg: [X + 'くない', X + 'なない', X + 'いじゃない', X + 'だじゃない', X + 'ない'],
        past: [X + 'かった', X + 'なった', X + 'くだった', X + 'だたった', X + 'だった'],
        pastneg: [X + 'くなかった', X + 'なかった', X + 'じゃないかった', X + 'ではなかっ', X + 'だなかった'],
        te: [X + 'くて', X + 'て', X + 'なで', X + 'だで', X + 'にで'],
        adv: [X + 'く', X + 'で', X + 'な', X + 'だに', X + 'くに'],
        sugi: [X + 'なすぎ', X + 'だすぎ', X + 'いすぎ', X + 'くすぎ', X + 'にすぎ']
      };
      add.apply(null, gen[form] || []);
    }
    return out.filter(function (x) { return x !== correctDisp; });
  }
  function kuruDisp(cur, rd) {
    return cur.kuruKanji ? '来（' + rd + '）' + cur.kuruSuffix : rd + cur.kuruSuffix;
  }
  function displayOf(word, form) {
    var cj = conjugate(word, form);
    if (!cj) return null;
    if (cj.kuruRead !== undefined) return kuruDisp(cj, cj.kuruRead);
    return cj.written;
  }
  function readingOf(word, form) {
    var cj = conjugate(word, form);
    return cj ? cj.reading : null;
  }

  // ---------------------------------------------------------------- 出題
  function makeQuestion(word, form, rnd) {
    var c = classify(word);
    if (!c || formsOf(c.type).indexOf(form) < 0) return null;
    var correct = displayOf(word, form);
    var traps = uniq(distractors(word, form, correct)).filter(function (x) { return x !== correct; });
    var filler = ['ない', 'て', 'た', 'ます'];
    var fi = 0;
    while (traps.length < 3 && fi < filler.length) { var f = word.kanji + filler[fi++] + 'る'; if (f !== correct && traps.indexOf(f) < 0) traps.push(f); }
    traps = traps.slice(0, 3);
    var ex = explain(word, form);
    var label = formLabel(c.type, form);
    var promptHint = (c.type === 'v2' && form === 'pot') ? '（標準書面形）' : '';
    return {
      kind: 'conj',
      id: 'CONJ_' + word.id + '_' + form,
      wordId: word.id,
      word: word,
      formKey: form,
      formLabel: label,
      wordType: c.type,
      prompt: '「' + word.kanji + '」（' + word.kana + '）的「' + label + '」' + promptHint + '是？',
      answer: correct,
      reading: readingOf(word, form),
      traps: traps,
      options: shuffle([correct].concat(traps), rnd),
      rule: ex.rule,
      pitch: ex.pitch,
      explanation: ex.rule + '\n' + ex.pitch
    };
  }
  function parseQuestionId(id) { // CONJ_N5_008_te ➔ { wordId:'N5_008', form:'te' }
    var m = /^CONJ_(.+)_([a-z]+)$/.exec(id || '');
    return m ? { wordId: m[1], form: m[2] } : null;
  }

  // ---------------------------------------------------------------- 說明與 Pitch
  var TYPE_NAME = { v1: '第一類動詞（五段）', v2: '第二類動詞（一段）', v3: '第三類動詞（不規則）', i: 'い形容詞', na: 'な形容詞', noun: '名詞' };
  function explain(word, form) {
    var c = classify(word);
    if (!c) return { rule: '', pitch: '' };
    var t = c.type, e = last(c.reading), rule = '', cj = conjugate(word, form);
    var head = '【' + TYPE_NAME[t] + (c.sub === 'naEndI' ? '・字尾是い的な形容詞' : '') + '】';
    if (t === 'v1') {
      if (form === 'te' || form === 'ta') {
        var ta = form === 'ta' ? '（た形＝把 て/で 換成 た/だ）' : '';
        if (c.sub === 'iku') rule = '⚠️ 特例：行く 是促音便例外，行く ➔ ' + cj.written + '（不可用 く ➔ いて）' + ta;
        else if ('うつる'.indexOf(e) >= 0) rule = '字尾「' + e + '」➔ 促音便「っ」：' + word.kanji + ' ➔ ' + cj.written + ta + (e === 'る' ? '（長得像第二類但其實是五段，不能直接去る）' : '');
        else if ('ぬぶむ'.indexOf(e) >= 0) rule = '字尾「' + e + '」➔ 鼻音便「ん」：' + word.kanji + ' ➔ ' + cj.written + ta;
        else if (e === 'く') rule = '字尾「く」➔ い音便：' + word.kanji + ' ➔ ' + cj.written + ta;
        else if (e === 'ぐ') rule = '字尾「ぐ」➔ い音便且濁音化「いで」：' + word.kanji + ' ➔ ' + cj.written + ta;
        else rule = '字尾「す」➔ 沒有音便，直接換「し」：' + word.kanji + ' ➔ ' + cj.written + ta;
      } else if (form === 'masu') rule = '字尾「う段」倒退一格變「い段」＋ます：' + word.kanji + ' ➔ ' + cj.written + (c.sub === 'masuI' ? '（⚠️ 敬語特例：る 變成 い）' : '');
      else if (form === 'nai') rule = (e === 'う' ? '⚠️ 字尾是單獨「う」要變「わ」：' : c.sub === 'aru' ? '⚠️ ある 的否定是「ない」（不是あらない）：' : '字尾「う段」前進一格變「あ段」＋ない：') + word.kanji + ' ➔ ' + cj.written;
      else if (form === 'vol') rule = '字尾「う段」跳兩格變「お段」＋う：' + word.kanji + ' ➔ ' + cj.written;
      else if (form === 'pot') rule = '字尾「う段」前進一格變「え段」＋る：' + word.kanji + ' ➔ ' + cj.written + '（對象助詞を ➔ が）';
      else if (form === 'ba') rule = '字尾「う段」前進一格變「え段」＋ば：' + word.kanji + ' ➔ ' + cj.written;
      else rule = '先變ます形語幹（い段），拔掉ます直接接すぎ：' + word.kanji + ' ➔ ' + cj.written;
    } else if (t === 'v2') {
      rule = { masu: '去掉「る」＋ます', te: '去掉「る」＋て', ta: '去掉「る」＋た', nai: '去掉「る」＋ない', vol: '去掉「る」＋よう', pot: '去掉「る」＋られる（口語常省略成「れる」＝ら抜き，但標準形是られる）；⚠️ 不要當五段處理', ba: '去掉「る」＋れば', sugi: '去掉「る」＋すぎ（先變ます形語幹）' }[form] + '：' + word.kanji + ' ➔ ' + cj.written;
    } else if (t === 'v3') {
      if (c.sub === 'kuru') {
        rule = '来る 的漢字不變、假名會變：來（き）ます／來（き）て／來（こ）ない／來（こ）よう／來（こ）られる／來（く）れば。此處：' + displayOf(word, form) + '（' + cj.reading + '）';
      } else rule = (c.sub === 'sunoun' ? '名詞＋する 變成第三類動詞，活用全部落在「する」上：' : 'する 的不規則變化：') + word.kanji + ' ➔ ' + cj.written;
    } else if (t === 'i') {
      if (c.sub === 'ii') rule = '👑 いい 是變形大魔王：只有現在肯定與修飾名詞維持いい，一進入變形系統必須退回「よい」：' + cj.written + '（❌ いくない／いかった）';
      else rule = { pos: '原形＋です／原形', neg: '拔 い ➔ 換 くない', past: '拔 い ➔ 換 かった', pastneg: '拔 い ➔ 換 くなかった', te: '拔 い ➔ 換 くて', adv: '拔 い ➔ 換 く', sugi: '拔掉字尾「い」直接接すぎ' }[form] + '：' + word.kanji + ' ➔ ' + cj.written;
    } else {
      rule = { pos: '加上 だ／です', neg: '加上 じゃない（口語）或 ではない（文章）', past: '加上 だった／でした', pastneg: '加上 じゃなかった 或 ではなかった', te: '直接加 で', adv: '加上 に', sugi: '拔掉「な／だ」直接接すぎ' }[form] + '：' + word.kanji + ' ➔ ' + cj.written;
      if (c.sub === 'naEndI') rule += '\n⚠️ ' + word.kanji + ' 字尾發音雖是「い」，但它是な形容詞，不能按い形容詞變成「' + (last(word.kanji) === 'い' ? cut(word.kanji) : word.kanji) + 'くない／かった」！';
      if (t === 'noun') rule = rule.replace('な形容詞', '名詞');
    }
    return { rule: head + rule, pitch: pitchNote(word, c, form, cj) };
  }

  function pitchNote(word, c, form, cj) {
    var acc = word.accent;
    if (acc === undefined || acc === null || acc === '') return '🎵 此單字沒有 Pitch Accent 資料。';
    var accN = Number(acc);
    var orig = word.kana + ' [' + accN + ']';
    var r = cj.reading, n = moras(r), est = null, note = '';
    var verb = (c.type === 'v1' || c.type === 'v2' || c.type === 'v3');
    if (verb) {
      if (form === 'masu') { est = n - 1; note = 'ます 形重音固定落在「ま」上（ま↓す）'; }
      else if (form === 'te' || form === 'ta') {
        if (accN === 0) { est = 0; note = '平板型動詞活用後仍為平板型'; }
        else {
          est = Math.min(accN, n - 1);
          var ml = moraList(r);
          if (ml[est - 1] === 'っ' || ml[est - 1] === 'ん') est = est - 1; // 促音 / 撥音不能承載重音，前移一拍
          note = '有重音的動詞，降調位置大致維持在原拍數（若落在 っ/ん 上則前移一拍）';
        }
      } else if (form === 'nai') { var base = n - 2; est = accN === 0 ? 0 : base; note = accN === 0 ? '平板型活用後仍為平板型' : '有重音的動詞，ない 前一拍降調'; }
      else if (form === 'vol' || form === 'ba') { est = n - 1; note = form === 'vol' ? '意向形重音落在「う」前一拍' : 'ば 形重音落在「ば」前一拍'; }
      else if (form === 'pot') { est = accN === 0 ? 0 : n - 1; note = accN === 0 ? '平板型動詞的可能形仍為平板型' : '可能形是一段動詞型，重音在倒數第二拍'; }
      else { return '🎵 原調值：' + orig + '\n🔁 活用提醒：すぎ 與動詞合成複合詞後，調值會依整體重新計算（原動詞的降調位置不再適用），請以音檔聽辨。'; }
    } else if (c.type === 'i') {
      if (form === 'pos') { est = accN; note = '原形'; }
      else if (form === 'sugi') return '🎵 原調值：' + orig + '\n🔁 活用提醒：すぎ 合成後調值重新計算，請以音檔聽辨。';
      else { est = accN; note = accN === 0 ? '平板型活用後仍為平板型' : '降調位置大致維持在原拍數'; }
    } else {
      if (form === 'sugi') return '🎵 原調值：' + orig + '\n🔁 活用提醒：すぎ 合成後調值重新計算，請以音檔聽辨。';
      est = accN; note = accN === 0 ? '平板型後接助動詞仍為平板型' : '降調位置維持在名詞原本位置';
    }
    return '🎵 原調值：' + orig + '\n🔁 活用後調值移位提醒：' + cj.reading + ' ≈ [' + est + ']（' + note + '；依東京腔一般規則推估，請以音檔為準）';
  }

  // ---------------------------------------------------------------- 對外 API
  function withSupplement(list, levels) {
    var has = {};
    list.forEach(function (w) { if (w.kanji === '来る' || w.kanji === 'する') has[w.kanji] = true; });
    var extra = SUPPLEMENT.filter(function (s) { return !has[s.kanji] && (!levels || levels.indexOf(s.level) >= 0); });
    return list.concat(extra);
  }
  function eligibleForms(word) {
    var c = classify(word);
    return c ? formsOf(c.type) : [];
  }
  // 所有可用的 formKey（供 UI 篩選器列舉）
  var ALL_FORM_KEYS = [
    { key: 'masu', label: 'ます形' }, { key: 'te', label: 'て形' }, { key: 'ta', label: 'た形' }, { key: 'nai', label: 'ない形' },
    { key: 'vol', label: '意向形' }, { key: 'pot', label: '可能形' }, { key: 'ba', label: '條件形(ば)' }, { key: 'sugi', label: '過載形(すぎ)' },
    { key: 'pos', label: '形容詞現在肯定' }, { key: 'neg', label: '現在否定' }, { key: 'past', label: '過去肯定' }, { key: 'pastneg', label: '過去否定' }, { key: 'adv', label: '副詞化' }
  ];

  global.ConjugationEngine = {
    classify: classify, conjugate: conjugate, makeQuestion: makeQuestion, explain: explain,
    eligibleForms: eligibleForms, formLabel: formLabel, parseQuestionId: parseQuestionId,
    withSupplement: withSupplement, displayOf: displayOf,
    VERB_FORMS: VERB_FORMS, ADJ_FORMS: ADJ_FORMS, NOUN_FORMS: NOUN_FORMS, ALL_FORM_KEYS: ALL_FORM_KEYS, SUPPLEMENT: SUPPLEMENT,
    ADJ4: ['pos', 'neg', 'past', 'pastneg'],
    _shuffle: shuffle
  };
})(window);
