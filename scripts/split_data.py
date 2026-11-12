#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""按 9:1 拆分 train / val，并生成 data.yaml。

约定目录（YOLO 常见布局）：
    datasets/VOCdevkit/JPEGImages   <- 图片
    datasets/VOCdevkit/txt          <- 标注（同名 .txt），另有 classes.txt

输出：
    datasets/train/{images,labels}
    datasets/valid/{images,labels}
    datasets/data.yaml

注意：
  - 用固定随机种子，保证每次拆分结果一致、实验可复现
  - 只用"同时存在 .txt 和 .jpg"的样本，避免拆分时报 FileNotFoundError
  - data.yaml 的类别顺序来自 classes.txt 的行顺序，改顺序等于改标签含义

用法：
    python scripts/split_data.py --root datasets --val-ratio 0.1
"""
import argparse
import random
import shutil
from pathlib import Path

IMG_EXT = {".jpg", ".jpeg", ".png"}


def collect_pairs(img_dir: Path, txt_dir: Path):
    """返回 (stem, img_path, txt_path) 列表，只保留图片和标注都存在的。"""
    pairs, orphan_txt, orphan_img = [], [], []

    txt_stems = {p.stem for p in txt_dir.glob("*.txt") if p.name != "classes.txt"}
    img_map = {p.stem: p for p in img_dir.iterdir() if p.suffix.lower() in IMG_EXT}

    for stem in txt_stems:
        if stem in img_map:
            pairs.append((stem, img_map[stem], txt_dir / f"{stem}.txt"))
        else:
            orphan_txt.append(stem)
    for stem in img_map:
        if stem not in txt_stems:
            orphan_img.append(stem)

    return sorted(pairs), sorted(orphan_txt), sorted(orphan_img)


def read_classes(path: Path):
    if not path.exists():
        raise SystemExit(
            f"找不到 {path}\n"
            "请先创建它，内容为四行（顺序不能变）：\n"
            "    wb\n    sc\n    dc\n    wc"
        )
    classes = [ln.strip() for ln in path.read_text(encoding="utf-8-sig").splitlines() if ln.strip()]
    if not classes:
        raise SystemExit(f"{path} 是空的！这会导致 data.yaml 里 nc: 0，训练直接崩。")
    return classes


def main():
    ap = argparse.ArgumentParser(description="拆分 train/val 并生成 data.yaml")
    ap.add_argument("--root", default="datasets", help="数据集根目录")
    ap.add_argument("--val-ratio", type=float, default=0.1, help="验证集比例，默认 0.1")
    ap.add_argument("--seed", type=int, default=0, help="随机种子，默认 0（保证可复现）")
    args = ap.parse_args()

    root = Path(args.root)
    img_dir = root / "VOCdevkit" / "JPEGImages"
    txt_dir = root / "VOCdevkit" / "txt"
    classes = read_classes(txt_dir / "classes.txt")

    pairs, orphan_txt, orphan_img = collect_pairs(img_dir, txt_dir)
    if not pairs:
        raise SystemExit(f"在 {img_dir} 和 {txt_dir} 里没找到配对的图片+标注")

    print(f"类别（{len(classes)}）: {classes}")
    print(f"可用样本: {len(pairs)}")
    if orphan_txt:
        print(f"[警告] 有标注但没图片: {len(orphan_txt)} 个，例如 {orphan_txt[:3]}")
    if orphan_img:
        print(f"[提示] 有图片但没标注: {len(orphan_img)} 个，例如 {orphan_img[:3]}（将被忽略）")

    random.seed(args.seed)
    shuffled = pairs[:]
    random.shuffle(shuffled)
    n_val = max(1, int(len(shuffled) * args.val_ratio))
    val, train = shuffled[:n_val], shuffled[n_val:]

    for split in ("train", "valid"):
        for sub in ("images", "labels"):
            d = root / split / sub
            if d.exists():
                shutil.rmtree(d)
            d.mkdir(parents=True, exist_ok=True)

    def dump(items, split):
        for _stem, img, txt in items:
            shutil.copy2(img, root / split / "images" / img.name)
            shutil.copy2(txt, root / split / "labels" / txt.name)

    dump(train, "train")
    dump(val, "valid")

    yaml_path = root / "data.yaml"
    yaml_path.write_text(
        "train: data/train/images\n"
        "val: data/valid/images\n"
        f"nc: {len(classes)}\n"
        f"names: [{', '.join(classes)}]\n",
        encoding="utf-8",
    )

    print(f"\n拆分完成: train={len(train)}  valid={len(val)}  (val 占比 {n_val / len(pairs):.1%})")
    print(f"已生成 {yaml_path}:\n---\n{yaml_path.read_text(encoding='utf-8')}---")


if __name__ == "__main__":
    main()
