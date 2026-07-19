# Prospecção de clientes — Restituição de ITBI (Tema 1113/STJ)

Kit de prospecção para casos de ITBI pago a maior: situações em que o município calculou o
imposto sobre "valor venal de referência" (ou outra base arbitrada unilateralmente) superior
ao preço de compra declarado, em desacordo com a tese fixada pelo STJ no **Tema Repetitivo
1.113** (REsp 1.937.821/SP): a base de cálculo do ITBI é o valor da transação declarado pelo
contribuinte, que goza de presunção de veracidade e só pode ser afastado pelo fisco mediante
processo administrativo próprio (art. 148 do CTN).

## Conteúdo

### `planilha-triagem-itbi.xlsx`
Planilha de triagem da carteira de leads.

- **Aba Config** — parâmetros do escritório (alíquota padrão do município, valor mínimo de
  indébito para aceitar o caso, percentual de honorários de êxito) e resumo automático da
  carteira (leads cadastrados, casos viáveis, indébito e honorários potenciais).
- **Aba Triagem** — preencha as colunas A–H e P (fonte azul); as colunas I–O calculam
  automaticamente: ITBI devido sobre o valor declarado, indébito estimado, data em que o
  direito prescreve (pagamento + 5 anos, art. 168, I, CTN), dias restantes, situação
  (OK / URGENTE / PRESCRITO), viabilidade (SIM / AVALIAR / NÃO) e honorários estimados.
- A linha 4 é um exemplo — substitua pelos dados reais.

### `landing-page/index.html`
Landing page autocontida (sem dependências externas) com calculadora de restituição:
o visitante informa preço de compra, base de cálculo da guia, alíquota e data do pagamento,
e recebe a estimativa do indébito com checagem do prazo de 5 anos e botão de contato via
WhatsApp com mensagem pré-preenchida.

**Antes de publicar, edite:**
1. O bloco `CONFIG` no início do arquivo (WhatsApp com DDI+DDD, e-mail, alíquota padrão).
2. Os marcadores `[NOME DO ESCRITÓRIO]` e `[OAB/UF n.º 000.000]` no cabeçalho e no rodapé.

Hospedagem: qualquer serviço estático (GitHub Pages, Netlify, Vercel) — é um único arquivo HTML.

## Compliance (OAB — Provimento 205/2021)

- A página é marketing de conteúdo com calculadora informativa: o cliente vem até o
  escritório. **Não** utilize listas de compradores identificados (cartórios, bases públicas
  de ITBI) para abordagem direta — isso configura captação vedada de clientela.
- Os disclaimers do rodapé (caráter informativo, ausência de promessa de resultado) fazem
  parte do compliance — não os remova.
- Use dados públicos (ex.: base aberta de ITBI de municípios que a publicam) apenas para
  inteligência de mercado e segmentação de mídia por região.
