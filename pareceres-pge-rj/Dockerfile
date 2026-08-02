# Imagem dos pareceres da PGE-RJ para hospedagem (Render, Cloud Run, Fly).
#
# O acervo viaja dentro da imagem: 766 MB de SQLite lido em modo somente
# leitura, sem banco externo nem volume para manter. É grande — leia a nota
# sobre plano gratuito em HOSPEDAGEM.md antes de escolher o serviço.
FROM python:3.12-slim

WORKDIR /app

# As dependências mudam menos que o código: instaladas antes, para aproveitar
# o cache entre construções.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY pareceres/ ./pareceres/

# O acervo é artefato de dados, não código: vem de um asset de release, com a
# versão fixada. Assim o deploy é reproduzível, o rollback é trocar a versão, e
# o histórico do Git não carrega uma cópia binária a cada atualização.
#
# A versão é declarada AQUI, como padrão do ARG, e não como argumento de
# construção do serviço: nem todo serviço repassa argumentos de build, e
# depender disso deixa a imagem sem acervo por um motivo invisível.
# Publicar acervo novo é trocar estas duas linhas.
ARG ACERVO_URL=https://github.com/fm85gn2y4q-maker/Teste-/releases/download/pareceres-pge-rj-v1.0.0/pge-rj-pareceres-v1.0.0.db.gz
ARG ACERVO_SHA256=95b7d8a31a3889863cfc34bc798630c581634b7c1edf47f71e287b6c50739e43
COPY baixar_acervo.py ./
RUN python baixar_acervo.py "$ACERVO_URL" dados/pge_rj_pareceres.db "$ACERVO_SHA256"

# O serviço define a porta; 8080 é o padrão quando ele não define.
ENV PORT=8080 \
    PARECERES_HOST=0.0.0.0 \
    PARECERES_BANCO=/app/dados/pge_rj_pareceres.db \
    PYTHONUTF8=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8080

# PARECERES_DOMINIOS é definido depois do primeiro deploy, quando o endereço
# público passa a existir. Sem ele, só requisição local é aceita — o que na
# prática significa que o serviço recusa tudo com 421.
CMD ["python", "-m", "pareceres", "--http"]
