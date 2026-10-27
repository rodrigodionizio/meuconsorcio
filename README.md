# Consórcio Volkswagen Embracon — Acompanhamento da Cota 3177

> **Exclusivo para o regulamento do consórcio Volkswagen administrado pela Embracon.**
> A regra de conversão do sorteio (extração de dígitos, tamanho do grupo, critério de contemplação)
> foi calibrada e validada contra assembleias reais deste contrato específico.
> **Não use em outro consórcio sem recalibrar e validar as regras.**

---

## O que este projeto resolve

O consórcio Volkswagen/Embracon contempla cotas por sorteio em cada assembleia mensal.
O número sorteado é derivado do **1º prêmio da Loteria Federal da Caixa** — um número de
6 dígitos publicado às quartas e sábados. O contrato define uma regra precisa de conversão
desse prêmio em "cota ativa contemplada" e em "cota cancelada excluída".

O problema: não existe uma API ou painel oficial que diga diretamente
_"a cota 3177 foi contemplada hoje?"_. É preciso buscar o resultado da Federal,
aplicar a regra de conversão do regulamento e comparar com a cota acompanhada.

Este projeto faz exatamente isso, de forma automatizada e auditável.

---

## Como o sistema funciona

### 1. Busca do resultado oficial

O bot (`bot_consorcio.py`) consulta a API oficial da Caixa Econômica Federal:

```
https://servicebus2.caixa.gov.br/portaldeloterias/api/federal
```

Se a API principal estiver indisponível (comum em runners de CI), um espelho público é
usado como fallback. O script extrai o **1º prêmio** da lista de premiados — os outros
4 prêmios não são utilizados para determinar a contemplação.

### 2. Regra de conversão (Regulamento Volkswagen/Embracon)

O 1º prêmio da Federal é um número de 6 dígitos (ex.: `095866`).

**Cota ativa contemplada** — extrai os últimos 5 dígitos e pega as posições `[1:5]`:

```
1º prêmio:  0 9 5 8 6 6
posições:   0 1 2 3 4 5  (índices dos 6 dígitos)
últimos 5:    9 5 8 6 6
extrai [1:5]: 5 8 6 6  →  bruto = 5866
alvo = 5866 % 5000 = 866   →  cota ativa contemplada: 866
```

**Cota cancelada excluída** — extrai os últimos 5 dígitos e pega as posições `[0:4]`:

```
últimos 5:    9 5 8 6 6
extrai [0:4]: 9 5 8 6  →  bruto = 9586
cancelada = 9586 % 5000 = 4586   →  cota cancelada: 4586
```

A normalização `% 5000` garante que o resultado sempre caia dentro do grupo
(1 a 5000). Se o resultado for 0, considera-se a última cota (5000).

Esta regra foi confirmada cruzando o resultado da Federal de 17/06/2026
(`053952`) com o extrato de assembleia, que apontou:
- Cota ativa contemplada: **3952** ✓
- Cota cancelada: **395** ✓

### 3. Verificação da cota 3177

Após calcular o alvo, o bot compara com `COTA = 3177`:

- Se `alvo == 3177` → **contemplada** (`sorteada: true`)
- Caso contrário → registra a distância (`|alvo - 3177|`) para referência

### 4. Automação via GitHub Actions

O workflow `.github/workflows/atualizar.yml` executa o bot automaticamente:

- **Quarta-feira** às 23h00 UTC (20h00 Brasília) — sorteio da Federal de quarta
- **Sábado** às 23h00 UTC (20h00 Brasília) — sorteio da Federal de sábado

O bot atualiza `dados.json` e faz commit automático. O painel HTML lê esse arquivo
via GitHub Pages e exibe o resultado sem nenhuma configuração adicional.

---

## Estrutura do projeto

| Arquivo | Função |
|---|---|
| `bot_consorcio.py` | Busca a Federal, aplica a regra de conversão e grava `dados.json` |
| `dados.json` | Resultado mais recente + histórico dos últimos 200 sorteios |
| `index.html` | Painel visual (Tailwind CSS, dark mode, animações, SEO) |
| `.github/workflows/atualizar.yml` | Agendamento automático quarta e sábado |
| `requirements.txt` | Dependências Python (`requests`, `urllib3`) |

---

## dados.json — estrutura

```jsonc
{
  "concurso": 6082,             // número do concurso da Loteria Federal
  "data_sorteio": "11/07/2026", // data do sorteio
  "federal_original": "095866", // 1º prêmio completo (6 dígitos)
  "cota": 3177,                 // cota acompanhada
  "alvo": 866,                  // cota ativa derivada do sorteio
  "alvo_bruto": 5866,           // os 4 dígitos extraídos antes do módulo
  "sorteada": false,            // true somente se alvo == cota
  "distancia": 2311,            // |alvo - cota|
  "prob_exata_por_sorteio_pct": 0.02,
  "assembleias_esperadas_restantes": 177,
  "premissas": { ... },
  "atualizado_em": "11/07/2026 23:01",
  "historico": [ ... ]          // até 200 entradas anteriores
}
```

---

## Uso local

```bash
# Instalar dependências
pip install -r requirements.txt

# Buscar o último resultado e atualizar dados.json
python bot_consorcio.py

# Modo teste offline: calcular sem buscar nem salvar
python bot_consorcio.py 095866
# → imprime JSON com alvo, distância, etc.
```

---

## Colocar no ar (GitHub Pages)

1. Suba todos os arquivos para um repositório público.
2. **Permissões do robô:** `Settings → Actions → General → Workflow permissions`
   → marque **Read and write permissions**.
3. **GitHub Pages:** `Settings → Pages` → branch `main`, pasta `/root`.
   O painel fica em `https://SEU-USUARIO.github.io/REPOSITORIO/`.
4. Para rodar manualmente: `Actions → Atualizar Consórcio → Run workflow`.

---

## Parâmetros configuráveis (`bot_consorcio.py`)

| Constante | Valor atual | Descrição |
|---|---|---|
| `COTA` | `3177` | Número da cota acompanhada |
| `TOTAL_COTAS` | `5000` | Total de cotas do grupo |
| `VACANCIA` | `0.61` | Estimativa de cotas desistentes/inadimplentes |
| `CONTEMPLADOS_POR_ASSEMBLEIA` | `11` | Lances Fixos 25% contemplados por mês |
| `DIGITOS_INICIO` | `1` | Início do slice nos últimos 5 dígitos do 1º prêmio |
| `DIGITOS_FIM` | `5` | Fim do slice (exclusivo) |

> **Calibração:** se o alvo calculado não bater com o regulamento de uma assembleia
> passada, ajuste `DIGITOS_INICIO` e `DIGITOS_FIM`. Use a calculadora no painel ou
> `python bot_consorcio.py <numero>` para testar antes de alterar.

---

## Estimativas de longo prazo

As estimativas exibidas no painel são **modelos transparentes**, não garantias:

- **Chance por sorteio:** `1 / TOTAL_COTAS` (independente de distância ou histórico)
- **Assembleias estimadas restantes:** `cotas_ativas_estimadas / CONTEMPLADOS_POR_ASSEMBLEIA`
  onde `cotas_ativas_estimadas = TOTAL_COTAS × (1 - VACANCIA)`

Cada sorteio da Loteria Federal é matematicamente independente. A distância de um
sorteio não influencia o próximo. Use essas estimativas como referência de horizonte,
não como previsão.

---

## Limitações e avisos

- **Uso exclusivo:** este projeto foi calibrado para o regulamento do consórcio
  Volkswagen administrado pela **Embracon**. Outros planos podem usar regras de
  extração de dígitos diferentes.
- **Sem dados retroativos:** concursos registrados antes da correção do bot (6083–6087)
  aparecem sem `data_sorteio` e `federal_original` porque a API da Caixa havia alterado
  os nomes internos dos campos naquele período.
- **Apenas sorteio:** o sistema não acompanha contemplações por lance. A cota 3177
  pode ser contemplada por lance mesmo que nunca apareça como alvo do sorteio.
