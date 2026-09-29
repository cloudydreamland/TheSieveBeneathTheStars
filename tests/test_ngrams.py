"""n-gram 与归一化：中文优先的行为锁定。"""

from __future__ import annotations

from siftan.ngrams import ngrams, normalize


def test_normalize_nfkc_and_case():
    assert normalize("Ｈｅｌｌｏ　Ｗｏｒｌｄ") == "hello world"
    assert normalize("ＡＢＣ１２３") == "abc123"


def test_normalize_collapses_whitespace():
    assert normalize("a \t\n b　　c") == "a b c"


def test_ngrams_chinese_char_level():
    text = "大语言模型在中文场景下的分词行为与英文存在显著差异"
    grams = ngrams(text, 13)
    assert len(grams) == len(normalize(text)) - 13 + 1
    assert any("大语言模型在中文场景" in g for g in grams)


def test_short_text_is_empty_not_error():
    assert ngrams("太短", 13) == set()


def test_contamination_is_detectable_across_reformatting():
    """泄漏后改了大小写/全角/空白，仍应命中同一 n-gram。"""
    original = "下列哪项不是宪法规定的基本权利：A 选举权 B 受教育权"
    rewritten = "下列哪项不是宪法规定的基本权利：ａ 选举权　ｂ 受教 育权"
    assert ngrams(original, 13) & ngrams(rewritten, 13)


def test_disjoint_texts_share_nothing():
    a = "甲乙丙丁戊己庚辛壬癸子丑寅卯辰巳午未申酉戌亥"
    b = "_alpha_beta_gamma_delta_epsilon_zeta_eta_theta_iota_kappa"
    assert not (ngrams(a, 13) & ngrams(b, 13))
