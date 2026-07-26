# Imagem do Ementário para hospedagem (Cloud Run, Render, Fly e afins).
#
# O acervo viaja dentro da imagem: são ~10 MB de SQLite lido em modo
# somente-leitura, e assim não há banco externo nem volume para manter.
FROM python:3.12-slim

WORKDIR /app

# As dependências mudam menos que o código: instaladas antes para aproveitar
# o cache entre builds.
COPY requirements-servidor.txt ./
RUN pip install --no-cache-dir -r requirements-servidor.txt

COPY ementario/ ./ementario/

# O acervo é artefato de dados, não código: vem de um asset de release, com a
# versão fixada. Assim o deploy é reproduzível, o rollback é trocar a versão, e
# o histórico do Git não carrega uma cópia binária a cada atualização.
#
# A versão é declarada AQUI, como padrão do ARG, e não como argumento de
# construção do serviço de hospedagem: nem todo serviço repassa argumentos de
# build, e depender disso deixava a imagem sem acervo por um motivo invisível.
# Publicar um acervo novo é trocar estas duas linhas.
ARG ACERVO_URL=https://github.com/fm85gn2y4q-maker/Teste-/releases/download/acervo-v2.0.0/ementario-tcerj-v2.0.0.db.gz
ARG ACERVO_SHA256=513fd3146272d98a71dfa8b98aba5ce27b6262ce2f260360cbd0e2d135bab395
COPY baixar_acervo.py ./
RUN python baixar_acervo.py "$ACERVO_URL" dados/tcerj.sqlite "$ACERVO_SHA256"

# O serviço define a porta; 8080 é o padrão do Cloud Run quando ele não define.
ENV PORT=8080 \
    EMENTARIO_HOST=0.0.0.0 \
    EMENTARIO_BANCO=/app/dados/tcerj.sqlite \
    PYTHONUTF8=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8080

# EMENTARIO_DOMINIOS é definido depois do primeiro deploy, quando o endereço
# público passa a existir. Sem ele, só requisições locais são aceitas — o que
# na prática significa que o serviço responde 421 a tudo.
CMD ["python", "-m", "ementario", "--http"]
