# Acervo consultivo da AGU — servidor MCP

As manifestações de uniformização da **Consultoria Nacional da União de
Uniformização (CONUNI)** e de suas Câmaras Nacionais Temáticas, as
**Orientações Normativas** da AGU e as **Súmulas** da AGU.

Um servidor por acervo, como o Ementário do TCE-RJ, a Legislação de Mesquita e
os pareceres da PGE-RJ. Não mistura instituições: parecer da AGU, da PGE-RJ e de
outra Procuradoria têm graus de autoridade diferentes, e numa tabela só essa
diferença vira metadado ignorável.

## O acervo

| | |
|---|---|
| Documentos | 3.019 |
| Pareceres vinculantes do Advogado-Geral (art. 40, § 1º) | 215 |
| CONUNI e Câmaras Nacionais | 1.724 |
| Manifestações Jurídicas Referenciais (55 Consultorias) | 884 |
| Orientações Normativas (103 da AGU + 7 da extinta CNU) | 110 |
| Súmulas da AGU | 86 |
| Com texto pesquisável | 1.852 |
| — destes, recuperados por OCR | 369 |
| Sem arquivo público | 1.115 |
| Páginas indexadas | 7.893 |
| Período | 1993 a 2026 |
| Citações mapeadas | 16.722 |

Banco: `~/Documents/AGU_Acervo_Consultivo/agu_consultivo.db`, fora do
repositório — é artefato de dados. O caminho pode ser passado com `--banco` ou
pela variável `AGU_BANCO`.

## Como rodar

```bash
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m agu            # stdio, para o Claude
.\.venv\Scripts\python.exe -m agu --http     # HTTP em 127.0.0.1:8767
```

O SDK precisa ser da série 1.x: o `mcp` 2.0 removeu `mcp.server.fastmcp`.

### Claude Desktop

```json
{
  "mcpServers": {
    "consultivo-agu": {
      "command": "C:\\Users\\Matheus Menegatti\\projetos\\Teste-\\pareceres-agu\\.venv\\Scripts\\python.exe",
      "args": ["-m", "agu"],
      "env": {
        "PYTHONPATH": "C:\\Users\\Matheus Menegatti\\projetos\\Teste-\\pareceres-agu",
        "AGU_BANCO": "C:\\Users\\Matheus Menegatti\\Documents\\AGU_Acervo_Consultivo\\agu_consultivo.db",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1"
      }
    }
  }
}
```

O `PYTHONPATH` não é opcional: o Claude Desktop **descarta a chave `cwd`** ao
ler a configuração, e sem diretório de trabalho o `-m agu` não acha o pacote. O
sintoma é o servidor conectar e morrer em 350 ms, com `No module named agu` no
log.

Ao mudar ferramentas ou instruções, **remova e recrie** o conector — desligar e
religar não basta, o cliente mantém a versão antiga em cache. Confira com
`cobertura_do_acervo`: têm de vir 1.920 documentos.

## Ferramentas

| | |
|---|---|
| `o_que_vincula` | só o que tem força normativa: ONs, súmulas e o de alcance federal |
| `manifestacoes_referenciais` | referenciais das CONJURs, **separadas pelo prazo de validade** |
| `pesquisar_manifestacoes` | busca em ementa, assunto e enunciado |
| `pesquisar_inteiro_teor` | busca no texto e **devolve a página**, com seção e grau de transcrição |
| `ler_paginas` | páginas contíguas, para ver o contexto ao redor |
| `expandir_consulta` | variantes do conceito, com a contagem de cada uma |
| `obter_documento` | ficha completa |
| `quem_citou` | quem cita uma norma, súmula, ON ou acórdão |
| `situacao_do_ato` | o que a fonte declara sobre cancelamento, revogação e nova redação |
| `listar_documentos` | varredura por ano, câmara, fonte ou grau de vinculação |
| `cobertura_do_acervo` | volumes, período, distribuição por vinculação e limites |

## A régua: o grau de vinculação

Cada base tem um risco jurídico próprio, e é ele que define a ferramenta
central. No acervo de jurisprudência é a **proveniência** — de que parte do
acórdão veio o trecho. No de legislação, a **vigência**. Aqui é a **força
vinculante**.

Ela não está no texto. Um parecer que obriga toda a Administração Federal e um
que alcança apenas os órgãos envolvidos naquele processo têm o mesmo
vocabulário, a mesma estrutura e o mesmo aspecto. A diferença está no metadado.

O acervo tem cinco camadas, e elas não se equivalem:

```
  215  Pareceres do Advogado-Geral aprovados pelo Presidente e publicados
       — art. 40, § 1º, da LC 73/93. Grau máximo do sistema.
  110  Orientações Normativas da AGU
   86  Súmulas da AGU (obrigam AGU, PGF e PGBC)
1.724  Manifestações do CONUNI — só 12 de alcance federal
  884  Manifestações Referenciais das CONJURs, com prazo de validade
```

Dentro do CONUNI, que é o volume do acervo, a proporção é o que mais engana:

```
Apenas os órgãos envolvidos no processo    510
Órgãos da Consultoria-Geral da União       851
Órgãos da AGU                              350
Toda a Administração Pública Federal        12
```

**Doze de 1.724.** Apresentar qualquer um dos outros 1.712 como vinculante da
Administração Federal inverte o documento.

O servidor traduz o que a fonte declarou; não qualifica juridicamente. **Só nos
215 pareceres vinculantes os dois requisitos do art. 40, § 1º vêm documentados
na fonte** — o Presidente que aprovou e a data de publicação no DOU. Para o
resto, confere-se no ato.

**E nada disto vincula Município.** O acervo é federal: para o ente subnacional,
até a Orientação Normativa é precedente persuasivo. O aviso acompanha toda
resposta de busca — é o que mais importa para a carteira deste escritório.

## O segundo risco, que vale só para um corpus: o prazo

As 884 Manifestações Jurídicas Referenciais têm **prazo de validade**, e o resto
do acervo não. Um referencial dispensa a análise jurídica individualizada dos
processos da classe que descreve; vencido, **não dispensa nada**, e invocá-lo
para dispensar parecer é vício no processo administrativo.

Medido na coleta, das 823 com prazo declarado:

```
vencidas          463   (56%)
em vigor          360
sem prazo          61
```

Mais da metade. E o texto de uma vencida é idêntico ao de uma válida — a
diferença está só na data.

Por isso `manifestacoes_referenciais` separa em vigor, vencidas e sem prazo, e
calcula o vencimento **contra a data da consulta**, não contra a data em que o
acervo foi construído. Gravar "vencido" no índice congelaria a resposta e ela
envelheceria em silêncio.

## O que o acervo não tem

- **1.115 das 1.724 manifestações do CONUNI não têm inteiro teor.** A AGU as
  publica no Sapiens, sistema interno cujo acesso anônimo devolve a tela de
  login. Delas há ementa e assunto, e nada mais.
- **369 dos 609 PDFs públicos são digitalização sem camada de texto** —
  invisíveis à busca. Concentram-se entre 2010 e 2014. Precisariam de OCR em
  português, que não está instalado nesta máquina (há Tesseract 5.4, mas só com
  os idiomas `eng` e `osd`).
- Os pareceres **individuais** das Consultorias Jurídicas junto aos Ministérios
  não são públicos e não estão aqui. As **manifestações referenciais** dessas
  mesmas Consultorias estão — 884 delas.
- Dos 884 referenciais, só **88 têm PDF próprio**; 760 apontam para o Sapiens e
  760 ficam com ementa apenas. A ementa é substanciosa (traz fundamento
  jurídico, requisitos formais e prazo), mas não é o parecer.
- **7 Orientações Normativas não têm enunciado na página oficial** — a AGU
  publica só o título e a situação (cancelada, revogada, nova redação em outra
  ON). Vêm marcadas.

Consequência que precisa aparecer na resposta ao advogado: **ausência de um
argumento nesta base não prova que a AGU não o enfrentou.** "Não localizei no
que está publicado" é verdade; "a AGU não se pronunciou" não é.

## Vigência, e o que é melhor aqui do que na PGE-RJ

No acervo da PGE-RJ a situação da norma tinha de ser inferida da proximidade de
palavras na ementa. Aqui a fonte declara: 6 ONs vêm marcadas como canceladas,
revogadas ou de redação alterada; 53 manifestações do CONUNI nomeiam a
manifestação revogadora; as súmulas trazem o ato revogador com data e DOU.

O que continua fora do alcance, e o servidor diz: revogação tácita, norma
superveniente e decisão judicial. `situacao_do_ato` devolve o que a AGU
publicou na data da coleta, nunca uma garantia de vigência.

## Testes

```bash
.\.venv\Scripts\python.exe -m pytest
```

41 testes. Os de `test_autoridade.py` são os que importam: se passarem e todos
os outros falharem, o acervo ainda é honesto sobre a única coisa que decide o
uso do documento numa peça.
