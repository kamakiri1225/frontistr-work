#import pandas as pd
from os import path
import numpy as np
import pathlib

import yaml

#######################################################################################
# class
#######################################################################################
class Data_import:

    @classmethod
    def data_import_01(cls, file_name_1, file_path_1):
        # 元コードは r"setting\settings.yml" とWindows形式で書いており、Linuxでは
        # バックスラッシュがファイル名の一部になってしまう。OS非依存に setting/settings.yml とする。
        #file_name_1 = "Quad4_FEM.inp"

        #f0_path = pathlib.Path(__file__).parent.resolve() / file_name_0
        f0_path = file_path_1 / "setting" / "settings.yml"
        print("path:", f0_path)

        # 階層を１つ上がったところに*.inpファイルがある
        #f1_path = pathlib.Path(__file__).parent.resolve().parents[0] / file_name_1
        f1_path = file_path_1 / "Inp_Data" /file_name_1
        
        #settings.yamlの情報取得
        with f0_path.open(mode="r", encoding="utf-8") as f:
            sets = yaml.safe_load(stream=f)
            word1 = sets["Word_1"]
            word2 = sets["Word_2"]
            word3 = sets["Word_3"]
            word4 = sets["Word_4"]
            word5 = sets["Word_5"]
            word6 = sets["Word_6"]
            word7 = sets["Word_7"]
            word8 = sets["Word_8"]
            word9 = sets["Word_9"]
            word10 = sets["Word_10"]
            word11 = sets["Word_11"]

        with open(f1_path) as f:
            lines = f.readlines()

        # 1:NODE   2:ELEMENT   3:Fixed_111   4:Point_A   5:Point_O   6:Fixed_001   7:fixed_010
        # 8:Fixed_011   9:Fixed_100   10:Fixed_101   11:Fixed_110
        search =(word1, word2, word3, word4, word5, word6, word7, word8, word9, word10, word11)
        
        id=np.zeros((len(search),2),dtype="int64")

        for i,word in enumerate(search):
            temp=[]; temp00=[]; temp01=[]          #初期化（使いまわすので）
            hit = 0
            for j,l in enumerate(lines):
                #検索
                if word in l:
                    #print(f"search_hit!!:{word}(start)---{j}")
                    id[i][0]= j
                    hit = 1
                elif ("*" in l) and (hit == 1):
                    #print(f"search_hit!!:{word}(end)---{j}")
                    id[i][1] = j
                    hit = 0
                    break
                if hit == 1:
                    temp.append(l.split(","))

            #情報がある場合
            if id[i][1] !=0:
                #不要な情報削除（先頭の情報をカット）
                for j in range(1,len(temp)):
                    temp00.append((temp[j]))

                #ゼロスタートにして各情報に分ける
                if i == 0:          #node
                    node=temp00
                    for k in range(len(temp00)):
                        node[k][0]=int(node[k][0])-1
                        #print(node[k])
                    #print("**pass:node",node[1])

                elif i == 1:        #element
                    element=temp00
                    for k in range(len(temp00)):
                        for kk in range(len(temp00[0])):
                            element[k][kk]=int(temp00[k][kk])-1
                    #print("**pass:element",element[1])

                else:               #上記以外
                    for k in range(len(temp00)):
                        for kk in range(len(temp00[k])):
                            temp01.append(int(temp00[k][kk])-1)

                    if i == 2:
                        f_111 = temp01
 
                    elif i == 3:
                        point_o = temp01

                    elif i == 4:
                        point_a = temp01

                    elif i == 5:
                        f_001 = temp01
                    
                    elif i == 6:
                        f_010 = temp01

                    elif i == 7:
                        f_011 = temp01

                    elif i == 8:
                        f_100 = temp01

                    elif i == 9:
                        f_101 = temp01

                    elif i == 10:
                        f_110 = temp01

            else:   #値が０の場合
                    if i == 2:
                        f_111 = [-1]

                    elif i == 3:
                        point_o = [-1]

                    elif i == 4:
                        point_a = [-1]

                    elif i == 5:
                        f_001 = [-1]
                    
                    elif i == 6:
                        f_010 = [-1]

                    elif i == 7:
                        f_011 = [-1]

                    elif i == 8:
                        f_100 = [-1]

                    elif i == 9:
                        f_101 = [-1]

                    elif i == 10:
                        f_110 = [-1]

        return(node,element,f_111,point_o,point_a,f_001,f_010,f_011,f_100,f_101,f_110)       

    # コア数指定の関数
    @classmethod
    def setting_core(cls, setting_core_path):
        # 元コードは r"setting\settings_cores.yml"（Windows形式）。OS非依存に修正。
        fcore_path = setting_core_path / "setting" / "settings_cores.yml"
        print("path:", fcore_path)

        
        #settings.yamlの情報取得
        with fcore_path.open(mode="r", encoding="utf-8") as f:
            sets = yaml.safe_load(stream=f)
            core = sets["core"]
            print(core)
    
        return core