"""归一化与 n-gram 提取 + simhash 近重复指纹。

中文无空格分词，因此用**字符级 n-gram**（默认 n=13，与 GPT-3/LLaMA 系预训练
去重惯用的 13-gram 对齐）；英文经归一化后同样适用（按字符滑窗）。
归一化顺序：NFKC → 小写 → 压空白为单空格 → 去空白变体（全角空格等）。

simhash 层（iter2）：字符 3-gram 特征 → 64 位指纹，汉明距离 ≤ 阈值视为近重复。
用于抓"改写级泄入"（同义词替换/插入填充/标点改动）——13-gram 精确层抓不到的。
"""

from __future__ import annotations

import hashlib
import unicodedata

DEFAULT_N = 13
SIMHASH_FEATURE_N = 3
SIMHASH_BITS = 64


def normalize(text: str) -> str:
    """评测语料可比对的规范形。"""
    text = unicodedata.normalize("NFKC", text)
    text = text.lower()
    # 全部空白（含全角空格、零宽字符）压成单个空格
    text = "".join(
        ch if not ch.isspace() and unicodedata.category(ch) != "Cf" else " " for ch in text
    )
    return " ".join(text.split())


def ngrams(text: str, n: int = DEFAULT_N) -> set[str]:
    """归一化文本的字符级 n-gram 集合。短于 n 的文本返回空集（诚实：证据不足）。"""
    norm = normalize(text)
    if len(norm) < n:
        return set()
    return {norm[i : i + n] for i in range(len(norm) - n + 1)}


def simhash64(text: str, n: int = SIMHASH_FEATURE_N) -> int:
    """字符 n-gram 加权 simhash（md5 折叠为 64 位）。确定性，纯标准库。

    短文本（特征不足）返回 0——调用方以 0 为"无指纹"哨兵，不参与近重复比较。
    """
    norm = normalize(text)
    if len(norm) < n + 4:  # 特征太少，指纹无意义
        return 0
    bits = [0] * SIMHASH_BITS
    for i in range(len(norm) - n + 1):
        gram = norm[i : i + n]
        h = int.from_bytes(hashlib.md5(gram.encode("utf-8")).digest()[:8], "big")
        for b in range(SIMHASH_BITS):
            bits[b] += 1 if (h >> b) & 1 else -1
    return sum(1 << b for b in range(SIMHASH_BITS) if bits[b] > 0)


def hamming_distance(a: int, b: int) -> int:
    return bin(a ^ b).count("1")
