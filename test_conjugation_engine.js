// test_conjugation_engine.js
// Automated test suite for conjugation_engine.js
// Run via: /System/Library/Frameworks/JavaScriptCore.framework/Versions/Current/Helpers/jsc test_conjugation_engine.js

var window = this;
load('grammar_DB.js');
load('conjugation_engine.js');

if (!window.GRAMMAR_DB) throw new Error('GRAMMAR_DB not found');
if (!window.ConjugationEngine) throw new Error('ConjugationEngine not found');

var testWords = [
  // v1 Godan verbs
  { id: 'W1', kanji: '書く', kana: 'かく', notes: '第一類動詞', accent: 1 },
  { id: 'W2', kanji: '泳ぐ', kana: 'およぐ', notes: '第一類動詞', accent: 2 },
  { id: 'W3', kanji: '話す', kana: 'はなす', notes: '第一類動詞', accent: 2 },
  { id: 'W4', kanji: '待つ', kana: 'まつ', notes: '第一類動詞', accent: 1 },
  { id: 'W5', kanji: '死ぬ', kana: 'しぬ', notes: '第一類動詞', accent: 0 },
  { id: 'W6', kanji: '呼ぶ', kana: 'よぶ', notes: '第一類動詞', accent: 0 },
  { id: 'W7', kanji: '飲む', kana: 'のむ', notes: '第一類動詞', accent: 1 },
  { id: 'W8', kanji: '買う', kana: 'かう', notes: '第一類動詞', accent: 0 },
  { id: 'W9', kanji: '帰る', kana: 'かえる', notes: '第一類動詞', accent: 1 },
  { id: 'W10', kanji: '走る', kana: 'はしる', notes: '第一類動詞', accent: 2 },
  // v2 Ichidan verbs
  { id: 'W11', kanji: '食べる', kana: 'たべる', notes: '第二類動詞', accent: 2 },
  { id: 'W12', kanji: '見る', kana: 'みる', notes: '第二類動詞', accent: 1 },
  { id: 'W13', kanji: '起きる', kana: 'おきる', notes: '第二類動詞', accent: 2 },
  // v3 Irregular verbs
  { id: 'W14', kanji: '来る', kana: 'くる', notes: '第三類動詞', accent: 1 },
  { id: 'W15', kanji: 'する', kana: 'する', notes: '第三類動詞', accent: 0 }
];

var forms = ['masu', 'te', 'ta', 'nai', 'vol', 'pot', 'ba', 'sugi', 'pass', 'caus', 'imp', 'proh'];

var passedCount = 0;
var totalCount = testWords.length * forms.length;

testWords.forEach(function(w) {
  var c = window.ConjugationEngine.classify(w);
  if (!c || !c.type) throw new Error('Classification failed for ' + w.kanji);

  forms.forEach(function(f) {
    var res = window.ConjugationEngine.conjugate(w, f);
    if (!res || !res.written || !res.reading) {
      throw new Error('Conjugation failed for ' + w.kanji + ' (' + f + ')');
    }

    var q = window.ConjugationEngine.makeQuestion(w, f);
    if (!q || !q.answer || !q.reading) {
      throw new Error('Question creation failed for ' + w.kanji + ' (' + f + ')');
    }
    if (q.traps.length !== 3) {
      throw new Error('Traps length !== 3 for ' + w.kanji + ' (' + f + ')');
    }
    if (q.traps.indexOf(q.answer) !== -1) {
      throw new Error('Answer found in traps for ' + w.kanji + ' (' + f + ')');
    }
    var uniqueTraps = {};
    q.traps.forEach(function(t) { uniqueTraps[t] = true; });
    if (Object.keys(uniqueTraps).length !== 3) {
      throw new Error('Duplicate traps for ' + w.kanji + ' (' + f + ')');
    }

    passedCount++;
  });
});

print('✅ All ' + passedCount + ' / ' + totalCount + ' conjugation engine automated tests passed successfully!');
