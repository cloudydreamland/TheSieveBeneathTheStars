# CHANGELOG — siftan

## 0.1.0a1 (2026-09-28)

- 首个 alpha：字符级 13-gram（中文优先归一化）、可校验 gzip 索引
  （内容 sha256 头）、污染证明书（CLEAN/SUSPECT/CONTAMINATED +
  诚实边界声明）、CLI（build-index/screen/verify-index）。
- 14 项测试全绿；合成基准上逐字泄入检出率 100%、干净集 0 误报。
