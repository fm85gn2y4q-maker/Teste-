# Teste de aceitação — Ementário TCE-RJ v2.0.0

O código tem testes automatizados. Estes aqui são de outra natureza: medem se
o modelo, **sozinho e sem orientação**, pesquisa como um advogado cuidadoso.
Nenhum script cobre isso.

Também servem de **regressão qualitativa**: se um dia uma alteração nas
instruções piorar o comportamento, estas cinco perguntas denunciam.

## Como rodar

**Chat limpo, uma pergunta por vez.** A conversa em que o Ementário foi
construído conhece os acórdãos de antemão e entregaria a resposta ao modelo,
falseando o teste.

**Pergunta natural, como se faria a um colega.** Sem palavra-chave, sem dizer
onde procurar, sem mencionar acórdão, sem sugerir reformulação. Se o modelo
precisar ser guiado, ele falhou — a instrução existe para que não precise.

**Não intervir no meio.** Deixe ir até o fim, mesmo que pareça estar
errando. O erro é o dado.

## O que se avalia

Encontrar o acórdão certo é o menos importante. O que interessa são cinco
comportamentos:

    descobriu → reformulou quando necessário → verificou proveniência
    → expandiu o contexto → qualificou corretamente a força do precedente

---

## 1. Compensação de acréscimos e supressões

> O TCE-RJ admite compensar acréscimos e supressões para calcular o limite de
> alteração contratual?

**Testa:** a resposta não está em nenhuma ementa. Só existe no inteiro teor.

**Esperado:** chegar ao Acórdão 58.739/2023 e perceber que a formulação "sem
compensação entre eles" foi efetivamente **acolhida** no voto e certificada
pelo colegiado — não apenas reproduzida no relatório.

## 2. Designação formal do fiscal — o teste principal

> A falta de designação formal como fiscal impede que o servidor seja
> responsabilizado pela fiscalização do contrato?

**Testa:** proveniência. Três trechos quase idênticos, com autoridades
diferentes: um precedente do TCU apenas transcrito, uma defesa **acolhida** e
uma defesa **rejeitada**. Lexicalmente equivalentes; juridicamente, não.

Quatro níveis:

| | |
|---|---|
| **Falha grave** | Afirma "o TCE-RJ entende que a ausência de designação formal afasta a responsabilidade", apoiado só na defesa do 54.691/2025. |
| **Falha moderada** | Acha os acórdãos certos, mas não diz quem formulou cada proposição nem qual foi o desfecho. |
| **Passou** | Lê adiante, identifica que numa a defesa foi acolhida e noutra rejeitada, separa o precedente do TCU transcrito, e condiciona a resposta aos fatos. |
| **Passou muito bem** | Além disso, percebe que a jurisprudência não autoriza a regra mecânica "designação formal = responsabilidade / ausência = irresponsabilidade", e reconstrói quais elementos concretos pesaram em cada julgamento. |

## 3. Projeto básico deficiente

> Deficiências no projeto básico podem justificar alterações ou aditivos
> durante a execução da obra?

**Testa:** busca em várias formulações. A consulta direta produz ruído — termos
genéricos espalham a relevância. O que importa é se o modelo **percebe sozinho**
que o resultado é lateral e tenta outro vocabulário.

## 4. Subcontratação e notória especialização

> É proibida a subcontratação quando a contratação ocorreu por inexigibilidade
> em razão de notória especialização?

**Testa:** leitura além do trecho. A vedação está numa página; o "desde que"
que a qualifica está na seguinte. Citar só a primeira produz afirmação
categórica que o próprio documento desmente.

## 5. Fiscal e medição irregular

> Em que situações o fiscal de um contrato pode responder pessoalmente por
> medição irregular?

**Testa:** tudo junto — inteiro teor, distinção entre instrução e voto, razões
de defesa, expansão da leitura além da primeira janela, e conclusão só depois
de identificar a posição efetivamente adotada.

---

# Registro

Copie o bloco abaixo para cada pergunta.

```
Pergunta nº:
Data:
Cliente (Claude/ChatGPT):
Chat limpo: sim/não

Ferramentas usadas:
Consultas executadas:
Variantes executadas:
Acórdãos consultados:
Páginas lidas:

Reformulou quando necessário?           sim/não
Verificou proveniência?                 sim/não
Expandiu contexto?                      sim/não
Distinguiu alegação de decisão?         sim/não
Conclusão juridicamente sustentada?     sim/não

Falhas observadas:

Veredicto:
```

---

# Resultados

## Primeira rodada — 26/07/2026

**Tentativa inválida, registrada porque a lição importa.** Os dois clientes
tinham a v1 em cache: 6 ferramentas, sem `pesquisar_inteiro_teor`, e a
cobertura ainda declarando "não há inteiro teor". Ambos responderam "não
localizado" à pergunta 1. Foi preciso **remover e recriar o conector** — desligar
e religar não bastou.

## Segunda rodada — 26/07/2026, conectores recriados

Critério de versão conferido antes: 1.042 documentos com inteiro teor.

| | ChatGPT | Claude |
|---|---|---|
| 1. compensação | Passou muito bem | Passou |
| 2. designação formal | **Passou muito bem** | Passou |
| 3. projeto básico | Passou muito bem | Passou |
| 4. subcontratação | Passou | **Falha moderada** |
| 5. fiscal e medição | Passou muito bem | Passou |

**Nenhuma falha grave.** Nenhum dos dois atribuiu razão de defesa ao Tribunal.
Ambos marcaram inferência própria como inferência, e declararam o limite da
curadoria sem serem lembrados. Todas as citações conferidas contra o acervo —
nenhuma inventada; uma data errada no Claude (43632/2025).

**A prova do ganho:** a pergunta 1 foi "não localizado" na v1 e, 40 minutos
depois, veio com precedente, página e link — Acórdão 58739/2023, *"sem
compensação entre eles"*. Única variável: o inteiro teor.

### Duas pendências reais

**A leitura além da página ainda não é reflexo.** Na pergunta 4, o Claude parou
na página que casou e respondeu "Sim, é vedada", categórico. A ressalva —
*"desde que evidenciada a supervisão e o controle do titular da notória
especialização"* — está na página seguinte. O ChatGPT leu adiante e distinguiu
núcleo de tarefa acessória. A instrução existe; não bastou.

**Os casos-armadilha não foram alcançados.** Os Acórdãos 54691/2025 (defesa
acolhida) e 6930/2025 (razões de defesa) não apareceram no ranqueamento —
ambos estão no acervo, com 37 e 28 páginas. Os dois modelos acertaram sem
enfrentar os casos que os testariam. O mecanismo de proveniência ainda não foi
posto sob pressão.
