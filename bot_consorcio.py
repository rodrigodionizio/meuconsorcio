# -*- coding: utf-8 -*-
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---------------------------------------------------------------------------
# CONFIGURAÇÃO OFICIAL - GRUPO 1147
# ---------------------------------------------------------------------------
COTA_RODRIGO = 3177
TOTAL_COTAS_GRUPO = 5000
VACANCIA_ESTIMADA = 0.61  # 61% de desistentes conforme o app
CONTEMPLADOS_TOTAL_MES = 30  # Média total (Sorteio + Livres + Fixos)
VAGAS_LANCE_FIXO_25 = 11     # Vagas específicas da sua categoria

# Regra VW: 2º ao 5º algarismo do 1º prêmio
DIGITOS_INICIO = 1 
DIGITOS_FIM = 5

# Fuso Horário de Brasília (Leste Mineiro)
FUSO_BR = timezone(timedelta(hours=-3))

ARQUIVO_SAIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dados.json")

def extrair_alvo(numero_federal):
    """Extrai o milhar alvo e aplica a regra de normalização do grupo."""
    # Garante 5 dígitos (ex: 83358) ou trata 6 dígitos se vier série (ex: 083358)
    s = "".join(ch for ch in str(numero_federal) if ch.isdigit())
    s = s.zfill(5)[-5:] 
    
    # Isola o milhar (2º ao 5º dígito)
    milhar_extraido = int(s[DIGITOS_INICIO:DIGITOS_FIM])
    
    # Aplica a regra de normalização para o grupo de 5000
    alvo = milhar_extraido % TOTAL_COTAS_GRUPO
    if alvo == 0: 
        alvo = TOTAL_COTAS_GRUPO
        
    return alvo, milhar_extraido

def calcular_probabilidades(alvo):
    """Calcula a posição real na fila considerando a vacância de 61%."""
    distancia = abs(alvo - COTA_RODRIGO)
    
    # Estimativa de quantas pessoas 'vivas' existem no trajeto do sorteio
    concorrentes_ativos = distancia * (1 - VACANCIA_ESTIMADA)
    
    # Estimativa de quem deu lance fixo de 25% (aprox 50% dos ativos)
    fila_real_estimada = round(concorrentes_ativos * 0.5, 1)
    
    # Status de proximidade (Régua de Corte histórica ~22)
    if fila_real_estimada <= VAGAS_LANCE_FIXO_25:
        status = "ZONA DE VITÓRIA (Top 11)"
    elif fila_real_estimada <= 25:
        status = "ZONA DE CALOR (Iminente)"
    else:
        status = "FORA DO RAIO"

    # Estimativa de espera baseada na saúde financeira do grupo (30 contemplados/mês)
    ativos_totais = TOTAL_COTAS_GRUPO * (1 - VACANCIA_ESTIMADA)
    meses_restantes = round(ativos_totais / CONTEMPLADOS_TOTAL_MES)

    return {
        "distancia_nominal": distancia,
        "fila_real_estimada": fila_real_estimada,
        "status": status,
        "meses_espera_estatistica": meses_restantes
    }

def buscar_federal():
    """Busca o resultado oficial na API da Caixa."""
    url = "https://servicebus2.caixa.gov.br/portaldeloterias/api/federal"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, verify=False, timeout=20)
        dados = r.json()
        primeiro_premio = dados['listaDezenas'][0]
        return primeiro_premio, dados['numero'], dados['dataApuracao']
    except:
        # Fallback caso a API principal esteja fora
        r = requests.get("https://loteriascaixa-api.herokuapp.com/api/federal/latest")
        dados = r.json()
        return dados['dezenas'][0], dados['concurso'], dados['data']

def salvar(resultado):
    # Carrega histórico para não duplicar
    if os.path.exists(ARQUIVO_SAIDA):
        with open(ARQUIVO_SAIDA, "r") as f:
            db = json.load(f)
    else:
        db = {"historico": []}

    if not db["historico"] or db["historico"][0]["concurso"] != resultado["concurso"]:
        db["historico"].insert(0, resultado)
    
    db.update(resultado) # Atualiza dados do topo
    db["historico"] = db["historico"][:50] # Mantém 50 registros
    
    with open(ARQUIVO_SAIDA, "w") as f:
        json.dump(db, f, indent=2)

def main():
    primeiro, concurso, data = buscar_federal()
    alvo, bruto = extrair_alvo(primeiro)
    probs = calcular_probabilidades(alvo)
    
    final = {
        "concurso": concurso,
        "data": data,
        "federal": primeiro,
        "alvo": alvo,
        "cota": COTA_RODRIGO,
        "distancia": probs["distancia_nominal"],
        "posicao_fila": probs["fila_real_estimada"],
        "status": probs["status"],
        "espera_estimada": probs["meses_espera_estatistica"],
        "atualizado_em": datetime.now(FUSO_BR).strftime("%d/%m/%Y %H:%M")
    }
    salvar(final)
    print(f"Sucesso! Alvo: {alvo} | Fila: {probs['fila_real_estimada']}")

if __name__ == "__main__":
    main()