import urllib.parse, urllib.request, json, time
API="https://documentacao.pge.rj.gov.br/scripts/bnweb/bnmapi.exe?router=search"
FIELDS="codigo,tipo_sigla,tipo_nome,titulo,data_pub,ementa,numero,processo,precedentes"
EXPAND="assuntos,links,anexos,membros,andamentos"
def search(exp, page=1, limit=50, fields=FIELDS, expand=EXPAND, sort="codigo desc", tries=3):
    params={"page":str(page),"sort":sort,"filter":json.dumps({"exp":[exp]},ensure_ascii=False),
            "limit":str(limit),"fields":fields}
    if expand: params["expand"]=expand
    url=API+"&"+urllib.parse.urlencode(params)
    last=None
    for _ in range(tries):
        try:
            raw=urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0"}),timeout=120).read()
            return json.loads(raw.decode("utf-8","ignore"))
        except Exception as e:
            last=e; time.sleep(2)
    raise last
def count(exp):
    return search(exp,limit=1,expand=None,fields="codigo")["pagination"]["total"]
