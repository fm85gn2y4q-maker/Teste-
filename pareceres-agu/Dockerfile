# Imagem do acervo consultivo da AGU para hospedagem (Render, Cloud Run, Fly).
#
# O acervo viaja dentro da imagem: SQLite lido em modo somente leitura, sem
# banco externo nem volume para manter. Aqui isso é barato — são dezenas de MB,
# contra os 766 MB do acervo da PGE-RJ, porque 1.115 das manifestações não têm
# inteiro teor público. O limite da fonte virou folga na hospedagem.
FROM python:3.12-slim

WORKDIR /app

# As dependências mudam menos que o código: instaladas antes, para aproveitar
# o cache entre construções.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY agu/ ./agu/

# O acervo é artefato de dados, não código: vem de um asset de release, com a
# versão fixada. Assim o deploy é reproduzível, o rollback é trocar a versão, e
# o histórico do Git não carrega uma cópia binária a cada atualização.
#
# A versão é declarada AQUI, como padrão do ARG, e não como argumento de
# construção do serviço: nem todo serviço repassa argumentos de build, e
# depender disso deixa a imagem sem acervo por um motivo invisível.
# Publicar acervo novo é trocar estas duas linhas.
ARG ACERVO_URL=https://github.com/fm85gn2y4q-maker/Teste-/releases/download/consultivo-agu-v1.2.0/consultivo-agu-v1.2.0.db.gz
ARG ACERVO_SHA256=4380acee9bba8d6ac602c42d0bee53edbb4a009c6d6ad313195f147dd16b5e49
COPY baixar_acervo.py ./
RUN python baixar_acervo.py "$ACERVO_URL" dados/agu_consultivo.db "$ACERVO_SHA256"

# O serviço define a porta; 8080 é o padrão quando ele não define.
ENV PORT=8080 \
    AGU_HOST=0.0.0.0 \
    AGU_BANCO=/app/dados/agu_consultivo.db \
    PYTHONUTF8=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8080

# AGU_DOMINIOS é definido depois do primeiro deploy, quando o endereço público
# passa a existir. Sem ele, só requisição local é aceita — o que na prática
# significa que o serviço recusa tudo com 421.
CMD ["python", "-m", "agu", "--http"]
