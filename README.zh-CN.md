# The Sieve Beneath the Stars — Siftan

[English](README.md) · 简体中文

> 名字取自古英语 **siftan**——「筛、淘」。千淘万漉虽辛苦，吹尽狂沙始到金。

**中文优先的基准污染检测库。"人人都在评测，没人能证明未污染"——Siftan把这句话变成可以出具证明书的工作。**

[![CI](https://github.com/cloudydreamland/TheSieveBeneathTheStars/actions/workflows/ci.yml/badge.svg)](.github/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

## 为什么需要它 / Why

- ICLR 2026 论文实证：主流污染检测器在 RL 训练后 AUROC 暴跌 14-17 点——**现有检测方法整体失效**（arXiv:2510.02386）
- 现有工具全部停更：MMLU-CF 126★（2025-05）、lm-contamination 83★（2024-04）、detect-pretrain-code-contamination 79★（2023-12）
- 对照：lm-eval-harness 14,085★——**人人都在评测，几乎没人能证明未污染**，这个不对称就是缺口
- 中文场景雪上加霜：C-Eval/MMLU 中文翻译版等静态题库被污染、刷榜的公开讨论不断

（完整取证：[GAP_PROOF.md](GAP_PROOF.md)）

## 安装 / Install

```bash
# 克隆仓库后，在项目根目录安装
python -m pip install .
# 发布到 PyPI 后可直接安装
python -m pip install siftan
```

## 快速开始 / Quickstart

```bash
# 1. 把基准变成可携带的 n-gram 指纹索引（13-gram，与预训练去重惯例对齐）

siftan build-index ceval_dev.jsonl -o ceval_dev.tsi --name C-Eval-dev

# 2. 筛查你的微调集/训练集，出具污染证明书

siftan screen ceval_dev.tsi my_sft_data.jsonl --text-field text --show-flagged
# {"label": "CLEAN", "flag_ratio": 0.0, "index": {"sha256": "9f3a…"}, ...}

# 退出码：0 CLEAN / 1 SUSPECT / 2 CONTAMINATED / 3 错误

```

```python
from siftan import build_index, screen

index = build_index(benchmark_texts, name="C-Eval-dev")
cert = screen("my-sft-data", [(rid, text), ...], index)
print(cert.label, cert.flag_ratio, cert.index_sha256)
```

## 工作原理 / How it works

两层信号：

1. **精确层（主判决）**：字符级 13-gram（NFKC 归一化 + 小写 + 空白压缩，
   全角/大小写/空白变体泄漏照样命中）
2. **近重复层（advisory，不改主判决）**：数据集记录的 8-gram 被基准包含的比率
   ≥ 0.25 即命中——抓"复制后插注释/水印"式改写泄入（13-gram 已断、8-gram 仍存活）。
   校准数据：合成注入式改写 ratio ∈ [0.264, 0.333]，干净语料 = 0.0，中间是空带。
   诚实边界：对抗级结构性改写（最长保留段 <8 字符）超出本层能力，命中样例需人工复核

- **索引 = 13-gram 集 + 8-gram 集 + 内容 sha256 头**（gzip 行式，schema v2）——
  第三方可用 `siftan verify-index` 复算，证明书的可信度来自索引本身可校验；
  v1 旧索引可加载，近重复层如实报告不可用
- **证明书**：数据集级 CLEAN/SUSPECT/CONTAMINATED（阈值公开），附索引哈希与全部参数

## 与现有方案的关系 / Landscape

| 方案 | 状态（2026-09-28） |
|---|---|
| detect-pretrain-code-contamination（79★） | 2023-12 停更；需白盒模型访问 |
| lm-contamination index（83★） | 2024-04 停更；手工数据库非工具 |
| MMLU-CF（126★） | 单基准特例，非通用基础设施 |
| LiveBench（1,329★） | 换题基准，回答"用什么测"而非"你的数据脏不脏" |
| Siftan | 可携带索引 + 可校验证明书 + 中文优先 + 零依赖 |

## 路线图 / Roadmap

见 [ROADMAP.md](ROADMAP.md)。当前 0.1.0a1：n-gram 核心 + 索引校验 + 证明书 + CLI。
接下来：近重复层（simhash/minhash）、常见基准的索引构建脚本、
删除式去污染（redact 泄入片段）、lm-eval-harness 中间件。

## 开发 / Development

```bash
pip install -e ".[dev]"
./.venv/Scripts/python.exe -m pytest -q
./.venv/Scripts/python.exe -m ruff check src tests
```

## License

MIT
