"""污染指纹索引：基准语料 → 双层 n-gram 集合 → 可校验的文件。

存储格式（schema v2，gzip 行式）：
- 首行：头部 JSON（元数据 + 内容哈希）
- 13-gram 行（精确层，排序去重）
- 分隔行 ===near-ngram-section===
- 8-gram 行（近重复层原料，排序去重）

近重复层语义：数据集记录的 8-gram 与索引 8-gram 的包含率 ≥ 阈值即命中——
抓"改写级泄入"（句式重构/同义替换后仍保留大量短片段）。选型说明：simhash 方案
在 iter2 实验中被合成短文本证伪（40 字考题改写后汉明距离 64=完全不相关），
短中文语料上包含率显著更鲁棒（见 tests/test_neardup.py 与 WORKLOG iter2）。

v1 文件（无近重复段）可正常加载，近重复层如实报告不可用——不伪装。

诚实边界：内存换速度——全集加载进 Python set。更大规模路线：分片/Bloom（评审后决策）。
"""

from __future__ import annotations

import gzip
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from siftan.ngrams import DEFAULT_N, ngrams

SCHEMA_VERSION = 2
NEAR_MARKER = "===near-ngram-section==="
NEAR_N = 8  # 近重复层片段长度：短到能跨改写存活，长到避免模板误伤（阈值公开可挑战）


def body_sha256(grams: set[str], near_grams: set[str]) -> str:
    gram_part = "\n".join(sorted(grams))
    if not near_grams:
        # v1 口径（无近重复段的旧索引）：仅对 13-gram 部分取哈希
        return hashlib.sha256(gram_part.encode("utf-8")).hexdigest()
    near_part = "\n".join(sorted(near_grams))
    payload = f"{gram_part}\n{NEAR_MARKER}\n{near_part}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass
class IndexMeta:
    name: str
    n: int
    count: int
    sha256: str
    near_count: int = 0
    sources: list[str] = field(default_factory=list)
    created_at: str = ""
    builder: str = ""


class ContaminationIndex:
    def __init__(
        self,
        meta: IndexMeta,
        grams: set[str] | None = None,
        near_grams: set[str] | None = None,
    ) -> None:
        self.meta = meta
        self.grams: set[str] = grams or set()
        self.near_grams: set[str] = near_grams or set()

    @property
    def n(self) -> int:
        return self.meta.n

    def __len__(self) -> int:
        return len(self.grams)

    @property
    def near_dup_available(self) -> bool:
        return bool(self.near_grams)

    def overlap(self, text: str) -> tuple[int, list[str]]:
        """返回 (13-gram 命中数, 命中样例)。"""
        grams = ngrams(text, self.meta.n)
        hits = grams & self.grams
        return len(hits), sorted(hits)[:5]

    def near_dup_ratio(self, text: str) -> float | None:
        """记录 8-gram 被索引包含的比率；层不可用/记录无指纹返回 None。"""
        if not self.near_grams:
            return None
        own = ngrams(text, NEAR_N)
        if not own:
            return None
        return len(own & self.near_grams) / len(own)

    # ---------- IO ----------

    def save(self, path: str | Path) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        sha = body_sha256(self.grams, self.near_grams)
        payload = {
            "schema_version": SCHEMA_VERSION,
            "name": self.meta.name,
            "n": self.meta.n,
            "sources": self.meta.sources,
            "created_at": self.meta.created_at,
            "builder": self.meta.builder,
            "count": len(self.grams),
            "near_count": len(self.near_grams),
            "sha256": sha,
        }
        self.meta.count = len(self.grams)
        self.meta.near_count = len(self.near_grams)
        self.meta.sha256 = sha
        with gzip.open(p, "wt", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
            for g in sorted(self.grams):
                f.write(g + "\n")
            if self.near_grams:
                f.write(NEAR_MARKER + "\n")
                for g in sorted(self.near_grams):
                    f.write(g + "\n")
        return p

    @classmethod
    def load(cls, path: str | Path) -> ContaminationIndex:
        p = Path(path)
        with gzip.open(p, "rt", encoding="utf-8") as f:
            lines = f.read().splitlines()
        if not lines:
            raise ValueError(f"索引为空: {p.name}")
        header = json.loads(lines[0])
        body = lines[1:]
        if NEAR_MARKER in body:
            split = body.index(NEAR_MARKER)
            gram_lines = body[:split]
            near_lines = body[split + 1 :]
        else:
            gram_lines = body
            near_lines = []
        grams = set(gram_lines)
        near_grams = set(near_lines)
        meta = IndexMeta(
            name=header["name"],
            n=header["n"],
            count=header["count"],
            sha256=header["sha256"],
            near_count=header.get("near_count", 0),
            sources=header.get("sources", []),
            created_at=header.get("created_at", ""),
            builder=header.get("builder", ""),
        )
        idx = cls(meta, grams, near_grams)
        if body_sha256(grams, near_grams) != meta.sha256 or len(grams) != meta.count:
            raise ValueError(f"索引校验失败: {p.name}（内容与头部哈希不一致）")
        return idx


def build_index(
    texts: list[str],
    name: str,
    n: int = DEFAULT_N,
    sources: list[str] | None = None,
    created_at: str = "",
    builder: str = "",
) -> ContaminationIndex:
    """从基准文本列表构建索引（13-gram 精确层 + 8-gram 近重复层）。

    短文本如实跳过对应层（无 13-gram 或无 8-gram 都不进入相应集合）。
    """
    grams: set[str] = set()
    near_grams: set[str] = set()
    for t in texts:
        grams |= ngrams(t, n)
        near_grams |= ngrams(t, NEAR_N)
    meta = IndexMeta(
        name=name,
        n=n,
        count=len(grams),
        sha256=body_sha256(grams, near_grams),
        near_count=len(near_grams),
        sources=sources or [],
        created_at=created_at,
        builder=builder,
    )
    return ContaminationIndex(meta, grams, near_grams)
