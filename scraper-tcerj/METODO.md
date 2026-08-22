# Método — como este acervo foi construído

Registro do que funcionou, do que falhou e do que descartei depois de testar,
para reaproveitar em outras bases: doutrina, pareceres da PGE/PGM, outros
tribunais.

Não é um manual de boas práticas genéricas. É o relato do que **este** projeto
exigiu, com os números que sustentam cada decisão.

---

## 1. Antes de construir, medir o pressuposto

Toda etapa aqui começou verificando a suposição da qual ela dependia. Sempre
que pulei isso, paguei depois.

**O endpoint.** A descoberta automática elegeu a lista de municípios do estado
como "endpoint de jurisprudência". Se eu tivesse aceitado, teria coletado 92
municípios em vez de acórdãos. Abri o relatório, vi a pontuação de 13, e fui
ao portal com um navegador.

**Os PDFs dos livros.** Antes de desenhar a ingestão de doutrina, medi a
qualidade do texto de cada obra com um vocabulário de referência montado do
próprio acervo do TCE-RJ. Resultado: a obra mais importante do acervo — Marçal
Justen Filho sobre a 14.133 — tem 58% de palavras reconhecíveis contra 71–87%
das demais. É OCR degradado: `"paro lins de controroçoo"`. Transcrever dali
produziria citação falsa atribuída a autor real.

**Os PDFs dos acórdãos.** Mesma medição antes de construir: 79–86%. Texto
nativo. Só então escrevi a ingestão.

> A medição não confirma o plano — ela o muda. Nos livros, mudou de "indexar
> tudo" para "indexar o que é transcritível". Nos acórdãos, autorizou seguir.

## 2. Calibrar contra a fonte real, em volume pequeno, cedo

Coletei **5 documentos** antes de coletar 1.067. Foi nos 5 que apareceu a
colisão de identidade — 20 registros viraram 19 documentos. Em 1.067 teria
passado despercebido como "quase tudo certo".

Cinco defeitos só apareceram contra dados reais, e nenhum deles seria pego por
teste com dado sintético:

| Defeito | Efeito |
|---|---|
| Carimbo ISO com `T` não casava o regex | `data_sessao` vazia em **100%** dos registros |
| Quebra de linha era a sequência literal `\n` | Aparecia crua em toda ementa |
| `tipo+número+ano` não é chave única | Segunda tese do mesmo acórdão sobrescrevia a primeira, em silêncio |
| `re.IGNORECASE` anulava a exigência de maiúscula | Relator capturado de prosa: `"antes de iniciada a"` |
| `numeroAcordao = 0` na origem | Virava "Acórdão 0/2000" |

O terceiro é o caro: é erro de modelagem, não de código.

## 3. Perguntar o que é um registro, antes de guardar

O erro mais caro do projeto foi assumir que espécie + número + ano identifica
um acórdão. Não identifica: **19 acórdãos rendem duas ou três ementas
selecionadas cada**, com teses distintas sobre macro-temas distintos.

As ementas não são duplicatas — são atos de curadoria diferentes sobre o mesmo
documento. O que era um só era o inteiro teor.

Consertar depois custou: 22 downloads redundantes, 618 páginas duplicadas, e
uma remodelagem com migração.

> Antes de criar a tabela, responder: *o que é uma linha aqui?* E depois:
> *duas linhas com os mesmos campos são o mesmo objeto?*

## 4. Erro de processamento se conserta sem rebaixar a fonte

Quando descobri que a remoção de moldura falhava — a detecção comparava texto
bruto e a remoção comparava texto normalizado, então `"Gabinete  da
Conselheira"` nunca casava com `"Gabinete da Conselheira"` —, os 1.064 PDFs já
estavam processados.

Refazer a coleta seria bater mil vezes no servidor do Tribunal por erro meu. O
reparo foi transformação determinística sobre o material já guardado.

> Separar, desde o início, **coletar** de **processar**. O que veio da rede
> fica; o que se derivou dele se refaz de graça.

## 5. Hipótese testada e reprovada também é resultado

Propus **relaxamento progressivo**: falhando a busca conjunta, remover o termo
mais comum e repetir, mantendo os mais raros. Parecia óbvio.

Testei. Falhou feio: `"exigível"` sozinho devolve *"Passivo circulante +
Exigível a Longo Prazo"* — termo contábil. Os termos raros são raros justamente
por serem polissêmicos.

Descartei, e o registro do descarte vale tanto quanto uma implementação: impede
que alguém tenha a mesma ideia daqui a seis meses.

Da mesma forma, remover verbos fracos da consulta — hipótese razoável —
corrigiu **1 de 6** casos. Foi implementado porque não piora nada, mas não era
a solução que parecia ser.

## 6. Medir onde está o custo antes de otimizar

O banco tinha 131,9 MB e eu ia otimizar por instinto. Medi por diferença
(copiar, remover uma parte, `VACUUM`, comparar), porque `dbstat` não estava
compilado:

```
índice FTS do inteiro teor   70,9 MB   54%
texto das páginas            51,5 MB   39%
índice FTS das ementas        2,8 MB    2%
resto                         6,8 MB    5%
```

**O índice era maior que o dado** — o FTS5 guardava uma segunda cópia do texto.
Trocar para conteúdo externo: 131,9 → 81,3 MB, em 6 segundos de reconstrução.

Sem a medição, eu teria otimizado o texto, que era a metade menor.

## 7. O especialista encontra o que a métrica não vê

Esta é a lição central, e não é técnica.

Gerei 42 páginas de material bruto — trechos com página anterior e seguinte —
para o advogado avaliar. Eu esperava medir "±1 página melhora a busca?".

A leitura dele encontrou outra coisa: no Acórdão 6.930/2025, o melhor trecho
da p. 15 eram **razões de defesa do jurisdicionado**, e a análise do relator só
começava na p. 16. Um sistema que apanha o melhor parágrafo faria o Tribunal
"decidir" exatamente o que a parte alegava.

Isso é **inversão, não imprecisão**. E nenhuma métrica minha apontaria: o
resultado era lexicalmente perfeito.

O documento reúne, no mesmo texto:

```
decisão colegiada · relatório · alegações da defesa · instrução técnica
parecer do MPC · decisões anteriores · precedentes transcritos
fundamentação do relator · dispositivo
```

Para a busca, caracteres iguais. Juridicamente, valores opostos.

> Entregue material bruto ao especialista, sem interpretar. Ele vê o que você
> não sabe procurar.

## 8. Estado é dado, não linha de log

Pendências viraram registro com situação (`ok`, `http_404`,
`sem_numero_acordao`, `erro_temporario`), data da tentativa e data da última
coleta bem-sucedida — que são informações diferentes e não podem se apagar.

Assim a rotina incremental retesta sozinha o que faz sentido retestar, e se o
Tribunal publicar o documento faltante, ele entra sem intervenção.

E a contagem fica auditável:

```
1.067 ementas de acórdão
  → 1.065 com número
    → 1.043 acórdãos distintos
      → 1.042 coletados
        → 1 com HTTP 404
```

Sem isso, alguém veria 1.042 contra 1.067 daqui a seis meses e suporia perda
de dados.

## 9. Publicação: cadeia fechada

```
versão fixa → sha256 declarado → conferência no build → falha fechada
```

O banco saiu do Git quando passou de 50 MB: é artefato de dados, não
código-fonte. Vai comprimido como asset de release — hoje 2,8 GB → 641 MB — e a
imagem o baixa na construção conferindo o hash. Se o arquivo publicado divergir, o
build falha em vez de subir um acervo diferente do declarado.

## 10. Teste de aceitação é comportamental, não automatizado

174 testes automatizados não medem se o modelo pesquisa como um advogado
cuidadoso. Para isso, cinco perguntas reais, em chat limpo, sem palavra-chave e
sem intervenção — *o erro é o dado*.

E um critério objetivo de que o cliente carregou a versão nova, antes de rodar
qualquer coisa. Na primeira tentativa os dois clientes estavam com a v1 em
cache e o teste inteiro foi inválido.

O ganho ficou demonstrado por comparação direta: a mesma pergunta que os dois
responderam **"não localizado"** na v1 foi respondida com precedente, página e
link 40 minutos depois. Única variável: o inteiro teor.


## 11. Ranqueador ajustado à mão contra dez documentos não se sustenta

Para escolher quais Notas Técnicas anexar à busca de jurisprudência, tentei
pontuar pertinência: fração de termos casados, depois limiar de dois terços,
depois exigência do termo mais raro. Cada ajuste consertava dois casos do meu
próprio conjunto de teste e quebrava outros dois.

- exigir TODOS os termos perdia a NT 5/2022, porque a pergunta diz "escolares"
  e o documento diz "merenda escolar";
- dois terços admitiam notas de compras para "visita técnica habilitação
  licitação", porque "técnica" e "licitação" estão em quase todas;
- o termo raro consertava essa e derrubava outras duas.

O defeito não era o limiar. Era estar **calibrando contra casos que eu mesmo
escolhera** — o que produz a sensação de progresso sem produzir generalização.
Hesitei tempo demais antes de reconhecer isso.

A saída foi o padrão já validado para súmula: busca literal, e devolução do
**conjunto** quando ela não casa. Afirmar ausência passa a depender de leitura,
não do silêncio do índice. Vale sempre que o universo couber numa leitura — 28
súmulas, 10 notas — e deixa de valer nos 25.561 acórdãos, onde ranquear é a
única opção e por isso o acervo declara os limites em vez de escondê-los.

---

## Erros que cometi, e o que cada um ensina

**Testei com o interpretador errado.** Empacotei a extensão e verifiquei com o
Python do sistema (3.12). O Claude Desktop usa o primeiro do PATH dele (3.13).
Três defeitos empilhados só apareceram na máquina do usuário.
→ *Reproduzir o ambiente do consumidor, não o meu.*

**Presumi um campo de configuração.** Escrevi `dockerBuildArgs` no
`render.yaml` sem verificar se existe. O deploy não subiu e a causa era
invisível de fora.
→ *Não inventar interface de terceiro. Se não dá para verificar, não depender.*

**Deixei uma declaração virar mentira.** O `cobertura_do_acervo` continuou
dizendo *"não há inteiro teor"* depois que 16.343 páginas entraram. É o texto
que o modelo lê como limite autoritativo — ele diria ao advogado que a base não
tem votos, tendo 35 milhões de caracteres de voto.
→ *Ao acrescentar capacidade, revisar o que o sistema declara sobre si mesmo.*

**Escrevi um teste errado e culpei o código.** O teste de número zero afirmava
`ano is None`, mas o ano vinha legitimamente da data do voto.
→ *Expectativa errada no teste parece defeito no código.*

---

## O que eu repetiria em outra base

1. Medir o pressuposto antes de escrever a primeira linha.
2. Calibrar com 5 registros antes de coletar 5 mil.
3. Definir o que é um registro antes de criar a tabela.
4. Separar coletar de processar.
5. Registrar hipóteses reprovadas.
6. Medir antes de otimizar.
7. Entregar material bruto ao especialista e ouvir o que ele vê.
8. Estado como dado.
9. Cadeia de integridade na publicação.
10. Teste de aceitação comportamental, com critério objetivo de versão.

O item 7 é o que separou uma boa base de dados de uma ferramenta de pesquisa
jurídica. Os outros nove são engenharia; esse é o que exigiu alguém que
entende do assunto olhando o resultado com desconfiança.
