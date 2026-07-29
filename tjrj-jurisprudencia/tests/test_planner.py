from datetime import date

from tjrj.crawl.planner import Fatia, Lacuna, planejar


def _contador(mapa_por_dia: dict[date, int]):
    """Contador de mentira: soma os acórdãos dos dias da fatia, com facetas."""

    def contar(f: Fatia) -> int:
        total = sum(
            n for d, n in mapa_por_dia.items() if f.inicio <= d <= f.fim
        )
        if "orgao_julgador" in f.facetas:
            total = total // 4  # cada órgão leva 1/4 do movimento
        return total

    return contar


def test_janela_pequena_nao_e_fatiada():
    dias = {date(2024, 1, d): 10 for d in range(1, 32)}
    fatias = list(planejar(date(2024, 1, 1), date(2024, 1, 31), _contador(dias), teto=1000))
    assert len(fatias) == 1
    assert fatias[0].inicio == date(2024, 1, 1) and fatias[0].fim == date(2024, 1, 31)


def test_fatia_ate_caber_no_teto():
    dias = {date(2024, 1, d): 100 for d in range(1, 32)}
    contar = _contador(dias)
    fatias = list(planejar(date(2024, 1, 1), date(2024, 1, 31), contar, teto=500))
    for f in fatias:
        assert contar(f) <= 450  # teto * margem 0.9
    assert _cobertura(fatias) == set(dias)


def test_cobertura_sem_buraco_nem_sobreposicao():
    dias = {date(2024, 3, d): 60 * (d % 7 + 1) for d in range(1, 32)}
    fatias = list(planejar(date(2024, 3, 1), date(2024, 3, 31), _contador(dias), teto=300))
    coberto = [d for f in fatias for d in _dias(f)]
    assert sorted(coberto) == sorted(dias)  # nenhum dia repetido, nenhum faltando


def test_dia_isolado_acima_do_teto_vira_faceta():
    dias = {date(2024, 5, 6): 5000}
    fatias = list(
        planejar(
            date(2024, 5, 6),
            date(2024, 5, 6),
            _contador(dias),
            teto=2000,
            valores_de_faceta=lambda chave, fatia: ["1a Camara Civel", "2a Camara Civel",
                                                    "3a Camara Civel", "4a Camara Civel"],
        )
    )
    assert len(fatias) == 4
    assert {f.facetas["orgao_julgador"] for f in fatias} == {
        "1a Camara Civel", "2a Camara Civel", "3a Camara Civel", "4a Camara Civel"
    }


def test_lacuna_e_registrada_quando_nao_ha_como_fatiar():
    dias = {date(2024, 5, 6): 99999}
    lacunas: list[Lacuna] = []
    fatias = list(
        planejar(date(2024, 5, 6), date(2024, 5, 6), _contador(dias), teto=100, lacunas=lacunas)
    )
    assert len(fatias) == 1  # coleta o truncado mesmo assim
    assert len(lacunas) == 1
    assert lacunas[0].total_declarado == 99999


def test_dias_vazios_nao_geram_requisicao():
    dias = {date(2024, 1, 15): 10}
    fatias = list(planejar(date(2024, 1, 1), date(2024, 1, 31), _contador(dias), teto=5))
    assert [f for f in fatias if not _dias(f) & {date(2024, 1, 15)}] == []


def _dias(f: Fatia) -> set:
    from datetime import timedelta

    return {f.inicio + timedelta(days=i) for i in range(f.dias)}


def _cobertura(fatias) -> set:
    return {d for f in fatias for d in _dias(f)}
