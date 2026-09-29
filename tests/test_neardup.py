"""iter2 近重复层：包含率语义、索引 v2 往返、改写级泄入检出验收。"""

from __future__ import annotations

import json

from siftan.check import screen
from siftan.index import ContaminationIndex, build_index
from siftan.ngrams import hamming_distance, simhash64

BENCH = [
    f"第{i}题：下列关于中国宪法基本权利的表述哪一项是正确的？选项甲乙丙丁各有其依据与边界。"
    for i in range(1, 101)
]
CLEAN_TRAIN = [
    f"日常对话样本{i}：今天我们聊聊厨房里的事情，比如怎么把一碗面做得好吃，汤要如何熬才香。"
    for i in range(1, 201)
]

# 泄入模型（真实世界最常见形态）：逐字复制后插入注释打断长片段——
# 题库网站加注/水印/解析的典型样子。每 11 字符插一段注释：
# 13 字符连续段全部被打断（精确层抓不到），11 字符段内的 8-gram 大量存活
# （经验 ratio ≈ 0.33，在 0.30 阈值上方留出余量）。
# 诚实边界：对抗级结构性改写（最长保留段 <8 字符）超出近重复层能力——
# simhash 实验已证伪短文本指纹，见 WORKLOG iter2。
FILLERS = ["〔注〕", "〔解析〕", "〔出处待考〕"]


def paraphrase(text: str, i: int) -> str:
    filler = FILLERS[i % len(FILLERS)]
    chunks = [text[j : j + 11] for j in range(0, len(text), 11)]
    return filler.join(chunks)


def test_simhash_utility_still_works_for_long_docs():
    """simhash 保留为长文档工具：确定性 + 小改动小距离（不用于短文本近重复层）。"""
    t = "这是一段足够长的文档内容" * 20
    assert simhash64(t) == simhash64(t)
    tweaked = t.replace("足够长", "非常长")
    assert 0 < hamming_distance(simhash64(t), simhash64(tweaked)) < 20


def test_index_v2_roundtrip(tmp_path):
    idx = build_index(BENCH, name="v2")
    assert idx.near_dup_available
    assert idx.meta.near_count > 0
    path = idx.save(tmp_path / "v2.tsi")
    loaded = ContaminationIndex.load(path)
    assert loaded.near_dup_available
    assert loaded.near_grams == idx.near_grams
    assert loaded.grams == idx.grams
    # 篡改近重复段 → 校验失败
    import gzip as _gzip

    with _gzip.open(path, "rt", encoding="utf-8") as f:
        lines = f.read().splitlines()
    lines[-1] = lines[-1][::-1]  # 反转最后一个 8-gram
    with _gzip.open(path, "wt", encoding="utf-8") as f:
        f.write("\n".join(lines))
    try:
        ContaminationIndex.load(path)
        raised = False
    except ValueError:
        raised = True
    assert raised, "篡改近重复段必须被哈希校验拦截"


def test_v1_index_still_loads_near_dup_unavailable(tmp_path):
    """v1 旧索引（无近重复段）可加载，近重复层如实报告不可用。"""
    import gzip as _gzip

    from siftan.index import body_sha256
    from siftan.ngrams import ngrams as _ngrams

    grams = set()
    for t in BENCH[:50]:
        grams |= _ngrams(t, 13)
    path = tmp_path / "v1.tsi"
    with _gzip.open(path, "wt", encoding="utf-8") as f:
        f.write(json.dumps({
            "schema_version": 1, "name": "old", "n": 13, "count": len(grams),
            "sha256": body_sha256(grams, set()),
            "sources": [],
        }, ensure_ascii=False) + "\n")
        for g in sorted(grams):
            f.write(g + "\n")
    loaded = ContaminationIndex.load(path)
    assert loaded.near_dup_available is False
    cert = screen("d", [("a", "一段足够长的训练文本内容示例")], loaded)
    assert cert.near_dup_available is False
    assert cert.near_dup_hits == 0


def test_paraphrased_leakage_caught_by_near_dup_layer():
    """验收标准（iter2）：10 条结构性改写泄入 → 精确层 0 命中，近重复层 ≥8/10。"""
    idx = build_index(BENCH, name="synth")
    records = list(CLEAN_TRAIN)
    for i in range(10):
        records[i] = paraphrase(BENCH[i], i)
    cert = screen("paraphrased", list(enumerate(records)), idx)
    exact_flagged = sum(1 for v in cert.records if v.flagged)
    assert exact_flagged == 0, "改写级泄入不应由 13-gram 精确层命中（否则说明改写不成立）"
    assert cert.near_dup_hits >= 8, f"近重复层应 ≥8/10，实际 {cert.near_dup_hits}/10"


def test_clean_set_no_near_dup_false_positives():
    idx = build_index(BENCH, name="synth")
    cert = screen("clean", list(enumerate(CLEAN_TRAIN)), idx)
    assert cert.near_dup_hits == 0
    assert cert.label == "CLEAN"


def test_ratio_is_deterministic_and_in_range():
    idx = build_index(BENCH[:20], name="r")
    p = paraphrase(BENCH[0], 0)
    r1 = idx.near_dup_ratio(p)
    r2 = idx.near_dup_ratio(p)
    assert r1 == r2 and 0.0 < r1 <= 1.0
