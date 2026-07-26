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
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
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


def porta_ocupada(porta: int) -> bool:
    with socket.socket() as s:
        s.settimeout(1.0)
        return s.connect_ex(("127.0.0.1", porta)) == 0


def esperar_servidor(porta: int, processo, espera_seg: int = 30) -> bool:
    """Só devolve True quando o servidor de fato responde.

    Anunciar o endereço sem confirmar isso é pior do que falhar: o túnel sobe
    de qualquer jeito, e quem cola a URL no ChatGPT recebe um 502 sem pista do
    motivo.
    """
    limite = time.monotonic() + espera_seg
    pedido = urllib.request.Request(
        f"http://127.0.0.1:{porta}/mcp",
        method="POST",
        data=b'{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}',
        headers={"Content-Type": "application/json",
                 "Accept": "application/json, text/event-stream"},
    )
    while time.monotonic() < limite:
        if processo.poll() is not None:
            return False
        try:
            with urllib.request.urlopen(pedido, timeout=3):
                return True
        except urllib.error.HTTPError:
            return True  # respondeu: está de pé, ainda que recusando o corpo
        except (urllib.error.URLError, OSError):
            time.sleep(1)
    return False


def publicar(porta: int = 8765, espera_seg: int = 40) -> int:
    executavel = achar_cloudflared()
    if not executavel:
        print(
            "cloudflared não encontrado. Instale com:\n"
            "  winget install --id Cloudflare.cloudflared",
            file=sys.stderr,
        )
        return 1

    if porta_ocupada(porta):
        print(
            f"A porta {porta} já está em uso — provavelmente por uma execução\n"
            f"anterior que não foi encerrada. Feche-a, ou use outra porta:\n"
            f"  python -m ementario.publicar --porta {porta + 1}",
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

    if not esperar_servidor(porta, servidor):
        for processo in (servidor, tunel):
            if processo.poll() is None:
                processo.terminate()
        print(
            "\nO servidor não subiu; nada seria publicado nesse endereço.\n"
            "Confira as mensagens acima.",
            file=sys.stderr,
        )
        return 1

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


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="python -m ementario.publicar",
        description="Publica o Ementário num endereço HTTPS público (para o ChatGPT).",
    )
    parser.add_argument("--porta", type=int, default=8765)
    args = parser.parse_args(argv)
    return publicar(porta=args.porta)


if __name__ == "__main__":
    raise SystemExit(main())
