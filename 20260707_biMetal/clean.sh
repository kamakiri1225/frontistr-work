#!/bin/bash
# FrontISTR実行結果のクリーンアップ
# 残すファイル: FistrModel.cnt, FistrModel.msh, hecmw_ctrl.dat, unv/, vtkMeshData/
set -eu
cd "$(dirname "$0")"

rm -f FSTR.* 0.log FistrModel.res.* FistrModel.restart.* hecmw_vis.ini FistrModel.log
rm -rf FistrModel.vis_psf.*
