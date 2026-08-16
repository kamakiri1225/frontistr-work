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
    def data_import(cls, inpfileName):
        file_name_0 = "settings.yml"
        file_name_1 = "./Inp_Data/" + inpfileName#"Quad4_FEM.inp"

        f0_path = pathlib.Path(__file__).parent.resolve() / file_name_0
        
        # 階層を１つ上がったところに*.inpファイルがある
        f1_path = pathlib.Path(__file__).parent.resolve().parents[0] / file_name_1
        
        #settings.yamlの情報取得
        with f0_path.open(mode="r", encoding="utf-8") as f:
            sets = yaml.safe_load(stream=f)
            word1 = sets["Word_1"]
            word2 = sets["Word_2"]
            word3 = sets["Word_3"]
            word4 = sets["Word_4"]
            word5 = sets["Word_5"]
            word6 = sets["Word_6"]

        with open(f1_path) as f:
            lines = f.readlines()
        # Fixed--->node,    Face_load-->node,   Force-->node,   F_L_Element-->element
        #search =("NODE","ELEMENT","Fixed","Face_load","Force","F_L_Element")
        search =(word1, word2, word3, word4, word5, word6)
        
        id=np.zeros((len(search),2),dtype="int64")

        for i,word in enumerate(search):
            temp=[]; temp00=[]; temp01=[]          #初期化（使いまわすので）
            hit = 0
            for j,l in enumerate(lines):
                #検索
                if word in l:
                    #print("search:",word)
                    #print(l)
                    id[i][0]= j
                    hit = 1
                elif ("*" in l) and (hit == 1):
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
                        fixed = temp01
                        #print("***pass:fixed",fixed) #--- ok
                    elif i == 3:
                        force = temp01
                        #print("***pass:face_load",face_load) #--- ok
                    elif i == 4:
                        face_load = temp01
                        #print("***pass:force",force) #--- ok
                    elif i == 5:
                        fl_element = temp01
                        #print("***pass:fl_element",fl_element) #--- ok    
            else:
                    if i == 3:
                        force = [0]
                        #print(face_load) --- ok
                    elif i == 4:
                        face_load = [0]
                        #print(force) --- ok
                    elif i == 5:
                        fl_element = [0]
                        #print(fl_element) --- ok 

        return(node,element,fixed,force, face_load, fl_element)       