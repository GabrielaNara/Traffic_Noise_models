# -*- coding: utf-8 -*-
"""
Created on Mon Feb 24 00:06:24 2020

@author: NaraPeixoto
"""

import numpy as np
import geopandas as gpd
import pandas as pd
import math
import time

inicio = time.time()
tempo2 = inicio

#VARIÁVEIS
FatorK = 1 #Porcentagem de MOTO que é contabilizada como LEVE modelo RLS90
aceleracao = "semaforo" #escolher entre "semaforo", "rotatoria" ou "none"
T = 29 # Temperatura média em Fortaleza
h = 1.2 #altura da medição
validacao = 3 
lista_locais = ["avenida1","avenida","avenida3"]
modelo = "RLS90"
    
for local in lista_locais:
    #DADOS DE FLUXO:
    xlsx = pd.ExcelFile("MEDICAO.xlsx") 
    fluxo = pd.read_excel(xlsx, '%s' %local, index_col="medicao")
    
    conjunto_vias = fluxo["nome"].unique()
    print(conjunto_vias)
    
    for via in conjunto_vias:
        fluxo["%s_leve" %via ].fillna("0", inplace = True)
        fluxo["%s_pesado" %via].fillna("0", inplace = True)
        fluxo["%s_art" %via ].fillna("0", inplace = True)
        fluxo["%s_moto" %via ].fillna("0", inplace = True)    
    
    #Shape de emissores do QGIS
    fe  = ("%s/PONTOS_EMISSORES_%s.csv") % (local,local) 
    dat_emissores  = pd.read_csv(fe)
    #fe  = ("%s/Emissores_%s.shp") % (local,local) 
    #dat_emissores  = gpd.read_file(fe)
    dat_emissores["id_point"] = dat_emissores["idpoint"]
    dat_emissores = dat_emissores.set_index("id_point")
    
    frM = ("%s/PONTOS_RECEPTORES_%s.shp") % (local,local) 
    dat_receptoresM = gpd.read_file(frM)
    dat_receptoresM ["id_point"] = dat_receptoresM['idpoint']
    dat_receptoresM = dat_receptoresM.sort_values(by = ['idpoint'], ascending = [True])
    dat_receptoresM = dat_receptoresM.set_index("id_point")
        
    #Criação das colunas de fluxo no shape emissores do QGIS
    colunas = ["Tmed","leve","pesado","art","moto","vel"]
    
    # --------------------------------------------------------------------------------------------------------------------
    # CALCULOS RLS90:
    rls90 = [] 
    #for x in [1]:
    for x in fluxo.index: #x é o numero da medicao
        for k in range(6):
            a = colunas[k]
            def a(row): 
                for i in range(len(conjunto_vias)):
                    if dat_emissores.nome[row] == conjunto_vias[i]:
                        return fluxo.loc[x,"%s_%s" %(conjunto_vias[i],colunas[k])]
            dat_emissores["%s" %colunas[k]] = [a(row) for row in dat_emissores['idpoint']] 
        dat_emissores = dat_emissores.astype({"leve" :float,"pesado":float,"art" :float,"moto" :float, "vel":float})
          
        def RLS90_emissao(row,modelo):
            Tmed = dat_emissores.Tmed[row]  #tempo de medição
            leve = dat_emissores.leve[row] #fluxo de veículos leves
            pesado = dat_emissores.pesado[row] #fluxo de veículos pesados
            art = dat_emissores.art[row] #fluxo de veículos pesados articulados (3 eixos)
            moto = dat_emissores.moto[row] #fluxo de motos
            vel = dat_emissores.vel[row] #Velocidade dos veículos
            Hbuild = dat_emissores.Hbuild[row] #altura das edificacoes
            w = dat_emissores.w[row] #distancia entre os edifícios 
            pav = dat_emissores.pav[row] #distancia entre os edifícios 
            if aceleracao == "semaforo" or aceleracao == "rotatoria":
                HubDist = dat_emissores.HubDist[row] #distância do ponto ao semáforo mais próximo
            else:
                HubDist = 120 
            #CÁLCULOS
            #particao = distancia entre os pontos no eixo emissor
            particao = 1.5
            '''
            if w <= 13:
                particao = 2
            elif w > 13 and w < 30:
                particao = 2                   
            elif w >= 30 and w < 40:
                particao = 3       
            else:
                particao = 5 
            '''
            Fluxohora = ((leve + pesado + art + moto)*60)/(Tmed)
            porcpesados = (pesado + art +((1-FatorK)*moto))/(leve + pesado + art + moto)
            Lcar = 27.7 + 10 * math.log10(1+((0.02*vel)**3))
            Ltruck = 23.1 + 12.5*math.log10(vel)
            D = Ltruck - Lcar
            Dv = Lcar - 37.3 + 10 * math.log10((100+((10**(0.1*D))-1)*porcpesados)/(100 + 8.23*porcpesados))
            

            Lm = 37.3 + 10 *math.log10(Fluxohora*(1 + 0.082*porcpesados)) #RLS90

            DI = 10*math.log10(particao)
            Db = min(4*(Hbuild/w),3.2)
            def Dacc(HubDist):
                if HubDist <= 40:
                    return 3
                elif HubDist > 40 and HubDist <= 70: 
                    return 2
                elif HubDist > 70 and HubDist <= 100: 
                    return 1
                else: 
                    return 0
            def Dstro(pav):
                if pav == "Asfalto":
                    return 0
                elif pav == "Concreto":
                    return 2
                elif pav == "Pavimento":
                    return 3
                elif pav == "Material poroso": 
                    return -3 
                else:
                    return 6
            Lme = Dv + Lm + DI + Db + Dstro(pav) + Dacc(HubDist)
            return Lme
        
        # iterating over one column - `f` is some function that processes your data
        # result = [f(x) for x in df['col']]
        dat_emissores["RLS90_emissao"] = [RLS90_emissao(row,"%s" %modelo) for row in dat_emissores['idpoint']] 
         
        dist = pd.read_csv(("%s/MATRIZ_DISTANCIAS_%s.csv")% (local,local)) 
        dist["dist"] = dist.apply(lambda x: (math.sqrt(x[2]**2 + (h - 0.5)**2)),axis=1)
        dist['reduc'] = dist.apply(lambda x: (11.2 - 20*math.log10(x[3])-x[3]/200) + min(((1.5/x[3])*(34+600/x[3])-4.8),0),axis=1)
        dist['efeito'] = dist.apply(lambda x: 10**((dat_emissores.RLS90_emissao[x[0]]+x[4])/10),axis=1)
        soma_efeito = dist.groupby('ptr').sum()[['efeito']]
        soma_efeito['%s' %x] = soma_efeito.apply(lambda x: 10*math.log10(x[0]),axis = 1)
        rls90.append(soma_efeito['%s' %x])
      
    rls90 = pd.DataFrame(rls90, dtype=np.float64)
    rls90.to_csv(("rls90_%s.csv")%local,sep=';',decimal=',')
     
final = time.time()
tempototal = final - inicio
print('Tempo total: %8.5f minutos.' % (tempototal/60))

