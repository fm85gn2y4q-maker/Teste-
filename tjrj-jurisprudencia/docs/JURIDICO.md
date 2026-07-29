# Limites jurídicos do acervo

Você é advogado; não vou explicar LGPD. O que segue é o mapa de onde as
decisões jurídicas encostam nas decisões de engenharia deste projeto — e onde
o código já tomou partido.

## Publicidade não é licença de redifusão

Os acórdãos do TJRJ são públicos (art. 93, IX, da Constituição). Isso resolve
a coleta e não resolve a **redistribuição em massa** com dados pessoais. Um
acervo com ementa, inteiro teor e nome de parte, pesquisável por nome, é
funcionalmente outra coisa: é um cadastro de pessoas por litígio. É esse uso
que o CNJ restringe na consulta pública (Res. 121/2010) e que a LGPD
disciplina.

Por isso a tabela `parte` é separada de tudo o mais no esquema, tem coluna
`sigilo`, e as ferramentas do MCP nunca filtram por nome de parte — só
exibem, e apenas as não sigilosas. Se um dia você publicar o acervo, a
decisão de incluir ou não essa tabela é uma linha no exportador, tomada
conscientemente, e não um efeito colateral.

## Segredo de justiça

Processo em segredo não entra. Nem a ementa. O campo `segredo_justica` existe
para isso e deve ser preenchido sempre que a fonte sinalizar. Na dúvida sobre
um documento, o padrão é excluir.

## Ritmo de coleta

O código usa uma conexão, meia requisição por segundo, recuo exponencial e
`User-Agent` identificado com um e-mail de contato. Isso não é timidez: é o
que separa um coletor de um incidente de disponibilidade num serviço público.

Duas condutas que o projeto **não** implementa, deliberadamente: rotação de
IP e resolução de CAPTCHA. Se o TJRJ bloquear (`BloqueioError` no 403), o
caminho correto é parar, reduzir o ritmo e, se necessário, formalizar o
pedido pela via administrativa — não contornar o controle. Contornar
converteria um projeto legítimo de pesquisa em algo que você não quer ter que
explicar depois.

## Termos de uso

Confira o `robots.txt` e os termos vigentes do portal antes da varredura
longa, e registre a data da conferência. Se houver vedação expressa à coleta
automatizada, o pedido via LAI (ver `FONTES.md`, seção 6) deixa de ser
atalho e passa a ser o caminho.

## Uso do acervo por IA

Quando o MCP alimentar um modelo, duas cautelas viram texto nas instruções do
servidor:

1. **Ausência de resultado não é prova de inexistência de precedente.** A
   base tem lacunas conhecidas e declaradas (`cobertura_do_acervo`), e um
   modelo que trate silêncio como negativa produz parecer errado.
2. **A origem da proposição tem que aparecer.** "Consta da ementa" e "consta
   do voto, à p. 27" têm pesos diferentes numa peça. As duas buscas são
   ferramentas separadas exatamente para que essa distinção não se perca.

E o óbvio que precisa estar escrito: precedente de segundo grau não é
vinculante, e nenhum acervo dispensa a conferência do inteiro teor antes de
citar.
