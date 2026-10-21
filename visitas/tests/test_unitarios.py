from datetime import date, time

import pytest

from escolas.models import Escola
from visitas.forms import RondaVisitaForm
from visitas.models import RondaVisita

pytestmark = pytest.mark.django_db


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


def test_modelo_de_visita_define_valores_e_representacao(escola):
    """Valida valores padrão e a representação textual de uma visita."""
    visita = RondaVisita.objects.create(
        escola=escola,
        equipe="A",
        data_visita=date(2026, 10, 20),
        horario=time(9, 30),
    )

    assert visita.tipo_visita == "ROTINA"
    assert visita.situacao == "SEM_ALTERACAO"
    assert str(visita) == (
        "Escola Municipal Horizonte - 20/10/2026 - Equipe A"
    )


def test_formulario_de_visita_aceita_dados_validos(dados_visita, escola):
    """Valida a conversão dos dados válidos recebidos pelo formulário."""
    formulario = RondaVisitaForm(data=dados_visita)

    assert formulario.is_valid()
    assert formulario.cleaned_data["escola"] == escola
    assert formulario.cleaned_data["data_visita"] == date(2026, 10, 20)
    assert formulario.cleaned_data["horario"] == time(9, 30)


@pytest.mark.parametrize(
    "campo",
    ["escola", "equipe", "data_visita", "horario", "tipo_visita", "situacao"],
)
def test_formulario_de_visita_rejeita_campos_obrigatorios_vazios(
    dados_visita, campo
):
    """Valida a obrigatoriedade dos dados essenciais da visita."""
    dados = dados_visita.copy()
    dados[campo] = ""

    formulario = RondaVisitaForm(data=dados)

    assert not formulario.is_valid()
    assert campo in formulario.errors


def test_formulario_disponibiliza_somente_escolas_ativas():
    """Valida que uma nova visita só possa selecionar escola ativa."""
    escola_ativa = Escola.objects.create(
        nome="Escola Ativa", polo=1, endereco="Rua Um, 10"
    )
    Escola.objects.create(
        nome="Escola Inativa", polo=2, endereco="Rua Dois, 20", ativa=False
    )

    formulario = RondaVisitaForm()

    assert list(formulario.fields["escola"].queryset) == [escola_ativa]


def test_historico_relaciona_visitas_a_escola_em_ordem_decrescente(escola):
    """Valida o vínculo e a ordem da visita mais recente para a mais antiga."""
    antiga = RondaVisita.objects.create(
        escola=escola,
        equipe="A",
        data_visita=date(2026, 10, 19),
        horario=time(14, 0),
    )
    recente = RondaVisita.objects.create(
        escola=escola,
        equipe="B",
        data_visita=date(2026, 10, 20),
        horario=time(8, 0),
    )

    assert list(escola.visitas.all()) == [recente, antiga]
