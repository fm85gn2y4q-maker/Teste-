# Imagem do Ementário para hospedagem (Cloud Run, Render, Fly e afins).
#
# O acervo viaja dentro da imagem: 2,7 GB de SQLite lido em modo somente-
# leitura, e assim não há banco externo nem volume para manter. Parece muito
# para um plano gratuito, mas o que ele restringe é disco PERSISTENTE — e aqui
# não há: o arquivo é camada de imagem, imutável, e o filesystem efêmero basta.
#
# A memória também não é o gargalo que o tamanho sugere: o SQLite lê por
# páginas, com cache padrão de ~2 MB, e não carrega o banco na RAM.
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
ARG ACERVO_URL=https://github.com/fm85gn2y4q-maker/Teste-/releases/download/acervo-v3.3.0/ementario-tcerj-v3.3.0.db.gz
ARG ACERVO_SHA256=4787da94522ab71da99d501125e83e29b23effe7706dfed5622d9ebc01d8e0f2
COPY baixar_acervo.py ./
RUN python baixar_acervo.py "$ACERVO_URL" dados/tcerj.sqlite "$ACERVO_SHA256"

# O acervo NORMATIVO viaja no mesmo servidor, em banco separado. Separado
# porque as duas bases erram por motivos distintos — a jurisprudencia pela
# proveniencia do trecho, a norma pela vigencia — e um schema so convidaria a
# tratar as duas com a mesma regua. Juntas no processo, apartadas no banco.
ARG NORMAS_URL=https://github.com/fm85gn2y4q-maker/Teste-/releases/download/normas-v1.0.0/normas-tcerj-v1.0.0.db.gz
ARG NORMAS_SHA256=d88998db7d8d7fe2f9304900c16f9847a5897705639b4429448bfdf61a3538c4
RUN python baixar_acervo.py "$NORMAS_URL" dados/normas-tcerj.sqlite "$NORMAS_SHA256"

# O serviço define a porta; 8080 é o padrão do Cloud Run quando ele não define.
ENV PORT=8080 \
    EMENTARIO_HOST=0.0.0.0 \
    EMENTARIO_BANCO=/app/dados/tcerj.sqlite \
    NORMAS_BANCO=/app/dados/normas-tcerj.sqlite \
    PYTHONUTF8=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8080

# EMENTARIO_DOMINIOS é definido depois do primeiro deploy, quando o endereço
# público passa a existir. Sem ele, só requisições locais são aceitas — o que
# na prática significa que o serviço responde 421 a tudo.
CMD ["python", "-m", "ementario", "--http"]
