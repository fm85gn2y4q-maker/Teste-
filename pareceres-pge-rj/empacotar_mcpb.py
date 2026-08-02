"""Empacota os pareceres da PGE-RJ como extensão do Claude Desktop (.mcpb).

Instala com um duplo clique, sem editar configuração à mão — que foi
justamente onde este projeto tropeçou: a chave `cwd` que o aplicativo descarta
em silêncio, e o servidor morrendo em 350 ms com `No module named pareceres`.

O pacote leva as dependências junto (`server/lib`), porque o Claude Desktop não
instala nada: só executa o que está dentro. Leva também o acervo, para a
extensão funcionar sozinha.

    python empacotar_mcpb.py --python C:\\Caminho\\sem\\espaco\\python.exe

Gera `dist/pareceres-pge-rj.mcpb`.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
CONSTRUCAO = RAIZ / "build" / "mcpb"
DESTINO = RAIZ / "dist" / "pareceres-pge-rj.mcpb"

# O acervo é artefato de dados e mora fora do repositório.
BANCO = Path(os.environ.get(
    "PARECERES_BANCO",
    os.path.expanduser(
        "~/Documents/PGE-RJ_Pareceres_Contratacoes/pge_rj_pareceres_enxuto.db")))

# O Claude Desktop não usa o interpretador do projeto: pega o primeiro `python`
# do PATH dele. Como `pydantic_core` é binário compilado, um .pyd de cp312 não
# carrega no 3.13 — daí um conjunto de dependências por versão.
VERSOES = ("3.12", "3.13", "3.14")

ENTRADA = '''"""Ponto de entrada da extensão: sobe o servidor por stdio."""
import os
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent

# As dependências viajam dentro do pacote, separadas por versão de Python:
# `pydantic_core` é compilado, e o binário de uma versão não serve para outra.
MARCA = f"py{sys.version_info.major}{sys.version_info.minor}"
BIBLIOTECAS = AQUI / "lib" / MARCA
if not BIBLIOTECAS.is_dir():
    disponiveis = sorted(p.name for p in (AQUI / "lib").glob("py*"))
    print(
        f"Pareceres PGE-RJ: sem dependencias para Python "
        f"{sys.version_info.major}.{sys.version_info.minor}. "
        f"O pacote traz: {', '.join(disponiveis) or 'nenhuma'}.",
        file=sys.stderr,
    )
    raise SystemExit(1)

sys.path.insert(0, str(BIBLIOTECAS))
sys.path.insert(0, str(AQUI))

# O `mcp` importa `pywintypes` no Windows. Instalado com `pip --target`, o
# pywin32 nao roda seu pos-instalacao: os modulos ficam em `win32/lib` e as
# DLLs em `pywin32_system32`, nenhum dos dois alcancavel por padrao.
for _extra in ("win32", "pythonwin"):
    _caminho = BIBLIOTECAS / _extra
    if _caminho.is_dir():
        sys.path.insert(0, str(_caminho))
_lib_win32 = BIBLIOTECAS / "win32" / "lib"
if _lib_win32.is_dir():
    sys.path.insert(0, str(_lib_win32))

_dlls = BIBLIOTECAS / "pywin32_system32"
if _dlls.is_dir():
    os.add_dll_directory(str(_dlls))
    os.environ["PATH"] = str(_dlls) + os.pathsep + os.environ.get("PATH", "")

os.environ.setdefault(
    "PARECERES_BANCO", str(AQUI.parent / "dados" / "pge_rj_pareceres.db"))

from pareceres.servidor import construir  # noqa: E402

construir().run(transport="stdio")
'''

FERRAMENTAS = [
    ("pesquisar_pareceres", "Pesquisa na ementa, nos assuntos indexados e no título."),
    ("pesquisar_inteiro_teor", "Pesquisa no texto e devolve a página, com a seção e o "
                               "grau de transcrição."),
    ("ler_paginas", "Lê páginas contíguas de um parecer, para ver o contexto."),
    ("expandir_consulta", "Formas equivalentes de um conceito, com a contagem de cada uma."),
    ("obter_documento", "Ficha completa: ementa, procurador, órgão, processo e conclusão."),
    ("conclusoes_sobre", "Só as conclusões dos pareceres que casam com a busca."),
    ("quem_citou", "Quem cita uma norma, súmula, acórdão ou parecer interno."),
    ("listar_documentos", "Varredura por ano, procurador, órgão, eixo ou regime."),
    ("cobertura_do_acervo", "Volumes, período, recorte, autoridade e limites."),
]

MANIFESTO = {
    "manifest_version": "0.2",
    "name": "pareceres-pge-rj",
    "display_name": "Pareceres PGE-RJ",
    "version": "0.1.0",
    "description": "Pareceres da PGE-RJ em contratações, acordos e parcerias.",
    "long_description": (
        "Acervo consultivo da Procuradoria-Geral do Estado do Rio de Janeiro sobre "
        "licitação, contratação direta, contrato administrativo, convênio, terceiro "
        "setor, concessão e uso de bem público. 14.420 documentos, 8.559 com inteiro "
        "teor, 177.156 páginas, de 1961 a 2026. Cada resultado traz a página para "
        "citação, a seção do parecer, o grau de transcrição de terceiro e o regime "
        "de vigência."
    ),
    "author": {"name": "Matheus Menegatti"},
    "server": {
        "type": "python",
        "entry_point": "server/main.py",
        "mcp_config": {
            "command": "python",
            "args": ["${__dirname}/server/main.py"],
            "env": {"PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
        },
    },
    "tools": [{"name": n, "description": d} for n, d in FERRAMENTAS],
    "keywords": ["parecer", "PGE-RJ", "licitação", "contrato administrativo",
                 "terceiro setor", "direito administrativo"],
    # `compatibility` fica de fora de propósito: é opcional, e no projeto irmão
    # foi o único ponto que o Claude Desktop recusou na instalação.
}


def validar(pasta: Path) -> bool:
    """Passa o manifesto pelo validador oficial, se houver Node por perto.

    Empacotar não prova nada: um manifesto com chave fora do lugar zipa igual e
    só falha na instalação, com a mensagem aparecendo na tela do usuário e não
    aqui. Validador indisponível não é manifesto válido — é ausência de prova,
    e sai com aviso.
    """
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if not npx:
        print("  aviso: npx ausente, manifesto NÃO validado.")
        return True
    resultado = subprocess.run(
        [npx, "--yes", "@anthropic-ai/mcpb", "validate", str(pasta / "manifest.json")],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    saida = (resultado.stdout + resultado.stderr).strip()
    if resultado.returncode == 0:
        print("  manifesto válido.")
        return True
    if any(m in saida.lower() for m in ("invalid manifest", "unrecognized key", "validation")):
        print("  " + "\n  ".join(saida.splitlines()[-8:]))
        return False
    print("  aviso: o validador não pôde ser executado; manifesto NÃO validado.")
    return True


def sem_espacos(caminho: str) -> str | None:
    """Caminho na forma curta 8.3 quando tiver espaço.

    O Claude Desktop quebra o `command` do manifesto nos espaços: um
    interpretador em "C:\\Users\\Fulano Silva\\..." vira o comando
    "C:\\Users\\Fulano" e o resto vira argumento.
    """
    if " " not in caminho:
        return caminho
    import ctypes
    buffer = ctypes.create_unicode_buffer(1024)
    tamanho = ctypes.windll.kernel32.GetShortPathNameW(caminho, buffer, 1024)
    curto = buffer.value if tamanho else ""
    if curto and " " not in curto and Path(curto).exists():
        return curto
    return None


def conferir_interpretador(exe: str) -> bool:
    """Recusa interpretador que não importe o que o servidor usa.

    Um Python com biblioteca padrão incompleta roda `--version` sem reclamar e
    só falha quando o servidor sobe, dentro do Claude, onde o erro fica num log.
    """
    prova = "import html.entities, sqlite3, asyncio, json; print('ok')"
    r = subprocess.run([exe, "-I", "-c", prova], capture_output=True, text=True)
    if r.returncode == 0:
        return True
    ultima = (r.stderr.strip().splitlines() or [""])[-1]
    print(f"  {exe}\n  não serve: {ultima[:110]}", file=sys.stderr)
    return False


def empacotar(python: str | None = None) -> int:
    if python:
        if not Path(python).exists():
            print(f"Interpretador não encontrado: {python}", file=sys.stderr)
            return 1
        print("Conferindo o interpretador escolhido…")
        if not conferir_interpretador(python):
            return 1
        comando = sem_espacos(python)
        if comando is None:
            print(f"  O caminho tem espaços e não há nome curto 8.3 para ele:\n"
                  f"    {python}\n"
                  f"  O Claude Desktop quebraria o comando no primeiro espaço.",
                  file=sys.stderr)
            return 1
        if comando != python:
            print(f"  caminho tem espaço; usando o nome curto: {comando}")
            if not conferir_interpretador(comando):
                return 1
        MANIFESTO["server"]["mcp_config"]["command"] = comando
        versao = subprocess.run([comando, "--version"], capture_output=True,
                                text=True).stdout.strip()
        print(f"  fixado em {versao}")

    if not BANCO.exists():
        print(f"Acervo não encontrado em {BANCO}. Rode o pipeline antes.", file=sys.stderr)
        return 1

    if CONSTRUCAO.exists():
        shutil.rmtree(CONSTRUCAO)
    servidor = CONSTRUCAO / "server"
    servidor.mkdir(parents=True)

    print("Copiando o pacote…")
    shutil.copytree(RAIZ / "pareceres", servidor / "pareceres",
                    ignore=shutil.ignore_patterns("__pycache__"))
    (servidor / "main.py").write_text(ENTRADA, encoding="utf-8")

    for versao in VERSOES:
        marca = "py" + versao.replace(".", "")
        print(f"Instalando as dependências para Python {versao}…")
        r = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--quiet",
             "--target", str(servidor / "lib" / marca),
             "--python-version", versao, "--only-binary=:all:", "mcp>=1.28,<2"],
            capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            print(f"  aviso: sem pacotes para {versao}, seguindo sem ela.")
            shutil.rmtree(servidor / "lib" / marca, ignore_errors=True)

    disponiveis = sorted(p.name for p in (servidor / "lib").glob("py*"))
    if not disponiveis:
        print("Nenhuma dependência empacotada.", file=sys.stderr)
        return 1
    print("  versões no pacote:", ", ".join(disponiveis))

    print(f"Copiando o acervo ({BANCO.stat().st_size / 1e6:.0f} MB)…")
    (CONSTRUCAO / "dados").mkdir()
    shutil.copy2(BANCO, CONSTRUCAO / "dados" / "pge_rj_pareceres.db")

    (CONSTRUCAO / "manifest.json").write_text(
        json.dumps(MANIFESTO, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("Validando o manifesto…")
    if not validar(CONSTRUCAO):
        print("\nManifesto inválido; nada foi empacotado.", file=sys.stderr)
        return 1

    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    if DESTINO.exists():
        DESTINO.unlink()
    print("Compactando…")
    with zipfile.ZipFile(DESTINO, "w", zipfile.ZIP_DEFLATED) as pacote:
        for caminho in sorted(CONSTRUCAO.rglob("*")):
            if caminho.is_file() and "__pycache__" not in caminho.parts:
                pacote.write(caminho, caminho.relative_to(CONSTRUCAO))

    print(f"\n{DESTINO}  ({DESTINO.stat().st_size / 1e6:.0f} MB)")
    print("Instale arrastando o arquivo para Configuracoes > Extensoes do Claude.")
    return 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        prog="python empacotar_mcpb.py",
        description="Empacota os pareceres da PGE-RJ como extensão do Claude Desktop.")
    parser.add_argument("--python", metavar="EXE",
                        help="fixa o interpretador no manifesto, em vez de deixar o "
                             "Claude escolher pelo PATH.")
    raise SystemExit(empacotar(parser.parse_args().python))
