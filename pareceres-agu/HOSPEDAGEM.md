# Hospedagem

O servidor fala dois transportes. Por **stdio** ele roda como processo local —
é assim que o Claude Desktop o usa. Por **HTTP** ele pode ser hospedado, e aí
atende também o ChatGPT e outras máquinas.

Este documento é sobre o segundo caso.

## O tamanho, aqui, não é problema

| | Ementário (TCE-RJ) | Pareceres (PGE-RJ) | Consultivo (AGU) |
|---|---|---|---|
| Acervo na imagem | ~10 MB | 766 MB | **~30 MB** |
| Comprimido (asset) | 24 MB | 266 MB | **~10 MB** |

O acervo da PGE-RJ quase não coube no plano gratuito do Render. Este cabe com
folga, e pelo motivo menos animador possível: **1.115 das 1.724 manifestações
do CONUNI não têm inteiro teor público.** O limite da fonte virou folga na
hospedagem.

## Publicar o acervo como asset de release

O banco não vai para o Git: é artefato de dados. A imagem o busca na
construção, com a versão fixada.

```bash
python pipeline/publicar.py 1.0.0
```

O script comprime, calcula o sha256, cria a release e **atualiza as duas linhas
do `Dockerfile`** — `ACERVO_URL` e `ACERVO_SHA256`. A versão fica ali, e não no
`render.yaml`: campo desconhecido no Blueprint faz ele falhar inteiro, e
argumento de build não é repassado da mesma forma por todo serviço. Menos
lugares onde errar.

Sem o asset publicado, a construção falha na conferência do hash — que é o
comportamento desejado.

## Deploy no Render

O serviço está declarado no `render.yaml` da raiz do repositório, ao lado do
Ementário e dos pareceres da PGE-RJ. O nome define o endereço público e precisa
ser único entre **todos** os usuários do Render.

**A proteção de Host não usa curinga.** Sem `AGU_DOMINIOS` declarando o
endereço público real, o servidor recusa tudo com 421 — é a defesa do SDK
contra DNS rebinding, e ela compara o Host exatamente. Foi o que aconteceu com
os pareceres da PGE-RJ: o Render acrescentou um sufixo ao nome (`-kip3`) porque
o nome limpo já estava tomado, e o valor declarado precisou virar o real.

Por isso, na primeira publicação: crie o serviço, veja o endereço que o Render
deu, e só então acerte `AGU_DOMINIOS`.

No plano gratuito o serviço dorme após ~15 minutos parado, e a primeira
consulta seguinte demora perto de um minuto.

## Autenticação

Fica **desligada**, como nos servidores irmãos. O acervo é público — atos e
manifestações que a própria AGU publica em consulta aberta — e tanto o Claude
quanto o ChatGPT aceitam servidor MCP sem autenticação.

Vale a distinção que o projeto do Ementário registrou: **ato público pôde ir
para endereço aberto; doutrina não poderia.** Se algum dia este servidor passar
a servir obra protegida, a autenticação deixa de ser opcional.

## Conferir depois do deploy

Chame a cobertura do acervo. Têm de vir **1.920 documentos** — o mesmo número
que o conector local devolve. Vindo outro, ou vindo erro, o acervo da imagem
não é o que se espera.

E, ao trocar ferramentas ou instruções, **remova e recrie** o conector no
cliente: desligar e religar não limpa o cache da lista de ferramentas.
