// 用法：jsc dump_conj_texts.js  → 每行「級別<TAB>活用題發音文字」（與 index.html 的 speakText 清理規則一致）
var window = {};
['N5', 'N4', 'N3', 'N2', 'N1'].forEach(function (l) { load('vocab_' + l + '.js'); });
load('conjugation_engine.js');
var E = window.ConjugationEngine, seen = {};
['N5', 'N4', 'N3', 'N2', 'N1'].forEach(function (l) {
  (window.VOCAB_DB[l] || []).forEach(function (w) {
    if (!E.classify(w)) return;
    E.eligibleForms(w).forEach(function (f) {
      var q = E.makeQuestion(w, f);
      var t = (q.reading || q.answer || '').replace(/【.*?】/g, '').replace(/[〇～]/g, '').trim();
      if (t && !seen[t]) { seen[t] = 1; print(l + '\t' + t); }
    });
  });
});
E.SUPPLEMENT.forEach(function (w) {
  E.eligibleForms(w).forEach(function (f) {
    var t = (E.makeQuestion(w, f).reading || '').trim();
    if (t && !seen[t]) { seen[t] = 1; print('N5\t' + t); }
  });
});
