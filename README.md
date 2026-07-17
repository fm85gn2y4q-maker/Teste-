# 🛒 Feira Esperta · Rio de Janeiro

App mobile (Expo / React Native) que compara preços de supermercados **por bairro do Rio de
Janeiro** e monta um **plano inteligente de compra**: você monta (ou cola) sua lista de compras,
escolhe seu bairro, e ele calcula onde comprar com o **melhor custo-benefício global** — somando
preço dos itens, promoções e o custo de deslocamento até cada mercado, incluindo os bairros
vizinhos.

Exemplo: um morador da **Barra da Tijuca** vê os mercados da Barra e também de Recreio,
Jacarepaguá e São Conrado. O app responde se vale a pena atravessar até o Atacadão da Freguesia
ou ficar no Assaí da Barra — já descontando o custo de ir e voltar.

## Funcionalidades

- **Lista de compras** com busca no catálogo (45+ produtos em 8 categorias) e controle de quantidade.
- **Colar lista pronta**: interpreta texto livre, um item por linha — aceita `2 arroz`, `leite x3`,
  `café` — com correspondência tolerante a acentos e apelidos (ex.: "pasta de dente" → creme dental).
- **10 bairros do Rio** com malha de vizinhança e distâncias reais aproximadas: Barra, Recreio,
  Jacarepaguá, São Conrado, Ipanema/Leblon, Copacabana, Botafogo, Tijuca, Centro e Méier.
- **27 mercados inspirados nas redes cariocas** — Guanabara, Mundial, Prezunic, Zona Sul, Assaí,
  Atacadão, Extra, Pão de Açúcar, SuperPrix e Hortifruti Natural da Terra — cada bandeira com seu
  perfil típico de preço por categoria (atacarejo barato em básicos, Hortifruti imbatível em
  hortifrúti, Zona Sul forte em padaria...) e promoções ativas.
- **Ranking por custo-benefício**: para cada mercado próximo, o total considera
  `compras + deslocamento (ida e volta × R$/km)`, priorizando quem cobre toda a lista.
- **Plano inteligente dividido**: testa todas as combinações de mercados próximos (até o limite
  configurado), atribui cada item ao mais barato e soma o deslocamento de cada parada — só
  recomenda dividir a compra (ou ir a um bairro vizinho) quando a economia real compensa.
- **Configurável**: número máximo de mercados por plano (1–4) e custo por km (combustível/app de
  transporte/tempo).

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
│   ├── bairros.ts     # Bairros do Rio, custo de vida e malha de vizinhança (km)
│   └── markets.ts     # Mercados por bairro (perfil da rede, promoções) + marketsNear()
├── engine/
│   ├── pricing.ts     # Precificação: bairro × rede × categoria + promoções
│   ├── planner.ts     # Ranking por custo-benefício e otimização do plano dividido
│   └── parseList.ts   # Parser de lista colada (quantidades, acentos, apelidos)
├── store/useStore.ts  # Estado global (Zustand): bairro, lista, preferências
├── screens/           # Lista (Home), Resultados, Configurações
└── types/             # Tipos de domínio e navegação
```

### Como o otimizador funciona

1. `marketsNear(bairro)` reúne os mercados do bairro e dos vizinhos, com distância e custo de
   deslocamento (ida e volta × R$/km configurável).
2. Para cada mercado, gera um orçamento da lista aplicando preço de tabela
   (base × custo de vida do bairro × perfil da rede × fator da categoria) e promoções.
3. Ranqueia por cobertura da lista e menor **custo efetivo (compras + deslocamento)** →
   melhor mercado único.
4. Enumera todos os subconjuntos de mercados próximos com até `maxStops` elementos; em cada um,
   atribui cada item ao mercado mais barato que o vende e soma o deslocamento de cada parada.
   Vence o subconjunto com maior cobertura e menor custo efetivo.

Com ~10 mercados próximos e limite de 4 paradas a busca exaustiva é barata e garante o ótimo
global para o modelo.

## Dados

Redes e bairros são reais; **preços, endereços e promoções são simulados deterministicamente**
para demonstrar o produto. Próximos passos naturais: preços reais (APIs das redes, notas fiscais
via NFC-e, crowdsourcing), geolocalização do usuário com rotas reais (em vez de ida e volta por
mercado) e histórico de preços por produto.
