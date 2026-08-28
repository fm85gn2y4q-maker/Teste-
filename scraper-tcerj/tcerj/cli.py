"""Interface de linha de comando do coletor de jurisprudência do TCE-RJ."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

from .armazenamento import Armazenamento, exportar_csv, exportar_jsonl
from .config import Config
from .http import ServidorRecusando
from .modelos import ROTULOS, TipoDocumento

log = logging.getLogger("tcerj")


def _configurar_log(verboso: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verboso else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)


def _tipo(valor: str | None) -> TipoDocumento | None:
    if not valor or valor == "todos":
        return None
    tipo = TipoDocumento.de_texto(valor)
    if tipo is TipoDocumento.INDEFINIDO:
        raise argparse.ArgumentTypeError(
            f"Tipo desconhecido: {valor}. Use um de: "
            + ", ".join(t.value for t in TipoDocumento if t is not TipoDocumento.INDEFINIDO)
        )
    return tipo


# ---------------------------------------------------------------------------
# Comandos
# ---------------------------------------------------------------------------


def cmd_descobrir(args: argparse.Namespace) -> int:
    from .descoberta import descobrir, inferir_api

    config = Config.carregar(args.config)
    relatorio = asyncio.run(
        descobrir(config, termo=args.termo, headless=not args.mostrar_navegador)
    )

    destino = Path(args.saida)
    relatorio.salvar(destino)
    print(f"Relatório de descoberta: {destino}")
    print(f"Portais visitados: {len(relatorio.portais_visitados)}")
    print(f"Chamadas JSON capturadas: {len(relatorio.chamadas)}")

    for erro in relatorio.erros:
        print(f"  aviso: {erro}", file=sys.stderr)

    melhor = relatorio.melhor()
    if melhor is None:
        print(
            "\nNenhum endpoint de listagem reconhecido.\n"
            "Abra o relatório para inspecionar as chamadas capturadas, ou rode\n"
            "novamente com --mostrar-navegador e faça a busca manualmente.",
            file=sys.stderr,
        )
        return 1

    print(f"\nEndpoint mais provável: {melhor.metodo} {melhor.url}")
    print(f"  pontuação: {melhor.pontuacao}")
    print(f"  itens por página: {melhor.quantidade_itens}")
    print(f"  caminho da lista: {melhor.caminho_itens or '(raiz)'}")

    config.api = inferir_api(melhor, termo=args.termo)
    config.backend = "api"
    caminho_config = Path(args.escrever_config or args.config or "config.json")
    config.salvar(caminho_config)
    print(f"\nConfiguração gravada em {caminho_config} (backend=api).")
    print("Revise o arquivo e rode: python -m tcerj coletar")
    return 0


def cmd_coletar(args: argparse.Namespace) -> int:
    from .pipeline import executar

    config = Config.carregar(args.config)
    if args.backend:
        config.backend = args.backend
    if args.intervalo is not None:
        config.intervalo_seg = args.intervalo

    banco = Path(args.banco or Path(config.diretorio_saida) / "tcerj.sqlite")

    def progresso(novos: int, atualizados: int) -> None:
        print(f"  ... {novos} novos, {atualizados} atualizados", flush=True)

    with Armazenamento(banco) as armazenamento:
        novos, atualizados = asyncio.run(
            executar(
                config,
                armazenamento,
                termo=args.termo,
                tipo=_tipo(args.tipo),
                max_paginas=args.max_paginas,
                max_documentos=args.max_documentos,
                headless=not args.mostrar_navegador,
                ao_progresso=progresso,
            )
        )
        estatisticas = armazenamento.estatisticas()

    print(f"\nColeta concluída: {novos} novos, {atualizados} atualizados.")
    print(f"Banco: {banco}")
    print(f"Total acumulado: {estatisticas['total']}")
    return 0


def cmd_inteiro_teor(args: argparse.Namespace) -> int:
    from .inteiro_teor import coletar

    config = Config.carregar(args.config)
    if args.intervalo is not None:
        config.intervalo_seg = args.intervalo
    banco = Path(args.banco or Path(config.diretorio_saida) / "tcerj.sqlite")

    def progresso(documentos: int, paginas: int, falhas: int) -> None:
        print(f"  ... {documentos} documentos, {paginas} páginas, {falhas} falhas",
              flush=True)

    with Armazenamento(banco) as armazenamento:
        contagem = asyncio.run(
            coletar(
                config,
                armazenamento,
                tipo=_tipo(args.tipo),
                max_documentos=args.max_documentos,
                reverificar=args.reverificar,
                ao_progresso=progresso,
            )
        )
        resumo = armazenamento.estatisticas_inteiro_teor()
        pendentes = armazenamento.pendencias()

    print(f"\nNovos: {contagem['novos']} | atualizados: {contagem['atualizados']} "
          f"| inalterados: {contagem['inalterados']} | falhas: {contagem['falhas']}")
    print(f"Páginas gravadas nesta execução: {contagem['paginas']}")
    print(f"Acumulado: {resumo['documentos']} documentos, {resumo['paginas']} páginas, "
          f"{resumo['caracteres']:,} caracteres.")
    if pendentes:
        print(f"\nPendências registradas ({len(pendentes)}):")
        for p in pendentes[:10]:
            print(f"  {p['tipo']} {p['numero']}/{p['ano']}: {p['status_coleta']}")
    return 0


def cmd_consultas(args: argparse.Namespace) -> int:
    from .consultas import coletar

    config = Config.carregar(args.config)
    if args.intervalo is not None:
        config.intervalo_seg = args.intervalo
    banco = Path(args.banco or Path(config.diretorio_saida) / "tcerj.sqlite")

    def progresso(d: int, p: int, f: int) -> None:
        print(f"  ... {d} respostas, {p} páginas, {f} falhas", flush=True)

    with Armazenamento(banco) as armazenamento:
        c = asyncio.run(coletar(config, armazenamento,
                                max_documentos=args.max_documentos,
                                ao_progresso=progresso))
    print("\n" + f"Novas: {c['novos']} | páginas: {c['paginas']} "
          f"| falhas: {c['falhas']} | sem arquivo: {c['sem_arquivo']}")
    return 0


def cmd_descobrir_acordaos(args: argparse.Namespace) -> int:
    from .http import Cliente
    from .pesquisa_textual import TETO, descobrir, naturezas_de_pessoal, e_ato_de_pessoal

    config = Config.carregar(args.config)
    if args.intervalo is not None:
        config.intervalo_seg = args.intervalo
    banco = Path(args.banco or Path(config.diretorio_saida) / "tcerj.sqlite")

    def _fatias() -> list[tuple[str | None, str | None]]:
        """Os recortes de data a percorrer."""
        if not args.por_mes:
            return [(args.desde, args.ate)]
        if not (args.desde and args.ate):
            raise SystemExit("--por-mes exige --desde e --ate")
        import calendar
        ai, mi = int(args.desde[:4]), int(args.desde[5:7])
        af, mf = int(args.ate[:4]), int(args.ate[5:7])
        fatias = []
        while (ai, mi) <= (af, mf):
            ultimo = calendar.monthrange(ai, mi)[1]
            fatias.append((f"{ai}-{mi:02d}-01", f"{ai}-{mi:02d}-{ultimo:02d}"))
            mi += 1
            if mi > 12:
                ai, mi = ai + 1, 1
        return fatias

    descartadas = 0

    async def rodar(armazenamento) -> tuple[int, int, list[str]]:
        nonlocal descartadas
        novas = conhecidas = 0
        saturadas = []
        termos = args.termo or [""]
        async with Cliente(config) as cliente:
            excluidas = None
            if args.sem_pessoal:
                excluidas = await naturezas_de_pessoal(cliente)
                if not excluidas:
                    # Sem o catálogo o filtro vira silêncio: a busca voltaria
                    # completa e ninguém saberia que o recorte não se aplicou.
                    raise SystemExit(
                        "--sem-pessoal pediu o catálogo de naturezas e ele não "
                        "veio. Abortado: sem ele a coleta traria tudo, e o "
                        "resultado pareceria filtrado.")
                print(f"  excluindo {len(excluidas)} naturezas de pessoal",
                      flush=True)
            for desde, ate in _fatias():
                for termo in termos:
                    referencias, total = await descobrir(
                        cliente, termo, municipio=args.municipio,
                        ano_min=args.ano_min, ano_max=args.ano_max,
                        desde=desde, ate=ate,
                        naturezas_excluidas=excluidas,
                    )
                    if args.sem_atos_de_pessoal:
                        antes = len(referencias)
                        referencias = [r for r in referencias
                                       if not e_ato_de_pessoal(r.natureza)]
                        descartadas += antes - len(referencias)
                    n, c = armazenamento.registrar_descobertos(referencias)
                    novas += n
                    conhecidas += c
                    marca = " (NO TETO — recorte incompleto)" if total >= TETO else ""
                    rotulo = (desde[:7] if desde else "tudo") + (
                        f" {termo}" if termo else "")
                    print(f"  {rotulo}: {total} no servidor, "
                          f"{len(referencias)} lidos, {n} novos{marca}", flush=True)
                    if total >= TETO:
                        saturadas.append(rotulo)
        return novas, conhecidas, saturadas

    with Armazenamento(banco) as armazenamento:
        novas, conhecidas, saturadas = asyncio.run(rodar(armazenamento))
        pendentes = len(armazenamento.oficiais_sem_texto())

    print(f"\nDescobertos: {novas} novos, {conhecidas} já conhecidos.")
    print(f"Aguardando inteiro teor: {pendentes} documentos.")
    if saturadas:
        print("\nConsultas que bateram o teto e ficaram incompletas:")
        for termo in saturadas:
            print(f"  {termo}")
        print("Estreite o recorte (--ano-min/--ano-max, --municipio) e repita.")
    print("\nPara baixar: python -m tcerj -c config.json inteiro-teor")
    return 0


def cmd_reparar(args: argparse.Namespace) -> int:
    from .inteiro_teor import reparar

    config = Config.carregar(args.config)
    banco = Path(args.banco or Path(config.diretorio_saida) / "tcerj.sqlite")

    def progresso(documentos: int, paginas: int) -> None:
        print(f"  ... {documentos} documentos, {paginas} páginas", flush=True)

    with Armazenamento(banco) as armazenamento:
        resumo = reparar(armazenamento, ao_progresso=progresso)
        print(f"\nDocumentos oficiais: {resumo['documentos_oficiais']}")
        print(f"Páginas: {resumo['paginas_antes']} -> {resumo['paginas_depois']} "
              f"({resumo['paginas_antes'] - resumo['paginas_depois']} redundantes "
              f"eliminadas)")
        if args.compactar:
            print("Compactando o banco…")
            armazenamento.conexao.execute("INSERT INTO paginas_fts(paginas_fts) "
                                          "VALUES('optimize')")
            armazenamento.conexao.execute("INSERT INTO documentos_fts(documentos_fts) "
                                          "VALUES('optimize')")
            armazenamento.conexao.commit()
            armazenamento.conexao.execute("VACUUM")
    return 0


def cmd_exportar(args: argparse.Namespace) -> int:
    config = Config.carregar(args.config)
    banco = Path(args.banco or Path(config.diretorio_saida) / "tcerj.sqlite")
    if not banco.exists():
        print(f"Banco não encontrado: {banco}", file=sys.stderr)
        return 1

    with Armazenamento(banco) as armazenamento:
        documentos = armazenamento.listar(tipo=_tipo(args.tipo), ano=args.ano)
        destino = Path(args.saida)
        if args.formato == "csv":
            total = exportar_csv(documentos, destino)
        else:
            total = exportar_jsonl(documentos, destino)

    print(f"{total} documento(s) exportado(s) para {destino}")
    return 0


def cmd_buscar(args: argparse.Namespace) -> int:
    config = Config.carregar(args.config)
    banco = Path(args.banco or Path(config.diretorio_saida) / "tcerj.sqlite")
    if not banco.exists():
        print(f"Banco não encontrado: {banco}", file=sys.stderr)
        return 1

    with Armazenamento(banco) as armazenamento:
        resultados = armazenamento.buscar(args.termo, limite=args.limite)

    if not resultados:
        print("Nenhum documento encontrado.")
        return 0

    for documento in resultados:
        print(f"\n{documento.citacao}")
        if documento.ementa:
            resumo = documento.ementa[:280]
            print(f"  {resumo}{'…' if len(documento.ementa) > 280 else ''}")
        if documento.url:
            print(f"  {documento.url}")
    print(f"\n{len(resultados)} resultado(s).")
    return 0


def cmd_estatisticas(args: argparse.Namespace) -> int:
    config = Config.carregar(args.config)
    banco = Path(args.banco or Path(config.diretorio_saida) / "tcerj.sqlite")
    if not banco.exists():
        print(f"Banco não encontrado: {banco}", file=sys.stderr)
        return 1

    with Armazenamento(banco) as armazenamento:
        estatisticas = armazenamento.estatisticas()

    print(f"Total de documentos: {estatisticas.pop('total')}")
    for tipo, quantidade in estatisticas.items():
        rotulo = ROTULOS.get(TipoDocumento(tipo), tipo)
        print(f"  {rotulo:.<24} {quantidade}")
    return 0


def cmd_config_exemplo(args: argparse.Namespace) -> int:
    destino = Path(args.saida)
    Config().salvar(destino)
    print(f"Configuração padrão gravada em {destino}")
    return 0


# ---------------------------------------------------------------------------
# Analisador de argumentos
# ---------------------------------------------------------------------------


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m tcerj",
        description="Coletor da jurisprudência do TCE-RJ "
        "(acórdãos, súmulas, enunciados, deliberações e afins).",
    )
    parser.add_argument("-v", "--verboso", action="store_true", help="log detalhado")
    parser.add_argument("-c", "--config", help="arquivo de configuração JSON")
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser(
        "descobrir",
        help="abre o portal num navegador real e identifica o endpoint de dados",
    )
    p.add_argument("--termo", default="licitação", help="termo usado na busca-sonda")
    p.add_argument("--saida", default="descoberta.json", help="relatório de saída")
    p.add_argument("--escrever-config", help="onde gravar a configuração inferida")
    p.add_argument(
        "--mostrar-navegador", action="store_true", help="não usar modo headless"
    )
    p.set_defaults(func=cmd_descobrir)

    p = sub.add_parser("coletar", help="coleta os documentos e grava no banco")
    p.add_argument("--termo", help="termo de busca (vazio = tudo que a listagem trouxer)")
    p.add_argument("--tipo", help="acordao, sumula, enunciado, deliberacao, ... ou todos")
    p.add_argument("--banco", help="caminho do SQLite")
    p.add_argument("--backend", choices=("api", "navegador"), help="sobrescreve a config")
    p.add_argument("--max-paginas", type=int, default=50)
    p.add_argument("--max-documentos", type=int)
    p.add_argument("--intervalo", type=float, help="segundos entre requisições")
    p.add_argument("--mostrar-navegador", action="store_true")
    p.set_defaults(func=cmd_coletar)

    p = sub.add_parser(
        "inteiro-teor",
        help="baixa o PDF oficial dos documentos já coletados e guarda o texto "
             "por página",
    )
    p.add_argument("--tipo", help="restringe a espécie (padrão: todas)")
    p.add_argument("--max-documentos", type=int)
    p.add_argument("--intervalo", type=float, help="segundos entre requisições")
    p.add_argument("--banco")
    p.add_argument(
        "--reverificar",
        action="store_true",
        help="rebaixa também o que já está guardado, para conferir se mudou. "
             "O portal não oferece meio barato de checar isso, então é o "
             "mesmo custo de uma coleta — use quando houver motivo.",
    )
    p.set_defaults(func=cmd_inteiro_teor)

    p = sub.add_parser(
        "inteiro-teor-consultas",
        help="baixa o inteiro teor das Respostas a Consulta (têm arquivo próprio)")
    p.add_argument("--max-documentos", type=int)
    p.add_argument("--intervalo", type=float,
                   help="segundos entre requisições (servidor público)")
    p.add_argument("--banco")
    p.set_defaults(func=cmd_consultas)

    p = sub.add_parser(
        "descobrir-acordaos",
        help="acha acórdãos pela Pesquisa Textual, além da curadoria do "
             "Serviço de Jurisprudência",
    )
    p.add_argument("--termo", action="append",
                   help="expressão a procurar. Pode repetir. Aspas fazem busca "
                        "exata; ' E ', ' OU ' e ' -- ' são os operadores. "
                        "Omitido, varre o recorte inteiro sem filtrar palavra.")
    p.add_argument("--desde", help="data ISO da sessão mais antiga (2026-01-01)")
    p.add_argument("--ate", help="data ISO da sessão mais recente (2026-12-31)")
    p.add_argument("--sem-atos-de-pessoal", action="store_true",
                   help="descarta aposentadoria, pensão, admissão e afins. "
                        "São ~90% do que o Tribunal julga, não firmam tese, e "
                        "trazem nome de servidor com matrícula e proventos "
                        "para um acervo que existe para citar precedente.")
    p.add_argument("--sem-pessoal", action="store_true",
                   help="exclui registro de ato de pessoal (aposentadoria, "
                        "pensão, contratação por prazo determinado e afins). "
                        "Em 2026 são 91% dos acórdãos, sem tese para citar e "
                        "com nome e proventos de servidor no texto.")
    p.add_argument("--por-mes", action="store_true",
                   help="fatia o intervalo mês a mês. Um ano inteiro passa do "
                        "teto de 10.000 e volta truncado sem avisar; por mês, "
                        "a soma das fatias é demonstravelmente o conjunto.")
    p.add_argument("--municipio", type=int,
                   help="id do ente federativo (ex.: 93 = Mesquita)")
    p.add_argument("--ano-min", type=int, help="ano de sessão mais antigo")
    p.add_argument("--ano-max", type=int, help="ano de sessão mais recente")
    p.add_argument("--intervalo", type=float)
    p.add_argument("--banco")
    p.set_defaults(func=cmd_descobrir_acordaos)

    p = sub.add_parser(
        "reparar-inteiro-teor",
        help="reagrupa as páginas por documento oficial e repassa a limpeza, "
             "sem baixar nada de novo",
    )
    p.add_argument("--banco")
    p.add_argument("--compactar", action="store_true",
                   help="otimiza os índices e roda VACUUM ao final")
    p.set_defaults(func=cmd_reparar)

    p = sub.add_parser("exportar", help="exporta o acervo para JSONL ou CSV")
    p.add_argument("saida", help="arquivo de destino")
    p.add_argument("--formato", choices=("jsonl", "csv"), default="jsonl")
    p.add_argument("--tipo")
    p.add_argument("--ano", type=int)
    p.add_argument("--banco")
    p.set_defaults(func=cmd_exportar)

    p = sub.add_parser("buscar", help="busca textual no acervo já coletado")
    p.add_argument("termo")
    p.add_argument("--limite", type=int, default=20)
    p.add_argument("--banco")
    p.set_defaults(func=cmd_buscar)

    p = sub.add_parser("estatisticas", help="resumo do que já foi coletado")
    p.add_argument("--banco")
    p.set_defaults(func=cmd_estatisticas)

    p = sub.add_parser("config-exemplo", help="gera um arquivo de configuração padrão")
    p.add_argument("--saida", default="config.json")
    p.set_defaults(func=cmd_config_exemplo)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = construir_parser()
    args = parser.parse_args(argv)
    _configurar_log(args.verboso)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\nInterrompido. O progresso já gravado é preservado.", file=sys.stderr)
        return 130
    except ServidorRecusando as erro:
        # Código próprio: uma coleta longa costuma rodar destacada, e quem for
        # ler o registro depois precisa distinguir "o servidor mandou parar" de
        # um erro qualquer. Retomar sem antes conferir o portal é reincidir.
        print(f"\nCOLETA ENCERRADA PELO SERVIDOR\n{erro}", file=sys.stderr)
        return 75
    except (FileNotFoundError, ValueError) as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
