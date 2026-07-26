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

_A preencher._
