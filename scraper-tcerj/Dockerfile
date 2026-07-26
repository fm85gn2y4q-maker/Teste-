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
ARG ACERVO_URL
ARG ACERVO_SHA256=""
COPY baixar_acervo.py ./
RUN test -n "$ACERVO_URL" || (echo "Defina ACERVO_URL na construção." && exit 1) \
 && python baixar_acervo.py "$ACERVO_URL" dados/tcerj.sqlite "$ACERVO_SHA256"

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
