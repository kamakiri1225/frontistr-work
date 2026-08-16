# biMetal_heatFilm 解析計画

## やりたいこと

`20260707_biMetal`（prescribed温度）とは別に、
**熱伝達係数（対流BC）を与えた熱伝導→熱応力の2ステップ解析**を行う。

---

## 解析フロー

```
Step 1: 熱伝導解析
  入力: press面に対流BC (h=10 W/m²K, T_amb=393K)
        fix節点に固定温度 293K
  出力: FistrModel.res.0.1 (温度分布)
          └→ ParaViewで TEMP 確認

Step 2: 熱応力解析
  入力: Step1の温度分布を読み込み
        fix節点を全拘束
  出力: FistrModel.vis_psf.0001.pvtu
          └→ ParaViewで DISP, MISES 確認
```

---

## フォルダ構成

```
20260707_biMetal_heatFilm/
├── FistrModel.msh          # コピー済み（20260707_biMetalから）
├── hecmw_ctrl.dat          # コピー済み
├── FistrModel_step1.cnt    # 未作成 ← 次に作る
├── FistrModel_step2.cnt    # 未作成 ← 次に作る
└── docs/
    └── plan.md             # このファイル
```

---

## Step1 cnt ファイル内容（案）

```
!VERSION
 3
!WRITE,RESULT
!WRITE,VISUAL
!SOLUTION, TYPE=HEAT
!HEAT
 0.0
!OUTPUT_RES
TEMP, ON
!OUTPUT_VIS
TEMP, ON
!FIXTEMP, GRPID=1
fix, 293.0
!FILM, GRPID=1
press, 10.0, 393.0
!VISUAL, method=PSR
!surface_num=1
!surface
!display_method=1
!output_type = VTK
!END
```

**ポイント:**
- `!HEAT` の引数 `0.0` = 定常解析（非定常は時間刻みを指定）
- `!FIXTEMP` = 節点グループに温度固定（fix=左端面 293K）
- `!FILM` = 面要素グループに対流BC（press=上下面 h=10, T_amb=393K）

---

## Step2 cnt ファイル内容（案）

```
!VERSION
 3
!WRITE,RESULT
!WRITE,VISUAL
!SOLUTION, TYPE=STATIC
!STATIC
!SOLVER,METHOD=CG,PRECOND=1,ITERLOG=NO,TIMELOG=YES
 20000, 2
 1.00000e-06, 1.00000, 0.00000
 0.100000, 0.100000
!OUTPUT_RES
DISP, ON
NMISES, ON
NSTRESS, ON
EMISES, ON
TEMP, ON
!OUTPUT_VIS
DISP, ON
NMISES, ON
NSTRESS, ON
EMISES, ON
TEMP, ON
!BOUNDARY, GRPID=1
fix, 1, 1, 0.0
fix, 2, 2, 0.0
fix, 3, 3, 0.0
!TEMPERATURE, READRESULT=1, RSTEP=1
!REFTEMP
 293.0
!MATERIAL, NAME=Aluminum
!ELASTIC, TYPE=ISOTROPIC
70000000000, 0.345
!DENSITY
2690
!EXPANSION_COEFF, DEPENDENCIES=0
0.000025
!MATERIAL, NAME=Steel
!ELASTIC, TYPE=ISOTROPIC
206000000000, 0.29
!DENSITY
7860
!EXPANSION_COEFF, DEPENDENCIES=0
0.000012
!VISUAL, method=PSR
!surface_num=1
!surface
!display_method=1
!output_type = VTK
!END
```

**ポイント:**
- `!TEMPERATURE, READRESULT=1, RSTEP=1` = Step1の結果ファイルから温度を読み込む
- `!REFTEMP 293.0` = 基準温度（熱ひずみ = α × (T - T_ref)）

---

## 実行手順（WSL）

```bash
cd /mnt/d/work/002_CAE/frontistr/work/20260707_biMetal_heatFilm

# Step1: FistrModel.cnt を step1 に差し替えて実行
cp FistrModel_step1.cnt FistrModel.cnt
~/local/frontistr/bin/fistr1 -t 1

# 結果確認後、Step2 実行
cp FistrModel_step2.cnt FistrModel.cnt
~/local/frontistr/bin/fistr1 -t 1
```

---

## 注意事項・制約

- `load` グループは **節点グループ(NGROUP)** のため `!FILM` に使用不可
  - 右端面に対流BCを設定したい場合は SALOMEで面要素グループを追加する必要あり
  - 現状は `press`（上下面）で代用
- `press` グループは上下面の面要素 3048個
- Step2 の `!TEMPERATURE, READRESULT` 構文は FrontISTR 5.x で動作確認要
