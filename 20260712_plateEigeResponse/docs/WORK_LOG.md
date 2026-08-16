# plate 固有値解析 → 周波数応答解析 作業メモ（ブログ用）

## 目的
平板（plate）モデルで、まず**固有値解析**を行い、その結果を使って**周波数応答解析**（周期荷重 FLOAD）を行う。
固有値解析と周波数応答解析はフォルダを分けて管理する。

## フォルダ構成
```
20260712_plateEigeResponse/
  unv/plate.unv          ← 元メッシュ（easyIstrサンプルからコピー）
  001_eigen/             ← Step1: 固有値解析
    FistrModel.msh
    FistrModel.cnt
    hecmw_ctrl.dat
  002_freqResponse/      ← Step2: 周波数応答解析（001_eigenの結果を参照）
    FistrModel.cnt
    hecmw_ctrl.dat
  docs/                  ← ブログ用メモ
```

## 解析条件
- 材料：Steel（ヤング率 2.06e11 Pa, ポアソン比 0.29, 密度 7860 kg/m³）
- 拘束：`fix` グループを完全固定（X/Y/Z）
- 周波数応答の荷重：`load` グループに周期荷重 FLOAD、Z方向 1.0 N（LOAD_CASE=1 実部）
- モニタ出力：nodeID=2、変位、sampling数10、出力指定 2:物理空間
- 周波数応答の設定（easyIstr 4-4-2-2 準拠）
  - TYPE=線形解析、運動方程式=陽解法（中央差分法）
  - 開始・終了 Hz：14000, 16000／全step数：20／変位計算 Hz：15000
  - 開始・終了時間：0.0, 6.6e-5／Rm, Rk：0.0, 7.2e-7

## 手順

### 1. UNV → FrontISTR メッシュ変換
.unvはそのままでは使えないため、easyIstr同梱の `unv2fistr.py` で `.msh` に変換する。
コマンドで直接実行する場合は環境変数が必要（GUIから実行する場合は不要）。

```bash
export easyIstrPath=/mnt/c/DEXCS/easyIstrPython/easyIstr
export easyIstrUserPath=/mnt/d/work/easyIstrUser
export PYTHONPATH=/mnt/c/DEXCS/easyIstrPython/easyIstr/python:/mnt/c/DEXCS/easyIstrPython/easyIstr/bin
mkdir -p /mnt/d/work/easyIstrUser/data/temp

cd 001_eigen
python3 /mnt/c/DEXCS/easyIstrPython/easyIstr/bin/unv2fistr.py ../unv/plate.unv FistrModel.msh
# 引数: <入力.unv> <出力名>
```

### 2. 固有値解析（001_eigen）
- `!SOLUTION,TYPE=EIGEN` + `!EIGEN`（固有値数, 許容差, 最大反復数）
- `!BOUNDARY` で fix を完全固定
- 材料 Steel
- 実行：`~/local/frontistr/bin/fistr1`
- 出力される `eigen_log` を周波数応答が参照する

### 3. 周波数応答解析（002_freqResponse）
- `!SOLUTION,TYPE=DYNAMIC` + `!DYNAMIC`（周波数応答モード）
- `!EIGENREAD` で 001_eigen の固有値結果を読み込む
- `!FLOAD` で load グループに周期荷重
- hecmw_ctrl.dat で ../001_eigen のメッシュ・固有値結果を参照

## メモ
- fistr1 は PATH に無く、`~/local/frontistr/bin/fistr1` にある
- unv2fistr.py は pyFistr モジュール＋環境変数（easyIstrPath, easyIstrUserPath）が必要
