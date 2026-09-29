"""筛查与污染证明书。

两层信号（iter2 起）：
1. **精确层**（主判决）：基准 13-gram 命中。记录命中 ≥ MIN_HITS 即 flagged；
   数据集 flagged 比例 ≥ DATASET_FLAG_RATIO → CONTAMINATED。
2. **近重复层**（advisory，不改主判决）：记录 8-gram 被基准包含的比率
   ≥ NEAR_DUP_RATIO → near_dup 命中。抓改写级泄入（句式重构/同义替换），
   报告为附加证据——把它计入主判决会放大阈值误伤，评审决策：先 advisory，
   待真实语料上量化误伤率后再考虑升级（ROADMAP）。

证明书带索引哈希与全部参数——第三方可用同索引复算。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from siftan.index import ContaminationIndex

MIN_HITS = 1
DATASET_FLAG_RATIO = 0.05
# 8-gram 包含率阈值（iter2 合成改写集上的经验校准，公开可挑战）：
# 注入式改写泄入实测 ratio ∈ [0.264, 0.333]，干净语料实测 = 0.0——
# 两者之间是空带，取 0.25 居中。真实语料上的分布迁移待官方基线索引建成后复测。
NEAR_DUP_RATIO = 0.25

THRESHOLDS_DOC = {
    "MIN_HITS": MIN_HITS,
    "DATASET_FLAG_RATIO": DATASET_FLAG_RATIO,
    "NEAR_DUP_RATIO": NEAR_DUP_RATIO,
}


@dataclass
class RecordVerdict:
    record_id: str
    hits: int
    near_dup_ratio: float | None = None  # None = 近重复层不可用/记录无指纹
    samples: list[str] = field(default_factory=list)

    @property
    def flagged(self) -> bool:
        return self.hits >= MIN_HITS

    @property
    def near_dup_hit(self) -> bool:
        return self.near_dup_ratio is not None and self.near_dup_ratio >= NEAR_DUP_RATIO


@dataclass
class ContaminationCertificate:
    dataset: str
    index_name: str
    index_sha256: str
    n: int
    total: int
    flagged_count: int
    flag_ratio: float
    label: str  # CLEAN / SUSPECT / CONTAMINATED（只由精确层决定）
    near_dup_hits: int = 0
    near_dup_available: bool = False
    records: list[RecordVerdict] = field(default_factory=list)
    thresholds: dict = field(default_factory=lambda: dict(THRESHOLDS_DOC))
    honesty: str = (
        "精确层（13-gram）只证明字面泄漏；近重复层（8-gram 包含率，advisory）抓改写级"
        "泄入但可能误伤模板化文本——命中样例需人工复核。证明书结论以所用索引为限，"
        "释义级与训练侧污染需其他方法。"
    )

    def to_dict(self) -> dict:
        return {
            "dataset": self.dataset,
            "index": {"name": self.index_name, "sha256": self.index_sha256, "n": self.n},
            "total": self.total,
            "flagged": self.flagged_count,
            "flag_ratio": round(self.flag_ratio, 4),
            "label": self.label,
            "near_dup": {
                "available": self.near_dup_available,
                "hits": self.near_dup_hits,
                "ratio_threshold": NEAR_DUP_RATIO,
                "semantics": "advisory（不改主判决）",
            },
            "thresholds": self.thresholds,
            "honesty": self.honesty,
        }


def screen(
    dataset_name: str,
    records: list[tuple[str, str]],
    index: ContaminationIndex,
) -> ContaminationCertificate:
    """records: [(record_id, text), ...]"""
    verdicts: list[RecordVerdict] = []
    for rid, text in records:
        hits, samples = index.overlap(text)
        ratio = index.near_dup_ratio(text)
        verdicts.append(
            RecordVerdict(record_id=rid, hits=hits, near_dup_ratio=ratio, samples=samples)
        )
    flagged = [v for v in verdicts if v.flagged]
    ratio = (len(flagged) / len(verdicts)) if verdicts else 0.0
    if ratio == 0.0:
        label = "CLEAN"
    elif ratio >= DATASET_FLAG_RATIO:
        label = "CONTAMINATED"
    else:
        label = "SUSPECT"
    return ContaminationCertificate(
        dataset=dataset_name,
        index_name=index.meta.name,
        index_sha256=index.meta.sha256,
        n=index.meta.n,
        total=len(verdicts),
        flagged_count=len(flagged),
        flag_ratio=ratio,
        label=label,
        near_dup_hits=sum(1 for v in verdicts if v.near_dup_hit),
        near_dup_available=index.near_dup_available,
        records=verdicts,
    )
