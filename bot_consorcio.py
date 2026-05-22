# -*- coding: utf-8 -*-
"""
Motor de acompanhamento de consórcio por sorteio (Loteria Federal da Caixa).

O QUE ESTE SCRIPT FAZ DE FORMA CONFIÁVEL (determinístico):
  - Busca o resultado oficial da Loteria Federal na API da Caixa.
  - Extrai o "alvo" do consórcio a partir do 1º prêmio, segundo a regra
    configurável abaixo (padrão: 2º ao 5º algarismo de um número de 5 dígitos).
  - Verifica se a SUA cota foi o alvo daquele sorteio (sim / não).
  - Guarda um histórico em dados.json para você acumular dados reais ao longo
    do tempo.

SOBRE AS "CHANCES" (leia com atenção):
  Cada sorteio da Federal é independente. A distância entre o alvo de uma
  semana e a sua cota NÃO prevê o resultado da semana seguinte. Por isso os
  campos de "cenário" abaixo são apenas estimativas transparentes, baseadas
  nas SUAS premissas (vacância etc.). Use-os como referência, não como
  garantia — e não tome decisões de lance/financeiras só com base neles.

Modo de uso:
  python bot_consorcio.py            -> busca a Federal e atualiza dados.json
  python bot_consorcio.py 83358      -> modo teste/offline: só calcula e imprime
"""

import json
import os
import sys
from datetime import datetime

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---------------------------------------------------------------------------
# CONFIGURAÇÃO — ajuste aqui
# ---------------------------------------------------------------------------
COTA = 3177             # número da sua cota
TOTAL_COTAS = 5000      # tamanho do grupo
VACANCIA = 0.61         # premissa sua: fração de cotas desistentes/inadimplentes
CONTEMPLADOS_POR_ASSEMBLEIA = 11   # Quantidade de Lances Fixos 25%
#CONTEMPLADOS_POR_ASSEMBLEIA = 2   # quantos são contemplados por mês (sorteio + lance) — ajuste

# Regra de extração do alvo a partir do 1º prêmio da Federal (5 dígitos).
# (1, 5) = "do 2º ao 5º algarismo" -> índices Python [1:5].
# Ex.: prêmio 83358 -> dígitos 2..5 = "3358" -> alvo 3358.
# IMPORTANTE: confira contra assembleias passadas (use a calculadora do site
# ou rode "python bot_consorcio.py <numero>") e ajuste se o seu contrato usar
# outra regra.
DIGITOS_INICIO = 1
DIGITOS_FIM = 5

API_FEDERAL = "https://servicebus2.caixa.gov.br/portaldeloterias/api/federal"
HISTORICO_MAX = 200     # quantos sorteios manter no histórico
ARQUIVO_SAIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dados.json")


def extrair_alvo(numero_federal):
    """Aplica a regra do consórcio ao 1º prêmio e devolve (alvo, bruto).

    alvo  -> número entre 1 e TOTAL_COTAS (cota equivalente sorteada)
    bruto -> os 4 dígitos extraídos antes da normalização do grupo
    """
    s = "".join(ch for ch in str(numero_federal) if ch.isdigit())
    s = s.zfill(5)[-5:]                      # garante exatamente 5 dígitos
    bruto = int(s[DIGITOS_INICIO:DIGITOS_FIM])
    alvo = bruto % TOTAL_COTAS               # normaliza para o tamanho do grupo
    if alvo == 0:                            # 0000/5000 -> última cota
        alvo = TOTAL_COTAS
    return alvo, bruto


def analisar(numero_federal, concurso=None, data_sorteio=None):
    """Calcula o resultado determinístico + estimativas transparentes."""
    alvo, bruto = extrair_alvo(numero_federal)
    distancia = abs(alvo - COTA)
    sorteada = (alvo == COTA)

    # --- Estatística honesta (modelo de sorteios independentes) ---
    cotas_ativas = max(1, round(TOTAL_COTAS * (1 - VACANCIA)))
    # Chance de a SUA cota ser exatamente o alvo num único sorteio:
    prob_exata_pct = round(100 / TOTAL_COTAS, 4)
    # Se o grupo contempla "a cota mais próxima ainda não contemplada", o que
    # importa no longo prazo é o tempo esperado até a contemplação:
    assembleias_esperadas = round(cotas_ativas / max(1, CONTEMPLADOS_POR_ASSEMBLEIA))

    return {
        "concurso": concurso,
        "data_sorteio": data_sorteio,
        "federal_original": str(numero_federal),
        "cota": COTA,
        "alvo": alvo,
        "alvo_bruto": bruto,
        "sorteada": sorteada,
        "distancia": distancia,
        "prob_exata_por_sorteio_pct": prob_exata_pct,
        "assembleias_esperadas_restantes": assembleias_esperadas,
        "premissas": {
            "total_cotas": TOTAL_COTAS,
            "vacancia": VACANCIA,
            "contemplados_por_assembleia": CONTEMPLADOS_POR_ASSEMBLEIA,
            "cotas_ativas_estimadas": cotas_ativas,
            "regra_digitos": [DIGITOS_INICIO, DIGITOS_FIM],
        },
        "atualizado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
    }


def buscar_federal():
    """Lê o resultado mais recente da Federal e devolve (1o_premio, concurso, data)."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        ),
        "Accept": "application/json",
    }
    r = requests.get(API_FEDERAL, headers=headers, verify=False, timeout=30)
    r.raise_for_status()
    dados = r.json()

    premios = dados.get("listaDezenas") or dados.get("dezenasSorteadasOrdemSorteio")
    if not premios:
        raise ValueError("Resposta da API sem lista de prêmios. Chaves: %s"
                         % list(dados.keys()))
    primeiro = premios[0]
    return primeiro, dados.get("numero"), dados.get("dataApuracao")


def carregar_existente():
    if os.path.exists(ARQUIVO_SAIDA):
        try:
            with open(ARQUIVO_SAIDA, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, ValueError):
            return {}
    return {}


def salvar(resultado):
    base = carregar_existente()
    historico = base.get("historico", [])

    # Evita duplicar o mesmo concurso no topo do histórico
    if not historico or historico[0].get("concurso") != resultado.get("concurso"):
        historico.insert(0, {
            "concurso": resultado["concurso"],
            "data_sorteio": resultado["data_sorteio"],
            "federal_original": resultado["federal_original"],
            "alvo": resultado["alvo"],
            "distancia": resultado["distancia"],
            "sorteada": resultado["sorteada"],
        })
    historico = historico[:HISTORICO_MAX]

    saida = dict(resultado)
    saida["historico"] = historico
    with open(ARQUIVO_SAIDA, "w", encoding="utf-8") as f:
        json.dump(saida, f, ensure_ascii=False, indent=2)
    return saida


def main():
    try:
        primeiro, concurso, data_sorteio = buscar_federal()
        resultado = analisar(primeiro, concurso, data_sorteio)
        salvar(resultado)
        print("OK - concurso %s | 1o premio %s | alvo %s | sorteada=%s"
              % (concurso, primeiro, resultado["alvo"], resultado["sorteada"]))
    except Exception as e:  # noqa: BLE001
        print("ERRO ao atualizar:", e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Modo teste/offline: calcula sem buscar nem salvar.
        print(json.dumps(analisar(sys.argv[1]), ensure_ascii=False, indent=2))
    else:
        main()
