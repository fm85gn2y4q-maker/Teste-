"""Publica o Ementário num endereço HTTPS público, para o ChatGPT alcançar.

O ChatGPT só conversa com servidor remoto: ele não enxerga `localhost`. Este
módulo levanta um túnel do Cloudflare e o servidor por trás dele, na ordem
certa — o endereço público só é conhecido depois que o túnel sobe, e o
servidor precisa declará-lo para aceitar requisições vindas de fora.

    python -m ementario.publicar

Imprime a URL a colar no ChatGPT e fica no ar até Ctrl+C.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from queue import Empty, Queue

# O instalador do Windows não põe o cloudflared no PATH da sessão corrente.
_CAMINHOS = (
    r"C:\Program Files (x86)\cloudflared\cloudflared.exe",
    r"C:\Program Files\cloudflared\cloudflared.exe",
)
_RE_URL = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")


def achar_cloudflared() -> str | None:
    return shutil.which("cloudflared") or next(
        (c for c in _CAMINHOS if Path(c).exists()), None
    )


def _drenar(fluxo, fila: Queue) -> None:
    for linha in iter(fluxo.readline, ""):
        fila.put(linha)
    fluxo.close()


def publicar(porta: int = 8765, espera_seg: int = 40) -> int:
    executavel = achar_cloudflared()
    if not executavel:
        print(
            "cloudflared não encontrado. Instale com:\n"
            "  winget install --id Cloudflare.cloudflared",
            file=sys.stderr,
        )
        return 1

    raiz = Path(__file__).resolve().parent.parent
    tunel = subprocess.Popen(
        [executavel, "tunnel", "--url", f"http://127.0.0.1:{porta}"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace", bufsize=1,
    )

    fila: Queue = Queue()
    threading.Thread(target=_drenar, args=(tunel.stdout, fila), daemon=True).start()

    print("Levantando o túnel…", file=sys.stderr)
    url = None
    limite = time.monotonic() + espera_seg
    while time.monotonic() < limite and url is None:
        try:
            achado = _RE_URL.search(fila.get(timeout=1))
        except Empty:
            continue
        if achado:
            url = achado.group(0)

    if url is None:
        tunel.terminate()
        print("O túnel não devolveu um endereço a tempo.", file=sys.stderr)
        return 1

    dominio = url.removeprefix("https://")
    servidor = subprocess.Popen(
        [sys.executable, "-m", "ementario", "--http",
         "--porta", str(porta), "--dominio", dominio],
        cwd=raiz,
        env={**os.environ, "PYTHONPATH": str(raiz), "PYTHONUTF8": "1"},
    )
    time.sleep(6)

    print("\n" + "─" * 68)
    print("  Ementário publicado. No ChatGPT, em Configurações → Conectores,")
    print("  adicione um conector com esta URL:\n")
    print(f"      {url}/mcp\n")
    print("  O endereço vale enquanto esta janela estiver aberta; ao reabrir,")
    print("  o Cloudflare sorteia outro. Ctrl+C encerra tudo.")
    print("─" * 68 + "\n", flush=True)

    try:
        while True:
            if servidor.poll() is not None or tunel.poll() is not None:
                print("Um dos processos encerrou; derrubando o outro.", file=sys.stderr)
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nEncerrando…", file=sys.stderr)
    finally:
        for processo in (servidor, tunel):
            if processo.poll() is None:
                processo.terminate()
    return 0


if __name__ == "__main__":
    raise SystemExit(publicar())
