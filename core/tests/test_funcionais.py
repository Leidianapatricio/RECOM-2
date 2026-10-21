from datetime import date, time

import pytest
from django.urls import reverse

from escolas.models import Escola, EscolaProblematica, TipoProblematica
from usuarios.models import Usuario
from visitas.models import RondaVisita

pytestmark = pytest.mark.django_db


@pytest.fixture
def coordenador(django_user_model):
    conta = django_user_model.objects.create_user(
        username="10001",
        password="senha-segura-123",
    )
    Usuario.objects.create(
        user=conta,
        nome="Coordenador de Testes",
        matricula="10001",
        perfil="COORDENADOR",
        primeiro_acesso=False,
    )
    return conta


@pytest.fixture
def cliente_coordenador(client, coordenador):
    client.force_login(coordenador)
    return client


@pytest.fixture
def cenario_indicadores():
    escolas = [
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
    RondaVisita.objects.create(
        escola=escolas[0],
        equipe="A",
        data_visita=date(2026, 10, 19),
        horario=time(8, 0),
    )
    RondaVisita.objects.create(
        escola=escolas[0],
        equipe="B",
        data_visita=date(2026, 10, 20),
        horario=time(9, 0),
    )
    RondaVisita.objects.create(
        escola=escolas[1],
        equipe="C",
        data_visita=date(2026, 10, 20),
        horario=time(10, 0),
    )
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
    return escolas


def test_ca07_1_ca07_3_ca07_5_indicadores_correspondem_aos_registros(
    cliente_coordenador, cenario_indicadores
):
    """CA07.1, CA07.3 e CA07.5: valida os totais calculados pelo sistema."""
    response = cliente_coordenador.get(reverse("core:dashboard_coordenador"))

    assert response.status_code == 200
    assert response.context["total_escolas"] == 3
    assert response.context["total_visitas"] == 3
    assert response.context["total_problematicas"] == 3


def test_ca07_2_apresenta_quantidade_de_escolas_com_visitas(
    cliente_coordenador, cenario_indicadores
):
    """CA07.2: valida a quantidade distinta de escolas visitadas."""
    response = cliente_coordenador.get(reverse("core:dashboard_coordenador"))

    assert "escolas_com_visitas" in response.context
    assert response.context["escolas_com_visitas"] == 2
    assert "Escolas Visitadas" in response.content.decode()


def test_ca07_4_apresenta_principais_problematicas(
    cliente_coordenador, cenario_indicadores
):
    """CA07.4: valida os tipos de problemática ordenados por frequência."""
    response = cliente_coordenador.get(reverse("core:dashboard_coordenador"))

    resultado = list(response.context["problematicas_por_tipo"])
    assert resultado == [
        {"tipo_problematica__nome": "Vandalismo", "total": 2},
        {"tipo_problematica__nome": "Iluminação insuficiente", "total": 1},
    ]
    conteudo = response.content.decode()
    assert "Vandalismo" in conteudo
    assert "Iluminação insuficiente" in conteudo


def test_ca07_6_atualizacao_reflete_novos_registros(cliente_coordenador):
    """CA07.6: valida a atualização após escola, visita e problemática."""
    url = reverse("core:dashboard_coordenador")
    inicial = cliente_coordenador.get(url)
    assert inicial.context["total_escolas"] == 0
    assert inicial.context["total_visitas"] == 0

    escola = Escola.objects.create(
        nome="Escola Municipal Nova",
        polo=1,
        endereco="Rua Nova, 10",
    )
    RondaVisita.objects.create(
        escola=escola,
        equipe="A",
        data_visita=date(2026, 10, 21),
        horario=time(9, 0),
    )
    tipo = TipoProblematica.objects.create(nome="Muro danificado")
    EscolaProblematica.objects.create(escola=escola, tipo_problematica=tipo)

    atualizado = cliente_coordenador.get(url)
    assert atualizado.context["total_escolas"] == 1
    assert atualizado.context["total_visitas"] == 1
    assert atualizado.context["total_problematicas"] == 1
    assert list(atualizado.context["problematicas_por_tipo"]) == [
        {"tipo_problematica__nome": "Muro danificado", "total": 1}
    ]


def test_ca07_7_indicadores_sem_dados_apresentam_zero_ou_mensagem(
    cliente_coordenador,
):
    """CA07.7: valida zeros e mensagens quando não existem registros."""
    response = cliente_coordenador.get(reverse("core:dashboard_coordenador"))

    assert response.context["total_escolas"] == 0
    assert response.context["total_visitas"] == 0
    assert response.context["total_problematicas"] == 0
    conteudo = response.content.decode()
    assert "Nenhuma escola encontrada." in conteudo
    assert "Nenhuma problemática cadastrada." in conteudo
