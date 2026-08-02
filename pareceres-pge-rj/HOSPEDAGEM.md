# Hospedagem

O servidor fala dois transportes. Por **stdio** ele roda como processo local —
é assim que o Claude Desktop o usa, seja pela configuração manual, seja pela
extensão `.mcpb`. Por **HTTP** ele pode ser hospedado, e aí atende também o
ChatGPT e outras máquinas.

Este documento é sobre o segundo caso.

---

## Antes de tudo: o tamanho é o problema

O acervo tem **766 MB**, contra os ~10 MB do Ementário. Isso muda o cálculo.

| | Ementário (TCE-RJ) | Pareceres (PGE-RJ) |
|---|---|---|
| Acervo na imagem | ~10 MB | **766 MB** |
| Comprimido (asset) | 24 MB | **266 MB** |

**Não verifiquei se o plano gratuito do Render comporta uma imagem desse
tamanho.** O plano free tem 512 MB de RAM, e o disco da instância é efêmero
mas precisa caber a imagem. O SQLite é lido do disco, não carregado em
memória, então a RAM tende a bastar — o risco está no disco e no tempo de
construção, que inclui baixar e descomprimir 266 MB.

Se o deploy falhar por espaço, há três saídas, em ordem de esforço:

1. **Plano pago** com mais disco — é a solução direta.
2. **Servir só a ficha**, deixando o inteiro teor de fora da imagem: sem
   `paginas_fts`, o banco cai para poucas dezenas de MB, e `pesquisar_pareceres`,
   `expandir_consulta`, `quem_citou` e `cobertura_do_acervo` continuam
   funcionando. Perde-se a busca por página, que é justamente o que permite
   citar folha — é uma perda séria, e o servidor precisaria declará-la.
3. **Não hospedar.** A extensão `.mcpb` já resolve o uso local, que é o seu
   caso principal. Hospedar só se justifica para o ChatGPT ou outra máquina.

---

## Publicar o acervo como asset de release

O banco não vai para o Git: é artefato de dados. A imagem o busca na
construção, com a versão fixada.

```bash
python pipeline/enxugar.py
```

Depois, comprima e calcule o hash:

```bash
python -c "import gzip,shutil,hashlib,os; src=os.path.expanduser('~/Documents/PGE-RJ_Pareceres_Contratacoes/pge_rj_pareceres_enxuto.db'); dst='pge-rj-pareceres-v1.0.0.db.gz'; f=open(src,'rb'); g=gzip.open(dst,'wb',6); shutil.copyfileobj(f,g,1<<20); g.close(); h=hashlib.sha256(); fh=open(dst,'rb'); [h.update(b) for b in iter(lambda: fh.read(1<<20), b'')]; print(dst, os.path.getsize(dst), h.hexdigest())"
```

Crie a release e suba o arquivo:

```bash
gh release create pareceres-pge-rj-v1.0.0 pge-rj-pareceres-v1.0.0.db.gz --title "Acervo PGE-RJ v1.0.0" --notes "14.420 documentos, 8.559 com inteiro teor, 177.156 paginas."
```

Por fim, atualize as **duas linhas** do `Dockerfile` — `ACERVO_URL` e
`ACERVO_SHA256`. A versão fica ali, e não no `render.yaml`: campo desconhecido
no Blueprint faz ele falhar inteiro, e argumento de build não é repassado da
mesma forma por todo serviço. Menos lugares onde errar.

O acervo atualmente declarado no `Dockerfile`:

```
sha256  95b7d8a31a3889863cfc34bc798630c581634b7c1edf47f71e287b6c50739e43
```

**Esse asset ainda não existe.** A URL está no Dockerfile, mas o arquivo
precisa ser publicado na release antes do primeiro deploy — a construção falha
na conferência do hash se ele não estiver lá, que é o comportamento desejado.

---

## Deploy no Render

O serviço já está declarado no `render.yaml` da raiz do repositório, ao lado do
Ementário. O nome define o endereço público e precisa ser único entre todos os
usuários do Render; trocando o `name`, troque também `PARECERES_DOMINIOS`.

```
https://pareceres-pge-rj.onrender.com/mcp
```

**A proteção de Host não usa curinga.** Sem `PARECERES_DOMINIOS` declarando o
endereço público, o servidor recusa tudo com 421 — é a defesa do SDK contra
DNS rebinding, e ela compara o Host exatamente.

No plano gratuito o serviço dorme após ~15 minutos parado, e a primeira
consulta seguinte demora perto de um minuto.

---

## Autenticação

Fica **desligada**, como no Ementário. O acervo é público — pareceres da PGE-RJ
publicados no portal da própria Procuradoria — e tanto o Claude quanto o
ChatGPT aceitam servidor MCP sem autenticação.

Se um dia for necessário, o projeto irmão tem o fluxo OAuth pronto e testado em
`scraper-tcerj/ementario/autenticacao.py`, e o padrão é ativá-lo declarando a
URL pública.

Vale a distinção que o outro projeto registrou: **ato público pôde ir para
endereço aberto; doutrina não poderia.** Se algum dia este servidor passar a
servir obra protegida, a autenticação deixa de ser opcional.

---

## Conferir depois do deploy

Chame a cobertura do acervo. Tem de vir **14.420 documentos e 177.156
páginas** — o mesmo número que a extensão local devolve. Vindo outro, ou
vindo erro, o acervo da imagem não é o que se espera.
