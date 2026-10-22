window.GRAMMAR_DB = {
  // 1. 實戰情境庫 (S01 ~ S08，來自 Source_Curriculum_and_Pragmatics.md)
  scenarios: [
    {
      id: "S01",
      stage: "Stage 1: 抵達與生存探索",
      title: "【S01】便利商店與速食店點餐",
      minLevel: "N5",
      vaultRefs: ["U01", "U05"],
      formulas: ["～をください / ～をお願いします", "～と～ (並列點餐)", "これ / それ / あれ / どれ"],
      mentalModels: ["萬用轉接頭 (て形中頓點餐)", "穿套裝 vs 穿睡衣 (温めてください vs チンして)", "看板は (袋は大丈夫です)"],
      matrix: {
        tier1: { ja: "温めてください。袋は大丈夫です。", kana: "あたためて ください。ふくろは だいじょうぶです。", zh: "請幫我加熱。不需要袋子。", audio: "./audio/grammar/S01_t1.mp3" },
        tier2: { ja: "温めて。袋いらない。", kana: "あたためて。ふくろ いらない。", zh: "幫我微波。不用袋子。", audio: "./audio/grammar/S01_t2.mp3" },
        tier3: { ja: "チンして！袋いらん。", kana: "ちんして！ふくろ いらん。", zh: "微波一下！不用袋子啦。", audio: "./audio/grammar/S01_t3.mp3" }
      },
      receptiveKeigo: [
        { ja: "袋はお分けしますか？ / ご利用になりますか？", zh: "需要袋子嗎？/需要分裝嗎？", reply: "袋は大丈夫です。", audio: "./audio/grammar/S01_k1.mp3" },
        { ja: "温めますか？", zh: "需要加熱嗎？", reply: "はい、お願いします。", audio: "./audio/grammar/S01_k2.mp3" },
        { ja: "ポイントカードはお持ちですか？", zh: "有集點卡嗎？", reply: "いいえ、持っていません。", audio: "./audio/grammar/S01_k3.mp3" }
      ],
      roleplayCmd: "/roleplay R01"
    }
    // ... S02 ~ S08
  ],

  // 2. 12大文法心態寶典庫 (U01 ~ U12，來自 all_12_grammar_sources_merged.md)
  vaultUnits: [
    {
      id: "U01",
      title: "單元 01：日文「て形 (Te-form)」核心用法大全（萬用轉接頭）",
      coreMindset: "て形不是時態，而是「轉接頭 / 橋樑」：我的話還沒說完，後面還有東西要接喔！",
      sections: [
        { subtitle: "🔌 1. 動作的串接與順序 (中頓)", formula: "[動作 A] て、[動作 B]", examples: [{ ja: "朝起きて、ご飯を食べます。", zh: "早上起床，然後吃飯。", vocabIds: ["N5_005", "N5_012", "N5_058", "N5_020"] }] }
        // ... 完整收錄五大類與附錄音便防呆圖鑑
      ]
    }
    // ... U02 ~ U12
  ],

  // 3. 例句挖空選擇題庫 (綁定 vocabLevel: N5~N1，隨側邊欄 selectedLevels 動態過濾！)
  clozeQuestions: [
    {
      id: "CLOZE_001",
      vocabLevel: "N5", // 👈 只有勾選 N5 時會出這題（核心單字 100% 來自 N5）
      unitId: "U01",
      scenarioId: "S01",
      category: "動詞て形與音便",
      tier: "Tier 1 丁寧體",
      sentence: "博多駅に（  ）、ラーメンを食べました。",
      translation: "去了博多車站，然後吃了拉麵。",
      answer: "行って",
      traps: ["行いて", "行んで", "行きて"],
      targetWordId: "N5_008", // 連結 N5_008 行く
      pitchHint: "行く [0] ➔ 行って [0]",
      explanation: "⚠️ 特例警報：「行く」雖然字尾是「く」，但它是第一類動詞中唯一的促音便特例（行く ➔ 行って），不可用一般「く ➔ いて」規則變成「行いて」！",
      audio: "./audio/grammar/CLOZE_001.mp3"
    },
    {
      id: "CLOZE_002",
      vocabLevel: "N4", // 👈 勾選 N4 以上才會解鎖這題（使用 N4_033 続ける / N4_211 会場 等）
      unitId: "U02",
      scenarioId: "S02",
      category: "から vs ので 接續陷阱",
      tier: "Tier 1 丁寧體",
      sentence: "電車が（  ）ので、遅刻してしまいました。",
      translation: "由於電車延誤的客觀事實，導致我不小心遲到了。",
      answer: "遅れた",
      traps: ["遅れるだ", "遅れな", "遅れて"],
      targetWordId: "N4_422", // 連結 N4_422 遅れる
      pitchHint: "遅れる [0] ➔ 遅れた [0]",
      explanation: "📄 遲到理由說明需用客觀報告書「ので」；動詞過去常體「遅れた」可直接接「ので」，不需要加「だ」或「な」（只有名詞與な形容詞接ので才要加な）！",
      audio: "./audio/grammar/CLOZE_002.mp3"
    }
  ]
};