from datetime import date, time

import pytest
from django.urls import reverse

from escolas.models import Escola
from visitas.models import RondaVisita

pytestmark = pytest.mark.django_db


@pytest.fixture
def administrador(django_user_model):
    return django_user_model.objects.create_superuser(
        username="admin_visitas",
        password="senha-segura-123",
        email="admin.visitas@example.com",
    )


@pytest.fixture
def cliente_autenticado(client, administrador):
    client.force_login(administrador)
    return client


@pytest.fixture
def escola():
    return Escola.objects.create(
        nome="Escola Municipal Horizonte",
        polo=1,
        endereco="Rua das Acácias, 100",
    )


@pytest.fixture
def dados_visita(escola):
    return {
        "escola": str(escola.pk),
        "equipe": "A",
        "data_visita": "2026-10-20",
        "horario": "09:30",
        "tipo_visita": "ROTINA",
        "situacao": "COM_ALTERACAO",
        "relato": "Portão lateral danificado.",
        "orientacoes": "A gestão foi orientada a solicitar o reparo.",
    }


def test_ca05_1_escola_e_obrigatoria_para_registrar_visita(
    cliente_autenticado, dados_visita
):
    """CA05.1: impede o registro e indica quando a escola não foi informada."""
    dados = dados_visita.copy()
    dados["escola"] = ""

    response = cliente_autenticado.post(
        reverse("visitas:cadastrar_visita"), dados
    )

    assert response.status_code == 200
    assert "Este campo é obrigatório." in response.context["form"].errors["escola"]
    assert RondaVisita.objects.count() == 0


def test_ca05_2_formulario_permite_informar_data_e_horario(
    cliente_autenticado
):
    """CA05.2: valida os campos de data e horário da visita."""
    response = cliente_autenticado.get(reverse("visitas:cadastrar_visita"))

    campos = response.context["form"].fields
    assert campos["data_visita"].required
    assert campos["horario"].required


def test_ca05_3_formulario_permite_identificar_equipe(cliente_autenticado):
    """CA05.3: valida a seleção da equipe responsável pela visita."""
    response = cliente_autenticado.get(reverse("visitas:cadastrar_visita"))

    escolhas = list(response.context["form"].fields["equipe"].choices)
    assert ("A", "Equipe A") in escolhas
    assert ("EXTRA", "Equipe Extraordinário") in escolhas


def test_ca05_4_formulario_permite_descrever_situacao(cliente_autenticado):
    """CA05.4: valida os campos de situação e relato da visita."""
    response = cliente_autenticado.get(reverse("visitas:cadastrar_visita"))

    campos = response.context["form"].fields
    assert "situacao" in campos
    assert "relato" in campos


def test_ca05_5_formulario_permite_registrar_providencias(cliente_autenticado):
    """CA05.5: valida o campo destinado às providências adotadas."""
    response = cliente_autenticado.get(reverse("visitas:cadastrar_visita"))

    assert "orientacoes" in response.context["form"].fields


def test_ca05_6_formulario_disponibiliza_observacoes_complementares(
    cliente_autenticado,
):
    """CA05.6: valida o campo de observações complementares."""
    response = cliente_autenticado.get(reverse("visitas:cadastrar_visita"))

    assert "observacoes" in response.context["form"].fields


def test_ca05_7_ca05_8_registro_fica_vinculado_e_disponivel_no_historico(
    cliente_autenticado, escola, dados_visita
):
    """CA05.7 e CA05.8: valida o vínculo e a inclusão no histórico."""
    response = cliente_autenticado.post(
        reverse("visitas:cadastrar_visita"), dados_visita
    )

    assert response.status_code == 302
    assert response.url == reverse(
        "escolas:detalhe_escola", kwargs={"pk": escola.pk}
    )
    visita = RondaVisita.objects.get()
    assert visita.escola == escola

    historico = cliente_autenticado.get(response.url)
    conteudo = historico.content.decode()
    assert visita.get_equipe_display() in conteudo
    assert visita.relato in conteudo
    assert visita.orientacoes in conteudo


def test_ca06_1_ca06_2_ca06_5_historico_exibe_dados_apenas_da_escola(
    cliente_autenticado, escola
):
    """CA06.1, CA06.2 e CA06.5: valida dados e vínculo no histórico."""
    outra_escola = Escola.objects.create(
        nome="Escola Municipal Aurora",
        polo=2,
        endereco="Rua Secundária, 20",
    )
    exibida = RondaVisita.objects.create(
        escola=escola,
        equipe="B",
        data_visita=date(2026, 10, 20),
        horario=time(14, 15),
        situacao="COM_ALTERACAO",
        relato="Vidro quebrado na entrada.",
        orientacoes="Área isolada e gestão comunicada.",
    )
    RondaVisita.objects.create(
        escola=outra_escola,
        equipe="C",
        data_visita=date(2026, 10, 20),
        horario=time(15, 0),
        relato="Registro de outra escola.",
    )

    response = cliente_autenticado.get(
        reverse("escolas:detalhe_escola", kwargs={"pk": escola.pk})
    )

    assert response.status_code == 200
    conteudo = response.content.decode()
    for valor in (
        "20/10/2026",
        "14:15",
        exibida.get_equipe_display(),
        exibida.get_situacao_display(),
        exibida.relato,
        exibida.orientacoes,
    ):
        assert valor in conteudo
    assert "Registro de outra escola." not in conteudo


def test_ca06_3_historico_apresenta_visitas_em_ordem_cronologica(
    cliente_autenticado, escola
):
    """CA06.3: valida a ordem da visita mais recente para a mais antiga."""
    antiga = RondaVisita.objects.create(
        escola=escola,
        equipe="A",
        data_visita=date(2026, 10, 19),
        horario=time(8, 0),
        relato="VISITA_ANTIGA",
    )
    recente = RondaVisita.objects.create(
        escola=escola,
        equipe="B",
        data_visita=date(2026, 10, 20),
        horario=time(9, 0),
        relato="VISITA_RECENTE",
    )

    response = cliente_autenticado.get(
        reverse("escolas:detalhe_escola", kwargs={"pk": escola.pk})
    )

    visitas = list(response.context["visitas"])
    assert visitas == [recente, antiga]
    conteudo = response.content.decode()
    assert conteudo.index("VISITA_RECENTE") < conteudo.index("VISITA_ANTIGA")


def test_ca06_4_historico_sem_visitas_informa_inexistencia(
    cliente_autenticado, escola
):
    """CA06.4: valida a mensagem para escola sem visitas registradas."""
    response = cliente_autenticado.get(
        reverse("escolas:detalhe_escola", kwargs={"pk": escola.pk})
    )

    assert response.status_code == 200
    assert "Nenhuma visita registrada para esta escola." in response.content.decode()
