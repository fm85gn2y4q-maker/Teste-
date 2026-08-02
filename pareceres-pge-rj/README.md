# Pareceres da PGE-RJ — servidor MCP

Acervo consultivo da Procuradoria-Geral do Estado do Rio de Janeiro sobre
**contratações, acordos e parcerias** — licitação, contratação direta, contrato
administrativo, convênio, terceiro setor (OS, OSCIP, MROSC), concessão,
permissão e uso de bem público.

Um servidor por acervo, como o Ementário do TCE-RJ e a Legislação de Mesquita.
Não mistura instituições: parecer da PGE-RJ, da AGU e de outra PGE têm graus de
autoridade diferentes, e numa tabela só essa diferença vira metadado ignorável.

## O acervo

| | |
|---|---|
| Documentos | 14.420 |
| Com inteiro teor | 8.559 |
| Só ficha e ementa | 5.861 |
| Páginas indexadas | 177.156 |
| Sem camada de texto | 291 |
| Período | 1961 a 2026 |
| Citações mapeadas | 76.017 |

Banco: `~/Documents/PGE-RJ_Pareceres_Contratacoes/pge_rj_pareceres.db` (1,3 GB),
fora do repositório — é artefato de dados. O caminho pode ser passado com
`--banco` ou pela variável `PARECERES_BANCO`.

## Como rodar

```bash
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pareceres            # stdio, para o Claude
.\.venv\Scripts\python.exe -m pareceres --http     # HTTP em 127.0.0.1:8766
```

O SDK precisa ser da série 1.x: o `mcp` 2.0 removeu `mcp.server.fastmcp`.

### Claude Desktop

```json
{
  "mcpServers": {
    "pareceres-pge-rj": {
      "command": "C:\\Users\\Matheus Menegatti\\projetos\\Teste-\\pareceres-pge-rj\\.venv\\Scripts\\python.exe",
      "args": ["-m", "pareceres"],
      "env": {
        "PYTHONPATH": "C:\\Users\\Matheus Menegatti\\projetos\\Teste-\\pareceres-pge-rj",
        "PARECERES_BANCO": "C:\\Users\\Matheus Menegatti\\Documents\\PGE-RJ_Pareceres_Contratacoes\\pge_rj_pareceres.db",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1"
      }
    }
  }
}
```

O `PYTHONPATH` não é opcional: o Claude Desktop **descarta a chave `cwd`** ao
ler a configuração, e sem diretório de trabalho o `-m pareceres` não acha o
pacote. O sintoma é o servidor conectar e morrer em 350 ms, com
`No module named pareceres` no log.

Ao mudar ferramentas ou instruções, **remova e recrie** o conector — desligar e
religar não basta, o cliente mantém a versão antiga em cache. Confira com
`cobertura_do_acervo`: tem de vir 14.420 documentos e 177.156 páginas.

## Ferramentas

| | |
|---|---|
| `pesquisar_pareceres` | busca em ementa, assuntos indexados e título |
| `pesquisar_inteiro_teor` | busca no texto e **devolve a página**, com seção e grau de transcrição |
| `ler_paginas` | páginas contíguas, para ver o contexto ao redor |
| `expandir_consulta` | variantes do conceito, com a contagem de cada uma |
| `obter_documento` | ficha completa |
| `conclusoes_sobre` | só as conclusões — triagem rápida de muitos pareceres |
| `quem_citou` | quem cita uma norma, súmula, acórdão ou parecer interno |
| `listar_documentos` | varredura por ano, procurador, órgão, eixo ou regime |
| `cobertura_do_acervo` | volumes, período, recorte, autoridade e limites |

## As três regras, e o que as sustenta

Não são conselhos de prudência: cada uma responde a um defeito medido no
acervo.

**1. A busca é literal; o vocabulário jurídico não é.** `"reequilíbrio
econômico-financeiro"` acha 248 documentos. `"equilíbrio econômico-financeiro"`
acha 649; `"reajustamento de preços"`, 397; `"teoria da imprevisão"`, 108.
Somadas, **1.716** — quem busca só a primeira forma perde 85%. Daí o tesauro de
130 variantes em 25 conceitos, cada uma com a contagem medida no próprio
acervo, e a instrução de chamar `expandir_consulta` antes de dizer que não há
precedente.

**2. De quem é o trecho.** Um parecer reúne o relatório do que o órgão
consultou, doutrina e jurisprudência transcritas, pareceres anteriores citados,
a tese que o parecerista vai **refutar**, e só então a opinião da PGE. Para a
busca são caracteres iguais. Cada página carrega `secao` e `transcricao` (0 a
100). **18% das páginas têm transcrição ≥ 50, e 11.658 dessas estão dentro da
fundamentação** — é ali que se atribui à Procuradoria palavra de terceiro.

**3. Vigência.** Dos 14.420 documentos, **12.535 são anteriores a 2021**. Entre
os que têm inteiro teor: 4.335 sob a Lei 8.666/93, revogada desde 30/12/2023, e
**101** aplicando exclusivamente a Lei 14.133/2021. Cada documento traz `regime`
e `alerta_vigencia`.

## Autoridade

Parecer da PGE-RJ vincula a Administração **estadual** fluminense nos termos da
legislação própria. **Para município é precedente persuasivo, não norma.**

Não é o acervo integral da PGE-RJ, que tem 49.139 documentos: é o recorte
temático. Ausência aqui não prova que a Procuradoria não se pronunciou.

## Limitações conhecidas

- **72.250 páginas (41%) têm `secao` indefinida.** A seção só é determinada
  quando há marcador de fim de relatório ("É o relatório", "passo a opinar").
  Ofícios, promoções e vistos não têm essa estrutura. Nessas páginas resta o
  `transcricao`, sem saber se o trecho está no relatório ou na fundamentação.
- **3.380 documentos com inteiro teor ficaram em `regime` não identificado** —
  não citam nenhuma lei de regência reconhecível, em geral por OCR degradado ou
  por tratarem de convênio e uso de bem público. Para esses, a data é o único
  sinal de vigência.
- **1.093 documentos não tiveram fórmula de conclusão identificada.** Para eles
  vem `fecho_bruto`, o fim literal do texto, explicitamente marcado como tal.
- **291 documentos são digitalização sem camada de texto** — invisíveis à busca.

Nenhuma dessas é bug: é o limite de heurística sobre texto degradado. Estão
declaradas em `cobertura_do_acervo` para que apareçam na resposta em vez de
ficarem escondidas atrás de um número redondo.
