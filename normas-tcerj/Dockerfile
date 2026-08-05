# Imagem do acervo normativo do TCE-RJ.
#
# O acervo viaja dentro da imagem: 22 MB de SQLite lido em modo somente-leitura,
# sem banco externo nem volume. O filesystem efêmero basta porque nada é escrito.
FROM python:3.12-slim

WORKDIR /app

COPY requirements-servidor.txt ./
RUN pip install --no-cache-dir -r requirements-servidor.txt

COPY servidor/ ./servidor/

# O acervo é artefato de dados, não código: vem de um asset de release, com a
# versão fixada. Publicar um acervo novo é trocar estas duas linhas.
ARG ACERVO_URL=https://github.com/fm85gn2y4q-maker/Teste-/releases/download/normas-v1.0.0/normas-tcerj-v1.0.0.db.gz
ARG ACERVO_SHA256=d88998db7d8d7fe2f9304900c16f9847a5897705639b4429448bfdf61a3538c4
COPY baixar_acervo.py ./
RUN python baixar_acervo.py "$ACERVO_URL" dados/normas-tcerj.sqlite "$ACERVO_SHA256"

ENV PORT=8080 \
    NORMAS_HOST=0.0.0.0 \
    NORMAS_BANCO=/app/dados/normas-tcerj.sqlite \
    PYTHONUTF8=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8080

# NORMAS_DOMINIOS é definido no serviço, depois do primeiro deploy: sem ele a
# proteção de Host recusa tudo com 421.
CMD ["python", "-m", "servidor", "--http"]
