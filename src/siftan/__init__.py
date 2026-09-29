"""Siftan — 基准污染检测。

"人人都在评测，没人能证明未污染。"（lm-eval-harness 14k★ vs 污染检测工具全部 <126★ 且停更）

siftan 把基准语料变成可携带的 n-gram 指纹索引，对任意数据集/微调集筛查，
出具带索引哈希的"污染证明书"（contamination certificate）。
"""

from siftan._version import __version__
from siftan.check import ContaminationCertificate, screen
from siftan.index import ContaminationIndex
from siftan.ngrams import hamming_distance, ngrams, normalize, simhash64

__all__ = [
    "ContaminationCertificate",
    "ContaminationIndex",
    "screen",
    "normalize",
    "ngrams",
    "simhash64",
    "hamming_distance",
    "__version__",
]
