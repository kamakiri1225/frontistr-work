# biMetal 作業ログ (更新: 2026-07-08)

## 作業概要
biMetalモデル（Al/Steel 2層板, 200×20×5mm）のFrontISTR熱応力解析

---

## ファイル構成

### ソースメッシュ
- UNVファイル: `c:\DEXCS\easyIstrPython\easyIstr\unvFiles\biMetal.unv`
- SI単位系 (kg-m-s)、節点数約5000、要素TYPE=351（三角柱）

### グループ一覧 (FistrModel.msh より)
| グループ名 | 種別 | 内容 |
|-----------|------|------|
| `fix` | NGROUP (節点) | 左端面の節点（固定端） |
| `load` | NGROUP (節点) | 右端面の節点（荷重端）※面要素グループではない |
| `press` | EGROUP (面要素 3048個) | 上下面の表面要素 |
| `top` | EGROUP (体積要素 6096個) | 上層 → Aluminum |
| `bottom` | EGROUP (体積要素 6096個) | 下層 → Steel |

### 材料 (FistrModel.cnt より)
| 材料名 | E [Pa] | ν | α [1/K] |
|--------|--------|---|---------|
| Aluminum | 70e9 | 0.345 | 25e-6 |
| Steel | 206e9 | 0.29 | 12e-6 |

---

## 解析フォルダ

### ① 熱応力解析（完了）
**フォルダ:** `d:\work\002_CAE\frontistr\work\20260707_biMetal\`

**設定:**
- 解析種別: `STATIC` (熱応力)
- 温度条件: `!TEMPERATURE` → 全節点 393K、参照温度 293K（ΔT=100K）
- 固定端: `fix` グループ 全3自由度固定
- 出力: DISP, NMISES, NSTRESS, EMISES, TEMP（RES+VIS両方）

**実行方法 (WSL):**
```bash
cd /mnt/d/work/002_CAE/frontistr/work/20260707_biMetal
~/local/frontistr/bin/fistr1 -t 1
```

**結果ファイル:**
- `FistrModel.vis_psf.0001.pvtu` → ParaViewで開く
- DISPLACEMENT, NodalMISES, NodalSTRESS, TEMP が含まれる

**初期化コマンド:**
```bash
cd /mnt/d/work/002_CAE/frontistr/work/20260707_biMetal
rm -f FSTR.* 0.log FistrModel.res.* FistrModel.vis_psf.*.pvtu FistrModel.restart.* hecmw_vis.ini
rm -rf FistrModel.vis_psf.0000 FistrModel.vis_psf.0001
```

---

### ② 熱流束解析（セットアップ中）
**フォルダ:** `d:\work\002_CAE\frontistr\work\20260707_biMetal_heatFilm\`

**目標:**
- Step1: 熱伝導解析（`press`面に対流BC: h=10 W/m²K, T_amb=393K、`fix`節点固定温度293K）
- Step2: 熱応力解析（Step1の温度分布を読み込み）

**制約メモ:**
- `load` グループは NGROUP（節点グループ）のため `!FILM` に直接使用不可
- `press` グループ（面要素）を対流BCの対象として代用
- 右端面に対流BCを設定したい場合はSALOMEで面要素グループを追加する必要あり

**現在の状態:** cnt ファイル未作成（作業中断）

---

## FrontISTR 実行パス (WSL)
```bash
~/local/frontistr/bin/fistr1   # version 5.9
# またはPATHを通す場合:
export PATH="$HOME/local/frontistr/bin:$PATH"
fistr1 -t 1
```

## easyIstr ツール (Windows)
- 変換スクリプト: `c:\DEXCS\easyIstrPython\easyIstr\bin\unv2fistr.py`
- copyスクリプト: `c:\DEXCS\easyIstrPython\easyIstr\python\copyFilesFromTempToCurrDir.py`
