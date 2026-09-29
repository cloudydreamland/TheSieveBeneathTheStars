"""CLI 集成：退出码语义。"""

from __future__ import annotations

import json

import pytest

from siftan.cli import main


@pytest.fixture()
def files(tmp_path):
    bench = tmp_path / "bench.jsonl"
    train_clean = tmp_path / "train_clean.jsonl"
    train_dirty = tmp_path / "train_dirty.jsonl"
    rows = [
        {
            "id": f"q{i}",
            "question": f"第{i}题：下列关于中国宪法基本权利的表述哪一项正确？选项甲乙丙丁。",
        }
        for i in range(1, 101)
    ]
    bench.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
    clean = [
        {"id": f"c{i}", "text": f"日常对话{i}：今天聊聊怎么把一碗面做得好吃。"} for i in range(200)
    ]
    train_clean.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in clean), encoding="utf-8"
    )
    dirty = [dict(r) for r in clean]
    for i in range(10):  # 10/200 = 5% ≥ 阈值 → CONTAMINATED
        dirty[i]["text"] = rows[i]["question"]
    train_dirty.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in dirty), encoding="utf-8"
    )
    return bench, train_clean, train_dirty, tmp_path


def _run(argv):
    with pytest.raises(SystemExit) as exc:
        main(argv)
    return exc.value.code


def test_build_screen_clean_then_dirty(files):
    bench, clean, dirty, tmp = files
    idx = str(tmp / "bench.tsi")
    assert _run(["build-index", str(bench), "-o", idx, "--name", "synth"]) == 0
    assert _run(["verify-index", idx]) == 0
    # --text-field text 且 --id-field id；干净集 CLEAN → 0
    assert _run(["screen", idx, str(clean), "--text-field", "text"]) == 0
    # 脏集 CONTAMINATED → 2
    assert _run(["screen", idx, str(dirty), "--text-field", "text"]) == 2


def test_screen_reports_flagged_records(files, capsys):
    bench, _, dirty, tmp = files
    idx = str(tmp / "bench.tsi")
    _run(["build-index", str(bench), "-o", idx, "--name", "synth"])
    with pytest.raises(SystemExit):
        main(["screen", idx, str(dirty), "--text-field", "text", "--show-flagged"])
    out = capsys.readouterr().out
    payload = json.loads(out[out.index("{"):])  # 跳过 build-index 的输出行
    assert payload["label"] == "CONTAMINATED"
    assert payload["flagged_records"][0]["id"] == "c0"


def test_corrupt_index_exit_3(tmp_path):
    bad = tmp_path / "bad.tsi"
    bad.write_bytes(b"not gzip")
    assert _run(["verify-index", str(bad)]) == 3
