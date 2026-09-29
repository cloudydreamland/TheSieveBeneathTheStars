"""索引与筛查端到端：合成基准上的 F1 锁定。"""

from __future__ import annotations

import pytest

from siftan.check import screen
from siftan.index import ContaminationIndex, build_index

BENCH = [
    f"第{i}题：下列关于中国宪法基本权利的表述哪一项是正确的？选项甲乙丙丁各有其依据与边界。"
    for i in range(1, 101)
]
CLEAN_TRAIN = [
    f"日常对话样本{i}：今天我们聊聊厨房里的事情，比如怎么把一碗面做得好吃，汤要如何熬才香。"
    for i in range(1, 201)
]


def _contaminated(records: list[str], bench: list[str], k: int) -> list[str]:
    """把前 k 条基准逐字（换格式）插入训练集前部。"""
    out = list(records)
    for i, b in enumerate(bench[:k]):
        out[i] = b.replace("第", "第 ", 1) + "（来自网络题库）"
    return out


@pytest.fixture(scope="module")
def index() -> ContaminationIndex:
    return build_index(BENCH, name="synth-bench", n=13)


def test_clean_dataset_is_clean(index):
    cert = screen("clean", list(enumerate(CLEAN_TRAIN)), index)
    assert cert.label == "CLEAN"
    assert cert.flagged_count == 0


def test_inserted_contamination_fully_detected(index):
    records = _contaminated(CLEAN_TRAIN, BENCH, 10)
    cert = screen("dirty", list(enumerate(records)), index)
    assert cert.label == "CONTAMINATED"
    assert cert.flagged_count == 10
    flagged_ids = {v.record_id for v in cert.records if v.flagged}
    assert flagged_ids == set(range(10))  # enumerate 给出的 int id
    # 证明书带索引指纹，可第三方复算
    assert len(cert.index_sha256) == 64


def test_single_hit_is_suspect(index):
    records = _contaminated(CLEAN_TRAIN, BENCH, 1)
    cert = screen("suspect", list(enumerate(records)), index)
    assert cert.label == "SUSPECT"


def test_index_roundtrip_with_tamper_check(tmp_path):
    idx = build_index(BENCH[:50], name="t", n=13)
    assert len(idx.meta.sha256) == 64  # 构建即带指纹（证明书即刻可引用）
    path = idx.save(tmp_path / "t.tsi")
    loaded = ContaminationIndex.load(path)
    assert len(loaded) == len(idx)
    # 篡改头部 count（构造合法 gzip 流）→ 内容与头部不一致 → 校验失败
    import gzip as _gzip
    import json as _json

    with _gzip.open(path, "rt", encoding="utf-8") as f:
        lines = f.read().splitlines()
    header = _json.loads(lines[0])
    header["count"] += 1
    tampered = "\n".join([_json.dumps(header, ensure_ascii=False), *lines[1:]])
    with _gzip.open(path, "wt", encoding="utf-8") as f:
        f.write(tampered)
    with pytest.raises(ValueError):
        ContaminationIndex.load(path)


def test_certificate_honesty_note():
    cert = screen("x", [], build_index([""], name="empty"))
    assert "字面泄漏" in cert.honesty
    assert cert.label == "CLEAN"  # 空数据集不算污染（但 total=0 值得警惕）
