import urllib.request
import urllib.error
import json

NOME = "ALINE TAVARES NEVES"
ANO = 2025

ENDPOINTS = [
    "https://transparencia.mesquita.rj.gov.br/sincronias/apidados.rule?sys=LAI",
    "http://transparencia.mesquita.rj.gov.br/sincronias/apidados.rule?sys=LAI",
    "https://transparencia.mesquita.rj.gov.br/apidados.rule?sys=LAI",
]

PAYLOAD = json.dumps({"api": "salarios_servidores_bruto_liquido", "ano": ANO}).encode("utf-8")

def tentar(url):
    req = urllib.request.Request(
        url,
        data=PAYLOAD,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read()
            return json.loads(body)
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code}: {url}")
        return None
    except Exception as e:
        print(f"  Erro: {e}: {url}")
        return None

data = None
for url in ENDPOINTS:
    print(f"Tentando: {url}")
    data = tentar(url)
    if data:
        print(f"  OK! Status: {data.get('status')}")
        break

if not data:
    print("\nNenhum endpoint funcionou.")
elif data.get("status") != "sucesso":
    print(f"\nErro da API: {data.get('retorno')}")
else:
    registros = [
        r for r in data.get("dados", [])
        if NOME in r.get("NOME", "").upper()
    ]

    if not registros:
        print(f"\nNenhum registro encontrado para '{NOME}' em {ANO}.")
        print("Nomes disponíveis com 'ALINE':")
        for r in data.get("dados", []):
            if "ALINE" in r.get("NOME", "").upper():
                print(" -", r["NOME"])
    else:
        print(f"\n{'='*60}")
        print(f"SERVIDOR: {registros[0]['NOME']}")
        print(f"{'='*60}")
        for r in sorted(registros, key=lambda x: (x["ANO"], x["MES"])):
            print(f"\n  Competência : {r['MES']:>2}/{r['ANO']}")
            print(f"  Cargo       : {r['CARGO']}")
            print(f"  Secretaria  : {r['SECRETARIA']}")
            print(f"  Regime      : {r['DESCRICAO_REGIME']}")
            print(f"  Base Sal.   : R$ {float(r['BASE_SALARIAL']):>10.2f}")
            print(f"  Bruto       : R$ {float(r['BRUTO']):>10.2f}")
            print(f"  IR          : R$ {float(r['IMPOSTODERENDA']):>10.2f}")
            print(f"  Prev.       : R$ {float(r['Desconto_Previdenciario']):>10.2f}")
            print(f"  Outros desc.: R$ {float(r['Outros_descontos']):>10.2f}")
            print(f"  LIQUIDO     : R$ {float(r['LIQUIDO']):>10.2f}")
            print(f"  Admissão    : {r['DATA_ADMISSAO'][:10]}")
            print(f"  Concursado  : {r['Concursado']}")
            print(f"  Fonte       : {r['FONTE_RECURSOS']}")
