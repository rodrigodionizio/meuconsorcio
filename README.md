# Consórcio Tracker

Acompanha automaticamente a sua cota de consórcio (nº **3177**, grupo de **5000**)
usando o resultado oficial da **Loteria Federal** da Caixa.

- `bot_consorcio.py` — busca a Federal, calcula o alvo do consórcio e grava `dados.json`.
- `index.html` — painel que lê o `dados.json` (publicado via GitHub Pages).
- `.github/workflows/atualizar.yml` — roda o robô sozinho aos sábados.
- `dados.json` — arquivo de dados (começa com um exemplo, é sobrescrito no 1º sorteio).

## Como a regra funciona

O alvo é formado pelo **2º ao 5º algarismo do 1º prêmio** da Federal (número de 5 dígitos)
e depois normalizado para o tamanho do grupo.
Exemplo: prêmio `83358` → `3358` → alvo **3358**.

> Confira contra assembleias passadas usando a calculadora no rodapé do painel
> (ou `python bot_consorcio.py 83358`). Se o alvo não bater com o que o Adinan
> informou, ajuste `DIGITOS_INICIO`/`DIGITOS_FIM` em `bot_consorcio.py`.

## Rodar localmente (teste)

```bash
pip install -r requirements.txt
python bot_consorcio.py            # busca a Federal e atualiza o dados.json
python bot_consorcio.py 83358      # modo teste: só calcula e imprime
```

## Colocar no ar (GitHub)

1. Crie um repositório (ex.: `meu-consorcio`) e suba todos estes arquivos.
2. **Permissão do robô:** em `Settings → Actions → General → Workflow permissions`,
   marque **Read and write permissions**.
3. **Agendamento:** o workflow já roda aos sábados 20h (Brasília). Para testar agora,
   vá em `Actions → Atualizar Consórcio → Run workflow`.
4. **Publicar o painel:** em `Settings → Pages`, selecione o branch `main` (pasta `/root`).
   O painel ficará em `https://SEU-USUARIO.github.io/meu-consorcio/`.

## Importante sobre as "chances"

O veredito **contemplada / não contemplada** é exato — vem do resultado oficial.
As **estimativas** (chance por sorteio, assembleias restantes) são aproximações
baseadas em premissas editáveis no topo do `bot_consorcio.py`. Cada sorteio da
Federal é independente: a distância de uma semana **não** prevê o sorteio seguinte.
Use as estimativas como referência, não como garantia.

> A `assembleias_esperadas_restantes` depende de `CONTEMPLADOS_POR_ASSEMBLEIA`.
> Ajuste esse número para o ritmo real do seu grupo (ex.: se o plano tem 80 meses
> para 5000 cotas, são ~60 contemplações por assembleia, não 2).
