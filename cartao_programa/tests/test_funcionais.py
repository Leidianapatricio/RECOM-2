from datetime import date, time

import pytest
from django.urls import reverse

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
    """Cria uma conta autenticável vinculada a um perfil RECOM."""
    conta = django_user_model.objects.create_user(
        username=matricula,
        password="senha-segura-123",
    )
    perfil_recom = Usuario.objects.create(
        user=conta,
        nome=f"Usuário {matricula}",
        matricula=matricula,
        perfil=perfil,
        ativo=ativo,
        primeiro_acesso=False,
    )
    return conta, perfil_recom

@pytest.fixture
def coordenador(django_user_model):
    return criar_usuario(django_user_model, "20001", "COORDENADOR")

@pytest.fixture
def cliente_coordenador(client, coordenador):
    client.force_login(coordenador[0])
    return client

@pytest.fixture
def cenario(django_user_model, coordenador):
    equipe = Equipe.objects.create(nome="Equipe Alfa")
    plantao = Plantao.objects.create(
        data=date(2026, 10, 22),
        tipo_servico="ORDINARIO",
    )
    viatura = ViaturaPlantao.objects.create(
        plantao=plantao,
        identificacao="VTR-01",
        modelo="Duster",
        tipo_servico="ORDINARIO",
        equipe=equipe,
    )
    escola = Escola.objects.create(
        nome="Escola Municipal Horizonte",
        polo=1,
        endereco="Rua das Acácias, 100",
    )
    conta_gcm, gcm = criar_usuario(django_user_model, "30001", "GCM")
    EfetivoViatura.objects.create(
        viatura=viatura,
        gcm=gcm,
        funcao="C",
    )
    return {
        "coordenador": coordenador[1],
        "conta_gcm": conta_gcm,
        "gcm": gcm,
        "equipe": equipe,
        "plantao": plantao,
        "viatura": viatura,
        "escola": escola,
    }

def criar_cartao_com_missao(cenario, numero=1, local=""):
    """Monta um cartão completo usado nos testes de consulta."""
    cartao, _ = CartaoPrograma.objects.get_or_create(
        plantao=cenario["plantao"],
        defaults={
            "coordenador": cenario["coordenador"],
            "observacoes": "Planejamento prioritário da região norte.",
        },
    )
    missao = MissaoCartao.objects.create(
        cartao=cartao,
        viatura=cenario["viatura"],
        numero=numero,
        escola=cenario["escola"] if not local else None,
        local=local,
        endereco=(
            cenario["escola"].endereco if not local else "Avenida Central, 50"
        ),
        periodo="MANHA",
        horario_inicio=time(7, 0),
        horario_fim=time(8, 0),
        tipo_missao="VISITA",
        observacoes="Realizar contato com a direção.",
    )
    return cartao, missao

def test_ca08_1_coordenador_pode_acessar_criacao(
    cliente_coordenador, cenario
):
    """CA08.1: permite que o Coordenador RECOM abra o cadastro."""
    response = cliente_coordenador.get(
        reverse(
            "cartao_programa:criar_cartao",
            kwargs={"plantao_id": cenario["plantao"].pk},
        )
    )

    assert response.status_code == 200
    assert "Criar Cartão Programa" in response.content.decode()

def test_ca08_1_perfil_sem_permissao_nao_pode_criar(
    client, django_user_model, cenario
):
    """CA08.1: bloqueia a criação por perfil operacional sem permissão."""
    conta, _ = criar_usuario(django_user_model, "40001", "MEDIADOR")
    client.force_login(conta)

    response = client.get(
        reverse(
            "cartao_programa:criar_cartao",
            kwargs={"plantao_id": cenario["plantao"].pk},
        )
    )

    assert response.status_code == 403

def test_bdd_cadastro_valido_cria_cartao_com_data_responsavel_e_observacoes(
    cliente_coordenador, cenario
):
    """BDD cadastro válido; CA08.2 e CA08.9: registra os dados do cartão."""
    response = cliente_coordenador.post(
        reverse(
            "cartao_programa:criar_cartao",
            kwargs={"plantao_id": cenario["plantao"].pk},
        ),
        {"observacoes": "Priorizar o acompanhamento da entrada escolar."},
    )

    assert response.status_code == 302
    cartao = CartaoPrograma.objects.get()
    assert cartao.plantao.data == date(2026, 10, 22)
    assert cartao.coordenador == cenario["coordenador"]
    assert cartao.observacoes == "Priorizar o acompanhamento da entrada escolar."

def test_bdd_cadastro_valido_registra_missoes_e_disponibiliza_consulta(
    cliente_coordenador, cenario
):
    """BDD cadastro válido; CA08.3, CA08.7 e CA08.10: registra e consulta."""
    cartao = CartaoPrograma.objects.create(
        plantao=cenario["plantao"],
        coordenador=cenario["coordenador"],
    )
    url = reverse(
        "cartao_programa:criar_missao",
        kwargs={"plantao_id": cenario["plantao"].pk},
    )
    dados_escola = {
        "numero": "1",
        "viatura": str(cenario["viatura"].pk),
        "escola": str(cenario["escola"].pk),
        "local": "",
        "endereco": cenario["escola"].endereco,
        "periodo": "MANHA",
        "horario_inicio": "07:00",
        "horario_fim": "08:00",
        "tipo_missao": "VISITA",
        "observacoes": "Conversar com a gestão escolar.",
    }
    primeira = cliente_coordenador.post(url, dados_escola)
    segunda = cliente_coordenador.post(
        url,
        {
            **dados_escola,
            "numero": "2",
            "escola": "",
            "local": "Praça Central",
            "endereco": "Avenida Central, 50",
            "horario_inicio": "14:00",
            "horario_fim": "15:00",
            "tipo_missao": "RONDAS_PB",
        },
    )

    assert primeira.status_code == 302
    assert segunda.status_code == 302
    assert cartao.missoes.count() == 2

    consulta = cliente_coordenador.get(
        reverse(
            "cartao_programa:visualizar_cartao",
            kwargs={"plantao_id": cenario["plantao"].pk},
        )
    )
    conteudo = consulta.content.decode()
    assert consulta.status_code == 200
    assert cenario["escola"].nome in conteudo
    assert "Praça Central" in conteudo
    assert "VTR-01" in conteudo
    assert "07:00" in conteudo
    assert "14:00" in conteudo

def test_bdd_campos_obrigatorios_impedem_registro_da_missao(
    cliente_coordenador, cenario
):
    """BDD campos obrigatórios; CA08.8: não salva uma missão incompleta."""
    CartaoPrograma.objects.create(
        plantao=cenario["plantao"],
        coordenador=cenario["coordenador"],
    )
    response = cliente_coordenador.post(
        reverse(
            "cartao_programa:criar_missao",
            kwargs={"plantao_id": cenario["plantao"].pk},
        ),
        {
            "numero": "",
            "viatura": "",
            "escola": "",
            "local": "",
            "endereco": "",
            "periodo": "",
            "tipo_missao": "",
        },
    )

    assert response.status_code == 200
    assert response.context["form"].errors
    assert MissaoCartao.objects.count() == 0

def test_bdd_campos_obrigatorios_cartao_sem_missao_nao_deve_ser_concluido(
    cliente_coordenador, cenario
):
    """BDD campos obrigatórios; CA08.3 e CA08.8: exige ao menos uma missão."""
    cliente_coordenador.post(
        reverse(
            "cartao_programa:criar_cartao",
            kwargs={"plantao_id": cenario["plantao"].pk},
        ),
        {"observacoes": "Cartão ainda sem missão."},
    )

    consulta = cliente_coordenador.get(reverse("cartao_programa:listar_cartoes"))

    assert CartaoPrograma.objects.count() == 0
    assert "Cartão ainda sem missão." not in consulta.content.decode()

def test_bdd_missao_operacional_permite_informar_dados_previstos(
    cliente_coordenador, cenario
):
    """BDD missão operacional; CA08.4: expõe todos os dados da missão."""
    CartaoPrograma.objects.create(
        plantao=cenario["plantao"],
        coordenador=cenario["coordenador"],
    )

    response = cliente_coordenador.get(
        reverse(
            "cartao_programa:criar_missao",
            kwargs={"plantao_id": cenario["plantao"].pk},
        )
    )
    campos = response.context["form"].fields

    assert response.status_code == 200
    assert {
        "horario_inicio",
        "horario_fim",
        "local",
        "escola",
        "viatura",
        "tipo_missao",
    } <= set(campos)

def test_bdd_associacao_efetivo_vincula_gcm_ativo_a_missao(cenario):
    """BDD associação do efetivo; CA08.6: vincula GCM ativo via viatura."""
    _, missao = criar_cartao_com_missao(cenario)

    gcms_responsaveis = list(
        missao.viatura.efetivo.values_list("gcm_id", flat=True)
    )
    assert cenario["gcm"].ativo
    assert gcms_responsaveis == [cenario["gcm"].pk]

def test_bdd_consulta_cartoes_coordenador_visualiza_cartao_completo(
    cliente_coordenador, cenario
):
    """BDD consulta cadastrados; CA09.1, CA09.3 e CA09.4: exibe os dados."""
    cartao, missao = criar_cartao_com_missao(cenario)

    listagem = cliente_coordenador.get(reverse("cartao_programa:listar_cartoes"))
    detalhe = cliente_coordenador.get(
        reverse(
            "cartao_programa:visualizar_cartao",
            kwargs={"plantao_id": cenario["plantao"].pk},
        )
    )
    conteudo = detalhe.content.decode()

    assert listagem.status_code == 200
    assert cartao in list(listagem.context["cartoes"])
    assert detalhe.status_code == 200
    for valor in (
        "22/10/2026",
        cenario["coordenador"].nome,
        missao.get_tipo_missao_display(),
        cenario["escola"].nome,
        cenario["viatura"].identificacao,
        cenario["gcm"].nome,
        "07:00",
        "08:00",
        cartao.observacoes,
    ):
        assert valor in conteudo

def test_bdd_consulta_cartoes_gcm_visualiza_somente_as_proprias_missoes(
    client, django_user_model, cenario
):
    """BDD consulta cadastrados; CA09.2 e CA09.6: respeita o perfil GCM."""
    _, missao_permitida = criar_cartao_com_missao(cenario)

    outro_plantao = Plantao.objects.create(
        data=date(2026, 10, 23), tipo_servico="ORDINARIO"
    )
    outra_equipe = Equipe.objects.create(nome="Equipe Bravo")
    outra_viatura = ViaturaPlantao.objects.create(
        plantao=outro_plantao,
        identificacao="VTR-02",
        tipo_servico="ORDINARIO",
        equipe=outra_equipe,
    )
    outro_cartao = CartaoPrograma.objects.create(
        plantao=outro_plantao,
        coordenador=cenario["coordenador"],
    )
    missao_restrita = MissaoCartao.objects.create(
        cartao=outro_cartao,
        viatura=outra_viatura,
        numero=1,
        local="LOCAL_RESTRITO",
        endereco="Rua Restrita, 10",
        periodo="TARDE",
        tipo_missao="RONDAS",
    )
    client.force_login(cenario["conta_gcm"])

    response = client.get(reverse("cartao_programa:meu_cartao_programa"))
    conteudo = response.content.decode()

    assert response.status_code == 200
    assert missao_permitida.get_tipo_missao_display() in conteudo
    assert cenario["escola"].nome in conteudo
    assert missao_restrita.local not in conteudo
    assert outra_viatura.identificacao not in conteudo

def test_ca09_6_gcm_nao_acessa_consulta_gerencial(client, cenario):
    """CA09.6: impede o GCM de acessar a listagem gerencial completa."""
    client.force_login(cenario["conta_gcm"])

    response = client.get(reverse("cartao_programa:listar_cartoes"))

    assert response.status_code == 403

def test_bdd_consulta_por_filtros_restringe_por_data_e_escola(
    cliente_coordenador, cenario
):
    """BDD consulta por filtros; CA09.5: restringe por data e escola."""
    cartao_esperado, _ = criar_cartao_com_missao(cenario)
    outro_plantao = Plantao.objects.create(
        data=date(2026, 10, 23), tipo_servico="EXTRAORDINARIO"
    )
    outro_cartao = CartaoPrograma.objects.create(
        plantao=outro_plantao,
        coordenador=cenario["coordenador"],
    )

    response = cliente_coordenador.get(
        reverse("cartao_programa:listar_cartoes"),
        {"data": "2026-10-22", "escola_local": "Horizonte"},
    )

    resultados = list(response.context["cartoes"])
    assert resultados == [cartao_esperado]
    assert outro_cartao not in resultados

def test_bdd_nenhum_resultado_encontrado_informa_ausencia(
    cliente_coordenador, cenario
):
    """BDD nenhum resultado; CA09.7: informa a ausência de correspondência."""
    criar_cartao_com_missao(cenario)

    response = cliente_coordenador.get(
        reverse("cartao_programa:listar_cartoes"),
        {"data": "2030-01-01", "escola_local": "Escola inexistente"},
    )

    assert list(response.context["cartoes"]) == []
    assert "Nenhum registro encontrado" in response.content.decode()

def test_ca09_7_consulta_sem_cartoes_informa_inexistencia(
    cliente_coordenador
):
    """CA09.7: apresenta mensagem quando não há cartões cadastrados."""
    response = cliente_coordenador.get(reverse("cartao_programa:listar_cartoes"))

    assert response.status_code == 200
    assert "Nenhum Cartão Programa cadastrado." in response.content.decode()