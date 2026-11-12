#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""清理 YOLO 标注文件中的空行。

labelImg 在"图上没有画框"时会生成一个空 txt，或者留下多余空行。
YOLO 训练时遇到纯空行会报错或静默出错，所以在拆分数据集之前先清理。

用法：
    python scripts/clean_labels.py --labels datasets/VOCdevkit/txt
"""
import argparse
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description="清理 YOLO 标注空行")
    ap.add_argument("--labels", required=True, help="标注 txt 目录")
    args = ap.parse_args()

    labels = Path(args.labels)
    if not labels.is_dir():
        raise SystemExit(f"目录不存在: {labels}")

    cleaned = 0
    emptied = 0
    for path in sorted(labels.glob("*.txt")):
        if path.name == "classes.txt":
            continue

        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        kept = [ln for ln in lines if ln.strip()]

        if len(kept) != len(lines):
            path.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
            cleaned += 1
        if not kept:
            emptied += 1

    print(f"扫描 {len(list(labels.glob('*.txt')))} 个文件")
    print(f"清理了 {cleaned} 个文件")
    print(f"其中 {emptied} 个文件清理后为空（说明对应图片没有标注任何目标）")


if __name__ == "__main__":
    main()
