from datetime import date, time

import pytest
from django.db.models import Count

from escolas.models import Escola, EscolaProblematica, TipoProblematica
from visitas.models import RondaVisita

pytestmark = pytest.mark.django_db


@pytest.fixture
def escolas():
    return [
        Escola.objects.create(
            nome="Escola Municipal Horizonte",
            polo=1,
            endereco="Rua das Acácias, 100",
        ),
        Escola.objects.create(
            nome="Escola Municipal Aurora",
            polo=2,
            endereco="Rua Secundária, 20",
        ),
        Escola.objects.create(
            nome="Escola Municipal Sem Visita",
            polo=3,
            endereco="Rua Terceira, 30",
        ),
    ]


def criar_visita(escola, dia, horario):
    """Cria uma visita simples para os cálculos dos indicadores."""
    return RondaVisita.objects.create(
        escola=escola,
        equipe="A",
        data_visita=date(2026, 10, dia),
        horario=time(*horario),
    )


def test_relacoes_permitem_contar_escolas_visitadas_sem_duplicidade(escolas):
    """Valida a contagem distinta de escolas que possuem visitas."""
    criar_visita(escolas[0], 19, (8, 0))
    criar_visita(escolas[0], 20, (9, 0))
    criar_visita(escolas[1], 20, (10, 0))

    total = Escola.objects.filter(visitas__isnull=False).distinct().count()

    assert total == 2


def test_problematicas_podem_ser_agrupadas_por_frequencia(escolas):
    """Valida o agrupamento das problemáticas mais registradas."""
    vandalismo = TipoProblematica.objects.create(nome="Vandalismo")
    iluminacao = TipoProblematica.objects.create(nome="Iluminação insuficiente")
    EscolaProblematica.objects.create(
        escola=escolas[0], tipo_problematica=vandalismo
    )
    EscolaProblematica.objects.create(
        escola=escolas[1], tipo_problematica=vandalismo
    )
    EscolaProblematica.objects.create(
        escola=escolas[2], tipo_problematica=iluminacao
    )

    resultado = list(
        EscolaProblematica.objects.values("tipo_problematica__nome")
        .annotate(total=Count("id"))
        .order_by("-total", "tipo_problematica__nome")
    )

    assert resultado == [
        {"tipo_problematica__nome": "Vandalismo", "total": 2},
        {"tipo_problematica__nome": "Iluminação insuficiente", "total": 1},
    ]


def test_contagens_refletem_novos_registros(escolas):
    """Valida que as consultas mudem quando novos registros são criados."""
    assert RondaVisita.objects.count() == 0
    assert EscolaProblematica.objects.count() == 0

    criar_visita(escolas[0], 20, (9, 30))
    tipo = TipoProblematica.objects.create(nome="Acesso inseguro")
    EscolaProblematica.objects.create(
        escola=escolas[0], tipo_problematica=tipo
    )

    assert RondaVisita.objects.count() == 1
    assert EscolaProblematica.objects.count() == 1
