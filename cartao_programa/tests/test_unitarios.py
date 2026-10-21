from datetime import date, time

import pytest
from django.core.exceptions import ValidationError

from cartao_programa.forms import EfetivoViaturaForm, MissaoCartaoForm
from cartao_programa.models import (
    CartaoPrograma,
    EfetivoViatura,
    Equipe,
    MissaoCartao,
    Plantao,
    ViaturaPlantao,
)
from escolas.models import Escola
from usuarios.models import Usuario

pytestmark = pytest.mark.django_db

def criar_usuario(django_user_model, matricula, perfil, ativo=True):
    """Cria uma conta e seu perfil RECOM para os cenários unitários."""
    conta = django_user_model.objects.create_user(
        username=matricula,
        password="senha-segura-123",
    )
    return Usuario.objects.create(
        user=conta,
        nome=f"Usuário {matricula}",
        matricula=matricula,
        perfil=perfil,
        ativo=ativo,
        primeiro_acesso=False,
    )

@pytest.fixture
def coordenador(django_user_model):
    return criar_usuario(django_user_model, "20001", "COORDENADOR")

@pytest.fixture
def plantao():
    return Plantao.objects.create(
        data=date(2026, 10, 22),
        tipo_servico="ORDINARIO",
        observacoes="Planejamento do turno diurno.",
    )

@pytest.fixture
def equipe():
    return Equipe.objects.create(nome="Equipe Alfa")

@pytest.fixture
def viatura(plantao, equipe):
    return ViaturaPlantao.objects.create(
        plantao=plantao,
        identificacao="VTR-01",
        modelo="Duster",
        tipo_servico="ORDINARIO",
        equipe=equipe,
    )

@pytest.fixture
def cartao(plantao, coordenador):
    return CartaoPrograma.objects.create(
        plantao=plantao,
        coordenador=coordenador,
        observacoes="Priorizar os horários de entrada e saída.",
    )

@pytest.fixture
def escola():
    return Escola.objects.create(
        nome="Escola Municipal Horizonte",
        polo=1,
        endereco="Rua das Acácias, 100",
    )

def test_ca08_2_cartao_associa_data_do_plantao_e_coordenador(
    cartao, plantao, coordenador
):
    """CA08.2: valida a data de execução e o responsável pelo cartão."""
    assert cartao.plantao.data == date(2026, 10, 22)
    assert cartao.coordenador == coordenador
    assert str(cartao) == "Cartão Programa - 22/10/2026"

def test_ca08_2_responsavel_deve_ser_coordenador(
    django_user_model, plantao
):
    """CA08.2: rejeita um responsável que não tenha perfil de coordenador."""
    gcm = criar_usuario(django_user_model, "30001", "GCM")
    cartao = CartaoPrograma(plantao=plantao, coordenador=gcm)

    with pytest.raises(ValidationError) as erro:
        cartao.full_clean()

    assert "coordenador" in erro.value.message_dict

def test_ca08_3_cartao_permite_uma_ou_mais_missoes(
    cartao, viatura, escola
):
    """CA08.3: valida o relacionamento de múltiplas missões com o cartão."""
    primeira = MissaoCartao.objects.create(
        cartao=cartao,
        viatura=viatura,
        numero=1,
        escola=escola,
        endereco=escola.endereco,
        periodo="MANHA",
        horario_inicio=time(7, 0),
        horario_fim=time(8, 0),
        tipo_missao="SAIDA",
    )
    segunda = MissaoCartao.objects.create(
        cartao=cartao,
        viatura=viatura,
        numero=2,
        local="Praça Central",
        endereco="Avenida Principal, 50",
        periodo="TARDE",
        horario_inicio=time(14, 0),
        horario_fim=time(15, 0),
        tipo_missao="RONDAS_PB",
    )

    assert list(cartao.missoes.all()) == [primeira, segunda]

def test_ca08_4_formulario_disponibiliza_dados_operacionais_da_missao(cartao):
    """CA08.4: valida os campos de horário, local, endereço, efetivo e tipo."""
    formulario = MissaoCartaoForm(cartao=cartao)

    assert {
        "horario_inicio",
        "horario_fim",
        "local",
        "escola",
        "endereco",
        "viatura",
        "tipo_missao",
    } <= set(formulario.fields)

def test_ca08_5_tipos_contemplam_atividades_operacionais_obrigatorias():
    """CA08.5: exige Entrada, Saída, Visita de Rotina e Rondas com PB."""
    descricoes = {descricao for _, descricao in MissaoCartao.MISSAO_CHOICES}

    assert {
        "Entrada escolar",
        "Saída escolar",
        "Visita de rotina",
        "Rondas e PB",
    } <= descricoes

def test_ca08_6_efetivo_disponibiliza_somente_gcms_ativos(
    django_user_model, viatura
):
    """CA08.6: filtra o efetivo para apresentar somente GCMs ativos."""
    gcm_ativo = criar_usuario(django_user_model, "30001", "GCM")
    gcm_inativo = criar_usuario(
        django_user_model, "30002", "GCM", ativo=False
    )
    coordenador = criar_usuario(
        django_user_model, "20002", "COORDENADOR"
    )

    formulario = EfetivoViaturaForm(viatura=viatura)
    ids_disponiveis = set(
        formulario.fields["gcm"].queryset.values_list("pk", flat=True)
    )

    assert gcm_ativo.pk in ids_disponiveis
    assert gcm_inativo.pk not in ids_disponiveis
    assert coordenador.pk not in ids_disponiveis

def test_ca08_6_modelo_rejeita_usuario_que_nao_e_gcm(
    django_user_model, viatura
):
    """CA08.6: impede que outro perfil componha o efetivo da missão."""
    mediador = criar_usuario(django_user_model, "40001", "MEDIADOR")
    efetivo = EfetivoViatura(viatura=viatura, gcm=mediador, funcao="C")

    with pytest.raises(ValidationError) as erro:
        efetivo.full_clean()

    assert "gcm" in erro.value.message_dict

def test_ca08_7_missao_pode_ser_associada_a_escola(
    cartao, viatura, escola
):
    """CA08.7: valida a associação de uma escola cadastrada à missão."""
    missao = MissaoCartao(
        cartao=cartao,
        viatura=viatura,
        numero=1,
        escola=escola,
        endereco=escola.endereco,
        periodo="MANHA",
        tipo_missao="VISITA",
    )
    missao.full_clean()
    missao.save()

    assert missao.escola == escola
    assert escola.missoes_cartao.get() == missao

@pytest.mark.parametrize(
    "campo",
    ["numero", "viatura", "periodo", "tipo_missao"],
)
def test_ca08_8_formulario_rejeita_campos_obrigatorios_da_missao(
    cartao, viatura, escola, campo
):
    """CA08.8: impede o registro quando um dado obrigatório está vazio."""
    dados = {
        "numero": "1",
        "viatura": str(viatura.pk),
        "escola": str(escola.pk),
        "local": "",
        "endereco": escola.endereco,
        "periodo": "MANHA",
        "horario_inicio": "07:00",
        "horario_fim": "08:00",
        "tipo_missao": "VISITA",
        "observacoes": "Acompanhar o portão principal.",
    }
    dados[campo] = ""

    formulario = MissaoCartaoForm(data=dados, cartao=cartao)

    assert not formulario.is_valid()
    assert campo in formulario.errors

def test_ca08_8_missao_exige_escola_ou_outro_local(cartao, viatura):
    """CA08.8: impede missão sem escola e sem descrição de outro local."""
    formulario = MissaoCartaoForm(
        data={
            "numero": "1",
            "viatura": str(viatura.pk),
            "escola": "",
            "local": "",
            "endereco": "",
            "periodo": "MANHA",
            "horario_inicio": "07:00",
            "horario_fim": "08:00",
            "tipo_missao": "VISITA",
            "observacoes": "",
        },
        cartao=cartao,
    )

    assert not formulario.is_valid()
    assert "local" in formulario.errors

def test_ca08_9_observacoes_ficam_registradas_no_cartao_e_na_missao(
    cartao, viatura, escola
):
    """CA08.9: valida as informações complementares do planejamento."""
    missao = MissaoCartao.objects.create(
        cartao=cartao,
        viatura=viatura,
        numero=1,
        escola=escola,
        endereco=escola.endereco,
        periodo="MANHA",
        tipo_missao="VISITA",
        observacoes="Realizar contato prévio com a gestão.",
    )

    assert cartao.observacoes == "Priorizar os horários de entrada e saída."
    assert missao.observacoes == "Realizar contato prévio com a gestão."