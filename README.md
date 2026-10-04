# The Sieve Beneath the Stars — Siftan

简体中文 · [English](README.en.md)

> 展示名 **The Sieve Beneath the Stars** 描绘一张在星空下筛取微尘的网；Siftan 是该项目的短名。

**面向语言模型评测语料的重合筛查工具。用你选择的索引发现可复核的匹配，并记录筛查参数与索引标识。**

[![PyPI](https://img.shields.io/pypi/v/siftan)](https://pypi.org/project/siftan/)
[![Python](https://img.shields.io/pypi/pyversions/siftan)](https://pypi.org/project/siftan/)
[![CI](https://github.com/cloudydreamland/TheSieveBeneathTheStars/actions/workflows/ci.yml/badge.svg)](https://github.com/cloudydreamland/TheSieveBeneathTheStars/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
## 为什么需要它 / Why

模型评测依赖测试集的可信度。如果训练数据与测试题重合，分数可能无法准确反映模型对新问题的泛化能力。Siftan 允许你针对指定的基准索引扫描语料中的 n-gram 重合，并导出带索引哈希和参数的结果供复查。

（完整取证：[GAP_PROOF.md](GAP_PROOF.md)）

## 安装 / Install

```bash
python -m pip install siftan
```

从源码安装（开发或最新版）：

```bash
git clone https://github.com/cloudydreamland/TheSieveBeneathTheStars.git
cd TheSieveBeneathTheStars
python -m pip install .
```

## 快速开始 / Quickstart

```bash
# 1. 把基准变成可携带的 n-gram 指纹索引（13-gram，与预训练去重惯例对齐）

siftan build-index ceval_dev.jsonl -o ceval_dev.tsi --name C-Eval-dev

# 2. 筛查你的微调集/训练集，生成可复核的筛查结果

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
  第三方可用 `siftan verify-index` 复算，筛查记录包含可校验的索引标识；
  v1 旧索引可加载，近重复层如实报告不可用
- **筛查结果**：数据集级 CLEAN/SUSPECT/CONTAMINATED（阈值公开），附索引哈希与全部参数

## 与现有方案的关系 / Landscape

| 方法类别 | 适用范围 |
|---|---|
| 评测框架 | 帮助运行 benchmark、计算分数；与训练语料重合检查是不同步骤 |
| 自建 n-gram 脚本 | 可针对特定数据集做精确匹配；需自行管理索引、规范化和复现信息 |
| Siftan | 针对用户提供的索引做可复现重合筛查；未命中不能证明语料完全无污染 |

## 路线图 / Roadmap

见 [ROADMAP.md](ROADMAP.md)。当前 0.1.0a1：n-gram 核心 + 索引校验 + 筛查结果 + CLI。
接下来：近重复层（simhash/minhash）、常见基准的索引构建脚本、
删除式去污染（redact 泄入片段）、lm-eval-harness 中间件。

## 开发 / Development

```bash
pip install -e ".[dev]"
./.venv/Scripts/python.exe -m pytest -q
./.venv/Scripts/python.exe -m ruff check src tests
```

## 反馈与参与

使用问题和功能建议可以在 [Discussions](https://github.com/cloudydreamland/TheSieveBeneathTheStars/discussions) 交流；可复现缺陷请提交 [Issue](https://github.com/cloudydreamland/TheSieveBeneathTheStars/issues)。请只附合成或脱敏后的最小样例，不要上传真实个人信息、API key 或业务原文。安全问题请按 [SECURITY.md](SECURITY.md) 私下报告。

## License

MIT
