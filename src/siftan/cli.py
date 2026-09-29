"""命令行入口。

    siftan build-index bench.jsonl -o idx.tsi --name C-Eval-dev
    siftan screen idx.tsi train.jsonl --id-field id --text-field text
    siftan verify-index idx.tsi

输入为 JSONL；screen 支持 --id-field/--text-field（默认 id/text，缺 id 用行号）。
退出码：0 CLEAN / 1 SUSPECT / 2 CONTAMINATED / 3 错误。
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

from siftan._version import __version__
from siftan.check import screen
from siftan.index import ContaminationIndex, build_index
from siftan.ngrams import DEFAULT_N


def _read_jsonl(path: str) -> list[dict]:
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:  # 空行跳过——空 dict 会在 build-index 侧变成 "{}" 垃圾 n-gram
                out.append(json.loads(line))
    return out


def _extract_text(row: dict, text_field: str) -> str:
    """text_field="all" 时拼接全部字符串值（与 build-index 的口径一致）。"""
    if text_field == "all":
        return " ".join(str(v) for v in row.values() if isinstance(v, str))
    return str(row.get(text_field, ""))


def cmd_build_index(args: argparse.Namespace) -> int:
    rows = _read_jsonl(args.input)
    texts = [
        " ".join(str(v) for v in row.values() if isinstance(v, str)) or str(row)
        for row in rows
    ]
    idx = build_index(
        texts,
        name=args.name,
        n=args.n,
        sources=[args.input],
        created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        builder=f"siftan {__version__}",
    )
    path = idx.save(args.out)
    print(f"索引 {idx.meta.name}: {len(idx)} 个 {idx.meta.n}-gram → {path}")
    print(f"sha256: {idx.meta.sha256[:16]}…")
    return 0


def cmd_screen(args: argparse.Namespace) -> int:
    index = ContaminationIndex.load(args.index)
    rows = _read_jsonl(args.dataset)
    records = []
    for i, row in enumerate(rows):
        text = _extract_text(row, args.text_field)
        rid = str(row.get(args.id_field, i)) if args.id_field in row else str(i)
        records.append((rid, text))
    cert = screen(args.dataset, records, index)
    payload = cert.to_dict()
    if args.show_flagged:
        payload["flagged_records"] = [
            {"id": v.record_id, "hits": v.hits, "samples": v.samples}
            for v in cert.records
            if v.flagged
        ][: args.max_show]
    if args.no_near_dup:
        payload.pop("near_dup", None)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return {"CLEAN": 0, "SUSPECT": 1, "CONTAMINATED": 2}[cert.label]


def cmd_verify_index(args: argparse.Namespace) -> int:
    index = ContaminationIndex.load(args.index)  # 校验失败会抛 ValueError
    print(
        f"OK {index.meta.name}: {len(index)} grams, n={index.meta.n}, "
        f"sha256={index.meta.sha256[:16]}…"
    )
    return 0


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="siftan", description="Siftan — 基准污染检测")
    sub = parser.add_subparsers(dest="command", required=True)

    p_build = sub.add_parser("build-index", help="从基准 JSONL 构建 n-gram 指纹索引")
    p_build.add_argument("input")
    p_build.add_argument("-o", "--out", required=True)
    p_build.add_argument("--name", required=True)
    p_build.add_argument("--n", type=int, default=DEFAULT_N)
    p_build.set_defaults(func=cmd_build_index)

    p_screen = sub.add_parser("screen", help="筛查数据集，出具污染证明书")
    p_screen.add_argument("index")
    p_screen.add_argument("dataset")
    p_screen.add_argument("--id-field", default="id")
    p_screen.add_argument(
        "--text-field",
        default="text",
        help="文本字段名；'all' 表示拼接全部字符串值（与 build-index 口径一致）",
    )
    p_screen.add_argument("--show-flagged", action="store_true")
    p_screen.add_argument("--max-show", type=int, default=20)
    p_screen.add_argument(
        "--no-near-dup", action="store_true", help="不输出近重复层结果（判决仍含）"
    )
    p_screen.set_defaults(func=cmd_screen)

    p_verify = sub.add_parser("verify-index", help="校验索引文件完整性")
    p_verify.add_argument("index")
    p_verify.set_defaults(func=cmd_verify_index)

    args = parser.parse_args(argv)
    try:
        code = args.func(args)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        code = 3
    raise SystemExit(code)


if __name__ == "__main__":
    main()
