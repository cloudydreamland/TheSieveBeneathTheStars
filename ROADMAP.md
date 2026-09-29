# ROADMAP — 夜间自动化迭代驱动表（siftan）

> 规则与 shijin 相同：每轮取第一个未勾选条目，代码+测试+文档完整做完再勾选；
> 每轮固定动作：实现 → 三视角对抗评审（资深开发者/项目经理/老板，可上网核查竞品）
> → 批评转化新条目 → pytest + ruff 全绿 → git 提交 → 更新 WORKLOG。
> 命令：`./.venv/Scripts/python.exe -m pytest -q`；`./.venv/Scripts/python.exe -m ruff check src tests`。

## 迭代条目

- [x] **iter0（2026-09-28 凌晨，主会话完成）**：字符级 13-gram（NFKC 归一化/小写/空白压缩）、
  索引（gzip JSONL + 内容 sha256 头 + 构建即哈希 + 加载校验）、证明书
  （CLEAN/SUSPECT/CONTAMINATED，公开阈值，诚实边界写入证书）、CLI
  （build-index/screen/verify-index，退出码 0-3）。14 项测试全绿 + ruff 清零。
- [x] **iter1（2026-09-28 06:14–06:50，夜间第 5 轮）— 对抗评审 #1 + 修复**：抓到并修复
  空行污染索引真 bug（空 dict → "{}" 垃圾 n-gram 入索引）+ screen/build-index
  口径一致性缺口（`--text-field all`）。
- [x] **iter2（同轮）— 近重复层**：首选 simhash+LSH 方案被验收实验**证伪**（40 字中文
  考题结构性改写后汉明距离 64=完全不相关），切换为 8-gram 包含率方案；阈值 0.25 由
  合成改写集实测校准（contaminated ∈ [0.264,0.333] / clean = 0.0，空带取中）。
  索引 schema v2（双段哈希、篡改可检出、v1 兼容加载）；证明书增 near_dup 字段
  （advisory 语义）。验收：10 条注入式改写 → 精确层 0/10、近重复层 10/10、干净集 0 误报。
  20 测试全绿。诚实边界：对抗级结构性改写不可检（README/证书已注明）。
- [ ] **iter3 — 删除式去污染**：`siftan scrub`：定位泄入片段（最长公共子串）并 redact，
  输出"去污后数据集 + 操作日志"；roundtrip 测试（scrub 后 screen = CLEAN）。
- [ ] **iter3b —（iter2 评审追加）近重复层误伤率量化**：构造含模板化文本
  （"请回答下列问题"类共享套话）的数据集，量化 0.25 阈值的误伤率；
  若误伤显著，引入停用片段表或提高阈值——near_dup 从 advisory 升级主判决的前提。
- [ ] **iter4 — 基准索引构建脚手架**：`tools/build_common_indexes.py`：常见开源基准
  （C-Eval / CMMLU / GSM8K / MMLU 子集）从 HF datasets 拉取并建索引的脚本
  （网络与数据集库为可选依赖，文档写明许可注意）；在 README 给出预计算索引的分发方案（HF）。
- [ ] **iter5 — 文档与科研联动**：README_EN；`docs/integration.md`
  （lm-eval-harness / inspect-ai 中间件用法草案）；论文引用清单页。
- [x] **iter7/wrap-up（2026-09-28 07:14–07:20，夜间最后一轮）— 终版复盘**：
  20 测试全绿、ruff 清零；REPORT.md 终版；终版评审记录见 WORKLOG。最终提交完成。

## 收尾条目

- [x] **wrap-up（已完成）**：REPORT.md 终版 + 终版提交完成（07:20）。

## 用户醒来后的人工事项

- 注册 GitHub 仓库并 push；HF 索引分发需用户账号
- 提供主流基准的下载环境（HF 网络）后跑 iter4 的真实索引构建
