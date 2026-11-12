#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""按类别批量重命名并归集图片。

用法：
    python scripts/filter_rename.py \
        --src    data/raw \
        --mapping mapping.csv \
        --dst    datasets/VOCdevkit/JPEGImages

mapping.csv 两列（带表头）：
    原文件名,类别
    1.jpg,wb
    10.jpg,none      <- 类别留空或写 none 表示跳过
    23.jpg,sc

规则：
  - 同一类从 01 开始编号，按原文件名的数字顺序递增
  - 输出命名 Wb01.jpg / Sc01.jpg / Dc01.jpg / Wc01.jpg
"""
import argparse
import csv
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

PREFIX = {"wb": "Wb", "sc": "Sc", "dc": "Dc", "wc": "Wc"}
SKIP = {"", "none", "-", "na", "无"}


def natural_key(name: str):
    """让 2.jpg 排在 10.jpg 前面，而不是按字符串排序。"""
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", name)]


def load_mapping(path: Path):
    rows = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        next(reader, None)  # 跳过表头
        for row in reader:
            if len(row) < 2:
                continue
            name = row[0].strip()
            cls = row[1].strip().lower()
            if not name:
                continue
            rows.append((name, cls))
    return rows


def main():
    ap = argparse.ArgumentParser(description="按类别重命名归集图片")
    ap.add_argument("--src", required=True, help="原始图片目录")
    ap.add_argument("--mapping", required=True, help="分类映射 CSV")
    ap.add_argument("--dst", required=True, help="输出目录（JPEGImages）")
    ap.add_argument("--dry-run", action="store_true", help="只打印，不实际复制")
    args = ap.parse_args()

    src = Path(args.src)
    dst = Path(args.dst)
    if not src.is_dir():
        sys.exit(f"源目录不存在: {src}")

    mapping = load_mapping(Path(args.mapping))
    if not mapping:
        sys.exit("mapping.csv 里没有有效数据")

    # 排序保证编号稳定可复现
    mapping.sort(key=lambda x: natural_key(x[0]))

    dst.mkdir(parents=True, exist_ok=True)
    counter = Counter()
    missing = []

    for name, cls in mapping:
        if cls in SKIP:
            continue
        if cls not in PREFIX:
            print(f"[跳过] {name}: 未知类别 {cls!r}")
            continue

        source = src / name
        if not source.exists():
            missing.append(name)
            continue

        counter[cls] += 1
        target_name = f"{PREFIX[cls]}{counter[cls]:02d}{source.suffix.lower()}"
        target = dst / target_name

        if args.dry_run:
            print(f"{name} -> {target_name}")
        else:
            shutil.copy2(source, target)

    print("\n--- 汇总 ---")
    for cls in ("wb", "sc", "dc", "wc"):
        if cls in PREFIX:
            print(f"  {cls}: {counter[cls]} 张")
    total = sum(counter.values())
    print(f"  合计: {total} 张")
    if missing:
        print(f"  [警告] 以下源文件找不到: {', '.join(missing)}")
    if args.dry_run:
        print("\n（dry-run 模式，未实际复制）")


if __name__ == "__main__":
    main()
