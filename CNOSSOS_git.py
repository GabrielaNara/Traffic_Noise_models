# -*- coding: utf-8 -*-
"""
Created on Mon Feb 24 00:06:24 2020

@author: NaraPeixoto
"""

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
local = "avenida1" #devido ao tempo de processamente somente 1 local é feito por vez

#DADOS DE FLUXO:
xlsx = pd.ExcelFile("MEDICAO.xlsx") 
fluxo = pd.read_excel(xlsx, '%s' %local, index_col="medicao")

#definindo as avenidas:
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
dat_emissores["id_point"] = dat_emissores["idpoint"]
dat_emissores = dat_emissores.set_index("id_point")

#Shape de recptores do QGIS
frM = ("%s/PONTOS_RECEPTORES_%s.shp") % (local,local) 
dat_receptoresM = gpd.read_file(frM)
dat_receptoresM ["id_point"] = dat_receptoresM['idpoint']
dat_receptoresM = dat_receptoresM.sort_values(by = ['idpoint'], ascending = [True])
dat_receptoresM = dat_receptoresM.set_index("id_point")

#Criação das colunas de fluxo no shape emissores do QGIS
colunas = ["Tmed","leve","pesado","art","moto","vel"]
NX = len(fluxo)

#lendo matriz de distancias emissores x receptores
dist = pd.read_csv(("%s/MATRIZ_DISTANCIAS_%s_csv.csv")% (local,local))
dist["dist"] = dist.apply(lambda x: (math.sqrt(x[2]**2 + 1)),axis=1)
recep = dist["ptr"].unique()

# --------------------------------------------------------------------------------------------------------------------
# CALCULOS CNOSSOS:
for x in fluxo.index:
    for k in range(6):
        a = colunas[k]
        def a(row): 
            for i in range(len(conjunto_vias)):
                if dat_emissores.nome[row] == conjunto_vias[i]:
                    return fluxo.loc[x,"%s_%s" %(conjunto_vias[i],colunas[k])]
        dat_emissores["%s" %colunas[k]] = [a(row) for row in dat_emissores['idpoint']] 
    dat_emissores = dat_emissores.astype({"leve" :float,"pesado":float,"art" :float,"moto" :float, "vel":float})
       
    def Lw_freq(row):
        lista = []
        vel = dat_emissores.vel[row] 
        HubDist = dat_emissores.HubDist[row] #distância do ponto ao semáforo mais próximo
        Vref = 70 #velocidade de referência CNOSSOS 
        slope = dat_emissores.slope[row]/100 
        
        for f in range(8):
            # Correction by pavimento
            def LRroad(row,f):
                if row == "Asfalto":
                    return cnossos.NL0_a[f] + cnossos.NL0_b[f]*math.log10(vel/Vref) 
                elif row == "Concreto":
                    return cnossos.NL08_a[f] + cnossos.NL08_b[f]*math.log10(vel/Vref) 
                elif row == "Pavimento":
                    return cnossos.NL10_a[f] + cnossos.NL10_b[f]*math.log10(vel/Vref) 
                elif row == "Material poroso":
                    return cnossos.NL13_a[f] + cnossos.NL13_b[f]*math.log10(vel/Vref) 
                else:
                    return cnossos.NL11_a[f] + cnossos.NL11_b[f]*math.log10(vel/Vref) 
            soma = 0
            for categoria in range(1,5):
                xlsx2 = pd.ExcelFile("tabelas_cnossos.xlsx") 
                cnossos = pd.read_excel(xlsx2, 'm%s' %categoria, index_col="index")
                # Fluxo de veículos
                def Q(row,categoria):
                    Tmed = dat_emissores.Tmed[row] #tempo de medição
                    if categoria == 1:
                        return dat_emissores.leve[row]*60/Tmed #fluxo de leves
                    elif categoria == 2: 
                         return dat_emissores.pesado[row]*60/Tmed  #fluxo de pesados
                    elif categoria == 3: 
                         return dat_emissores.art[row]*60/Tmed #fluxo de articulados (3 eixos)
                    elif categoria == 4: 
                         return dat_emissores.moto[row]*60/Tmed  #tempo de motos
                    else:
                         return 0
                # Correction by Acelerações e desacelerações
                def LRacc(row,f,categoria):   
                    if categoria == 1 or categoria == 2 or categoria == 3 :        
                        if aceleracao == "semaforo":
                            return cnossos.cr_crossing[f]*max(1-(HubDist/100),0)
                        elif aceleracao == "rotatoria":
                            return cnossos.cr_roundabout[f]*max(1-(HubDist/100),0)
                        else:
                            return 0
                    else:
                        return 0
                def LPacc(row,f,categoria):  
                    if categoria == 1 or categoria == 2 or categoria == 3 :        
                        if aceleracao == "semaforo":
                            return cnossos.cp_crossing[f]*max(1-HubDist/100,0)
                        elif aceleracao == "rotatoria":
                            return cnossos.cp_roundabout[f]*max(1-HubDist/100,0)
                        else:
                            return 0
                    else:
                        return 0
                # Correction by temperature 
                def LRtemp(categoria):
                    if categoria == 1 :
                        return 0.08*(20 - T)
                    if categoria == 2 or categoria == 3:
                        return 0.04*(20 - T)
                    else:
                        return 0
                # Correction by Gradiente da via:
                def LPgrad(row,categoria):
                    if categoria == 1:
                        if slope < -0.06:
                            return (min(0.12,slope*(-1))-0.06)/0.01
                        if slope > 0.02:
                            return ((min(0.12,slope)-0.02)*vel)/(0.015*100)
                        else:
                            return 0
                    if categoria == 2:        
                        if slope < -0.04:
                            return (min(0.12,slope*(-1))-0.04)*(vel-20)/(0.007*100)
                        if slope > 0:
                            return min(0.12,slope)*vel/(0.01*100)
                        else:
                            return 0
                    if categoria == 3:
                        if slope < -0.04:
                            return (min(0.12,slope*(-1))-0.04)*(vel-10)/(0.005*100)
                        if slope > 0:
                            return min(0.12,slope)*vel/(0.008*100)
                        else:
                            return 0
                    else:
                        return 0
                    
                #CÁLCULOS ruído motor (Lwr) e rolagem (Lwp):
                Lwr = cnossos.ar[f] + cnossos.br[f]*math.log10(vel/Vref) + LRroad(row,f) + LRacc(row,f,categoria) + LRtemp(categoria)  #ruído de rolagem(Lwr)
                Lwp = cnossos.ap[f] + cnossos.bp[f]*((vel-Vref)/Vref) + LPacc(row,f,categoria) + LPgrad(row,categoria)  #ruído de motor
                Lwim_unico = 10*math.log10(10**(Lwr/10)+10**(Lwp/10)) #ruído de rolagem(Lwr) + motor(Lwp) para veículo individual
                if Q(row,categoria) != 0: 
                    Lwim = Lwim_unico + 10*math.log10(Q(row,categoria)/(1000*vel)) #ruído de rolagem(Lwr) + motor(Lwp) por grupo de veiculos
                else: 
                    Lwim = 0
                soma = soma + 10**(Lwim/10)
            #print(10*math.log10(soma)) 
            lista.append(10*math.log10(soma))
        return lista
    
    lista2 = []
    for row in range(1,len(dat_emissores)+ 1): #len(dat_emissores)+ 1
        lista2.append(Lw_freq(row))
        #print(r)
    
    index = dat_emissores.idpoint
    df = pd.DataFrame(lista2, index = index)
    df.columns = ["cnossos_f0","cnossos_f1","cnossos_f2","cnossos_f3","cnossos_f4","cnossos_f5","cnossos_f6","cnossos_f7"]
    
    #PROPAGAÇÃO
    #-------------------------------------------------------------------
    # Atenuação atmosférica:
    Aatm = [0.0658077011456787, 0.254915341813177, 0.958129558730322,\
            3.09684086679252, 7.1955887593948, 12.3129015633058,\
                22.738855237777, 60.1091719367715]
    # Diferenças da curva db(A):
    Curva = [26.2, 16.1, 8.6, 3.2, 0, -1.2, -1, -1.1]
    
    Aground = 3 # Reflexões no solo
    Abuild = 3 # Reflexões na fachada
    
    #-------------------------------------------------------------------
    
    cnossos2 = [] 
    for ptr in recep:
        cnossos = [] 
        for f in range(8):        
            dist['reduc'] = dist.apply(lambda x: (20*math.log10(x[3])+11 + Aatm[f]*x[3]/1000 - Aground - Abuild + Curva[f]),axis=1)
            dist['efeito'] = dist.apply(lambda x: 10**((df.loc[x[0],"cnossos_f%s" %f]-x[4])/10),axis=1)
            soma_efeito = dist.groupby('ptr').sum()[['efeito']]
            soma_efeito['%s' %f] = soma_efeito.apply(lambda x: 10*math.log10(x[0]),axis = 1)
            cnossos.append(soma_efeito['%s' %f])    
        df2 = pd.DataFrame(cnossos, columns = [ptr])     
        df2['efeito']= 10**(df2[ptr]/10)
        soma_efeito2 = df2.sum()[["efeito"]]        
        soma_efeito2["ptr"] = 10*math.log10(soma_efeito2[0])
        cnossos_ptr = soma_efeito2["ptr"]
        cnossos2.append([ptr, cnossos_ptr])
        
    cnossos_final = pd.DataFrame(cnossos2, columns = ["ptr","Leq"])
    cnossos_final.to_csv(("%s/cnossos_propagacao/cnossos_%s_medicao%s.csv")% (local,local,x),sep=';',decimal=',')
    
    intermed = time.time()
    tempototal = intermed - tempo2
    tempo2 = intermed
    print('Tempo da rodada %02i-%02i: %6.2f minutos.' % (x,NX,tempototal/60)) 

