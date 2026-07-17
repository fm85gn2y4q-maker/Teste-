# 🛒 Feira Esperta

App mobile (Expo / React Native) que compara preços de supermercados **por região** e monta um
**plano inteligente de compra**: você monta (ou cola) sua lista de compras e ele calcula onde
comprar para obter o maior desconto global — seja em um único mercado, seja dividindo a compra
entre até 4 mercados quando a economia compensa o deslocamento.

## Funcionalidades

- **Lista de compras** com busca no catálogo (45+ produtos em 8 categorias) e controle de quantidade.
- **Colar lista pronta**: interpreta texto livre, um item por linha — aceita `2 arroz`, `leite x3`,
  `café` — com correspondência tolerante a acentos e apelidos (ex.: "pasta de dente" → creme dental).
- **Comparação por região**: 5 regiões, cada uma com seus próprios mercados (16 no total), perfis de
  preço por categoria e promoções ativas.
- **Melhor mercado único**: ranking completo dos mercados da região, priorizando quem cobre toda a
  lista, com economia vs. o mercado mais caro e total ganho em promoções.
- **Plano inteligente dividido**: testa todas as combinações de mercados (até o limite configurado),
  atribui cada item ao mercado mais barato da combinação e desconta um custo de deslocamento por
  parada extra — só recomenda dividir a compra quando a economia real supera o custo de ir a mais
  um mercado.
- **Configurável**: número máximo de mercados por plano (1–4) e custo de deslocamento por parada.

## Como rodar

```bash
npm install
npm start          # Expo Dev Server — leia o QR code com o app Expo Go
npm run android    # ou direto no emulador Android
npm run ios        # ou no simulador iOS
npm run web        # ou no navegador
```

## Arquitetura

```
src/
├── data/
│   ├── catalog.ts     # Catálogo de produtos (preço base, categoria, apelidos)
│   └── markets.ts     # Regiões e mercados (fatores de preço, promoções, indisponibilidades)
├── engine/
│   ├── pricing.ts     # Precificação: fatores região × mercado × categoria + promoções
│   ├── planner.ts     # Comparação, ranking e otimização do plano dividido
│   └── parseList.ts   # Parser de lista colada (quantidades, acentos, apelidos)
├── store/useStore.ts  # Estado global (Zustand): região, lista, preferências
├── screens/           # Lista (Home), Resultados, Configurações
└── types/             # Tipos de domínio e navegação
```

### Como o otimizador funciona

1. Para cada mercado da região, gera um orçamento da lista aplicando preço de tabela
   (base × fator da região × perfil do mercado × fator da categoria) e promoções.
2. Ranqueia por cobertura da lista e menor total → **melhor mercado único**.
3. Enumera todos os subconjuntos de mercados com até `maxStops` elementos; em cada um, atribui
   cada item ao mercado mais barato que o vende e soma
   `total dos itens + custo de deslocamento × (paradas − 1)`.
4. Vence o subconjunto com maior cobertura e menor custo efetivo. Se a economia não paga o
   deslocamento, o plano recomenda um único mercado.

Com ~4 mercados por região e limite de 4 paradas, a busca exaustiva é barata (≤ 15 combinações)
e garante o ótimo global.

## Dados

Os preços são **simulados deterministicamente** (sem aleatoriedade em runtime) para demonstrar o
produto. Próximos passos naturais: integrar fontes reais de preço (APIs de mercados, notas fiscais
via NFC-e, crowdsourcing), geolocalização para distâncias reais de deslocamento e histórico de
preços por produto.
