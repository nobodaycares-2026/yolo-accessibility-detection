# 完整流程与踩坑记录

记录整个项目的操作链路，以及每一步实际遇到的问题。
写给未来的自己看，也给想看这个仓库的人一个交代。

---

## 流程总览

```
原始素材(150张)
   ↓  人工筛选、按类别重命名
JPEGImages(149张)  Wb01-34 / Sc01-20 / Dc01-46 / Wc01-49
   ↓  labelImg 标注（YOLO 格式）
txt/(149个标注文件 + classes.txt)
   ↓  clean_labels.py  清理空行
   ↓  split_data.py    9:1 拆分 + 生成 data.yaml
train/(135) + valid/(14)
   ↓  train_dual.py  100 epochs
runs/train/exp/weights/best.pt
   ↓  detect_dual.py
带检测框的结果图
```

---

## 第 0 步　环境

- Windows + 一个已经配好 PyTorch 的 Python 3.8 虚拟环境
- labelImg 1.8.6
- **路径必须是纯英文**，例如 `D:\yolov9`。含中文会出现软件闪退、
  训练报错、文件读写失败等各种不可预期的结果。

## 第 1 步　数据筛选与命名

从 150 张素材里筛出含四类目标的图片，按类别重命名：

| 标签 | 含义 | 前缀 | 数量 |
|---|---|---|---|
| `wb` | 盲人（持盲杖） | `Wb` | 34 |
| `sc` | 拄单拐 | `Sc` | 20 |
| `dc` | 拄双拐 | `Dc` | 46 |
| `wc` | 坐轮椅 | `Wc` | 49 |

编号规则：同一类从 `01` 起，按原图的数字顺序递增。

**踩坑**：Windows 资源管理器按字符串排序，`1.jpg, 10.jpg, 100.jpg…`
不是 `1, 2, 3…`。人工编号时很容易跳号或重号，
所以写了 `filter_rename.py`，用自然排序保证编号连续可复现。

## 第 2 步　标注

- 工具：labelImg
- 格式：**YOLO**（不是 PascalVOC）
- 保存目录：`datasets/VOCdevkit/txt`

**最大的坑**：`classes.txt` 出厂是空的。
这个文件会被 `split_data.py` 读取，用来生成 `data.yaml` 的
`nc`（类别数）和 `names`。它如果为空：

- `data.yaml` 变成 `nc: 0`，训练直接崩
- 如果手写但顺序错了，四类标签会整体错位，模型学到的类别全反

正确内容（顺序不能换）：

```
wb
sc
dc
wc
```

标注规范（见 README 第 2 节）。

## 第 3 步　清理标注

```bash
python scripts/clean_labels.py --labels datasets/VOCdevkit/txt
```

labelImg 在"图上没画框"时会留空文件或空行。不清理的话，
拆分和训练阶段会报一些很难定位的错。

## 第 4 步　拆分数据集

```bash
python scripts/split_data.py --root datasets --val-ratio 0.1
```

- 9:1 拆分，固定 `seed=0`，可复现
- 只保留"图片和标注都在"的样本，避免复制时报 `FileNotFoundError`
- 自动生成 `data.yaml`

拆分完**先检查 `data.yaml`**：

```yaml
train: data/train/images
val: data/valid/images
nc: 4
names: [wb, sc, dc, wc]
```

`nc` 必须是 4。不是 4 就别往下走。

## 第 5 步　训练

```bash
python train_dual.py \
  --weights yolov9-c.pt \
  --cfg models/detect/yolov9-c.yaml \
  --data data/data.yaml \
  --batch-size 1 --epochs 100
```

**注意**：YOLOv9-c 是双头结构，要用 `train_dual.py`，
用 `train.py` 会报错。

**踩坑**：训练启动后会尝试下载 `Arial.ttf` 作为可视化字体，
网络不通时会卡住。解决办法是把字体文件手动放到
`%APPDATA%\Ultralytics\Arial.ttf`。

**踩坑**：不需要等 100 个 epoch 跑完。
第一个 epoch 能正常打印 loss 和 dataloader 信息，就说明链路通了；
后面只是时间问题。

## 第 6 步　推理

```bash
python detect_dual.py \
  --weights runs/train/exp/weights/best.pt \
  --source <目录> \
  --conf-thres 0.5
```

结果默认输出到 `runs/detect/exp/`。

**踩坑**：如果 `test-data` 里混进了不该检测的图片，
结果会多出一堆无关图。推理前先确认源目录干净。

---

## 复盘：如果重做一次，我会怎么改

1. **先写 classes.txt，再动手标注。** 顺序搞反会白标一批。
2. **先跑通 5 张图的完整链路，再上全量。** 用 5 张图验证
   标注→拆分→训练→推理能走通，比标完 149 张才发现格式错了要划算得多。
3. **去重。** 素材里有完全相同的图（sha256 一致），会轻微影响
   val 指标的客观性。
4. **类别不均衡。** 单拐 20 张 vs 轮椅 49 张，差一倍多。
   如果指标上不去，先看是不是小类别被压了。
