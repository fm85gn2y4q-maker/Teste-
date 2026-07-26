"""Empacota o Ementário como extensão do Claude Desktop (.mcpb).

Plano B para quando o conector HTTP não estiver disponível na conta: a
extensão roda o servidor localmente por stdio, instalada com um duplo clique,
sem túnel e sem depender do PC estar publicando nada.

O pacote leva as dependências junto (`server/lib`), porque o Claude Desktop
não instala nada: só executa o que está dentro. Leva também o acervo, para a
extensão funcionar sozinha.

    python empacotar_mcpb.py

Gera `dist/ementario.mcpb`.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
CONSTRUCAO = RAIZ / "build" / "mcpb"
DESTINO = RAIZ / "dist" / "ementario.mcpb"
BANCO = RAIZ / "dados" / "tcerj.sqlite"

ENTRADA = '''"""Ponto de entrada da extensão: sobe o Ementário por stdio."""
import os
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
# As dependências viajam dentro do pacote; o Claude Desktop não instala nada.
sys.path.insert(0, str(AQUI / "lib"))
sys.path.insert(0, str(AQUI))

os.environ.setdefault("EMENTARIO_BANCO", str(AQUI.parent / "dados" / "tcerj.sqlite"))

from ementario.servidor import construir  # noqa: E402

construir().run(transport="stdio")
'''

MANIFESTO = {
    "manifest_version": "0.2",
    "name": "ementario",
    "display_name": "Ementário",
    "version": "0.1.0",
    "description": "Jurisprudência do TCE-RJ: acórdãos, súmulas e respostas a consulta.",
    "long_description": (
        "Consulta o acervo de jurisprudência do Tribunal de Contas do Estado do "
        "Rio de Janeiro coletado do portal público — ementas de acórdãos, "
        "súmulas, respostas a consulta e questões de ordem. Cada resultado traz "
        "a citação no formato de peça e o link do inteiro teor para conferência."
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
    "tools": [
        {"name": "pesquisar_jurisprudencia",
         "description": "Pesquisa a jurisprudência do TCE-RJ por palavras da ementa."},
        {"name": "obter_documento",
         "description": "Devolve a ementa completa de um documento localizado."},
        {"name": "listar_documentos",
         "description": "Lista documentos por espécie, ano ou relator."},
        {"name": "cobertura_do_acervo",
         "description": "Volumes, período, relatores e limites da base."},
        {"name": "search", "description": "Busca compatível com pesquisa profunda."},
        {"name": "fetch", "description": "Recupera um documento pelo identificador."},
    ],
    "keywords": ["jurisprudência", "TCE-RJ", "direito", "contas públicas"],
    # `compatibility` fica de fora de propósito. É opcional, e foi o único
    # ponto que o Claude Desktop recusou ("Unrecognized key(s): python_version").
    # Sem um validador funcionando aqui para conferir a forma correta, declarar
    # menos é mais seguro do que chutar outra chave e falhar de novo na
    # instalação — que é onde o erro aparece.
}


def validar(pasta: Path) -> bool:
    """Passa o manifesto pelo validador oficial, se houver Node por perto.

    Empacotar não prova nada: um manifesto com uma chave fora do lugar zipa
    igual e só falha na hora de instalar, com uma mensagem que aparece na tela
    do usuário e não no build.

    Validador indisponível não é manifesto inválido: se o `npx` não roda, o que
    se sabe é que não se sabe — o pacote sai, com aviso.
    """
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if not npx:
        print("  aviso: npx ausente, manifesto NÃO validado.")
        return True

    resultado = subprocess.run(
        [npx, "--yes", "@anthropic-ai/mcpb", "validate", str(pasta / "manifest.json")],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    saida = (resultado.stdout + resultado.stderr).strip()
    if resultado.returncode == 0:
        print("  manifesto válido.")
        return True

    veredito = any(
        marca in saida.lower()
        for marca in ("invalid manifest", "unrecognized key", "validation")
    )
    if veredito:
        print("  " + "\n  ".join(saida.splitlines()[-8:]))
        return False

    print("  aviso: o validador não pôde ser executado; manifesto NÃO validado.")
    return True


def empacotar() -> int:
    if not BANCO.exists():
        print(f"Acervo não encontrado em {BANCO}. Rode a coleta antes.", file=sys.stderr)
        return 1

    if CONSTRUCAO.exists():
        shutil.rmtree(CONSTRUCAO)
    servidor = CONSTRUCAO / "server"
    servidor.mkdir(parents=True)

    print("Copiando o pacote…")
    shutil.copytree(
        RAIZ / "ementario", servidor / "ementario",
        ignore=shutil.ignore_patterns("__pycache__", "publicar.py"),
    )
    (servidor / "main.py").write_text(ENTRADA, encoding="utf-8")

    print("Instalando as dependências dentro do pacote…")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--quiet", "--target",
         str(servidor / "lib"), "mcp>=1.28"],
        check=True,
    )

    print("Copiando o acervo…")
    (CONSTRUCAO / "dados").mkdir()
    shutil.copy2(BANCO, CONSTRUCAO / "dados" / "tcerj.sqlite")

    (CONSTRUCAO / "manifest.json").write_text(
        json.dumps(MANIFESTO, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

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

    tamanho = DESTINO.stat().st_size / 1024 / 1024
    print(f"\n{DESTINO}  ({tamanho:.1f} MB)")
    print("Instale arrastando o arquivo para Configurações → Extensões do Claude.")
    return 0


if __name__ == "__main__":
    raise SystemExit(empacotar())
