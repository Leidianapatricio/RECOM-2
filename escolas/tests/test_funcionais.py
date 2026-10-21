"""Testes funcionais do módulo de Gestão de Escolas (F01 e F02)."""

import pytest
from django.urls import reverse

from escolas.models import Escola, EscolaProblematica, TipoProblematica


pytestmark = pytest.mark.django_db


@pytest.fixture
def dados_escola():
    return {
        "nome": "Escola Municipal Horizonte",
        "polo": "1",
        "endereco": "Rua das Acácias, 100",
        "bairro": "Centro",
        "gestor": "Ana Souza",
        "telefone": "(83) 99999-0000",
        "monitoramento": "True",
        "botao_panico": "False",
        "quantidade_alunos": "320",
        "quantidade_alunos_pcd": "12",
        "modalidade": "Ensino Fundamental",
        "observacoes": "Unidade atendida pela RECOM.",
    }

@pytest.fixture
def escola(dados_escola):
    return Escola.objects.create(**dados_escola)

@pytest.fixture
def tipos_problematicas():
    return [
        TipoProblematica.objects.create(nome="Iluminação insuficiente"),
        TipoProblematica.objects.create(nome="Vandalismo"),
    ]

def test_ca01_1_tela_de_cadastro_apresenta_os_campos_exigidos(client):
    response = client.get(reverse("escolas:cadastrar_escola"))

    assert response.status_code == 200
    campos = response.context["form"].fields
    assert {
        "nome",
        "polo",
        "endereco",
        "gestor",
        "telefone",
        "monitoramento",
        "botao_panico",
        "quantidade_alunos",
        "quantidade_alunos_pcd",
        "modalidade",
        "observacoes",
    } <= set(campos)

@pytest.mark.parametrize("campo", ["nome", "polo", "endereco"])
def test_ca01_2_nome_polo_e_endereco_sao_obrigatorios(
    client, dados_escola, campo
):
    dados = dados_escola.copy()
    dados[campo] = ""

    response = client.post(reverse("escolas:cadastrar_escola"), dados)

    assert response.status_code == 200
    assert campo in response.context["form"].errors
    assert Escola.objects.count() == 0

def test_ca01_3_nao_permite_escola_com_nome_duplicado(
    client, escola, dados_escola
):
    dados = dados_escola.copy()
    dados["nome"] = escola.nome.lower()

    response = client.post(reverse("escolas:cadastrar_escola"), dados)

    assert response.status_code == 200
    assert "nome" in response.context["form"].errors
    assert Escola.objects.count() == 1

def test_ca01_4_polo_disponibiliza_opcoes_de_1_a_9(client):
    response = client.get(reverse("escolas:cadastrar_escola"))

    escolhas = list(response.context["form"].fields["polo"].choices)
    polos_disponiveis = [
        escolha for escolha in escolhas if escolha[0] != ""
    ]

    assert polos_disponiveis == [
        (numero, f"Polo {numero}") for numero in range(1, 10)
    ]

@pytest.mark.parametrize("campo", ["monitoramento", "botao_panico"])
def test_ca01_5_campos_booleanos_disponibilizam_apenas_sim_e_nao(client, campo):
    response = client.get(reverse("escolas:cadastrar_escola"))

    escolhas = response.context["form"].fields[campo].choices
    assert list(escolhas) == [("True", "Sim"), ("False", "Não")]

@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("quantidade_alunos", "-1"),
        ("quantidade_alunos", "1.5"),
        ("quantidade_alunos_pcd", "-1"),
        ("quantidade_alunos_pcd", "1.5"),
    ],
)
def test_ca01_6_quantidades_aceitam_somente_inteiros_nao_negativos(
    client, dados_escola, campo, valor
):
    dados = dados_escola.copy()
    dados[campo] = valor

    response = client.post(reverse("escolas:cadastrar_escola"), dados)

    assert response.status_code == 200
    assert campo in response.context["form"].errors
    assert Escola.objects.count() == 0

def test_ca01_7_e_ca02_1_cadastro_valido_fica_disponivel_na_consulta(
    client, dados_escola
):
    cadastro = client.post(reverse("escolas:cadastrar_escola"), dados_escola)

    assert cadastro.status_code == 302
    escola = Escola.objects.get(nome=dados_escola["nome"])
    assert cadastro.url == reverse("escolas:listar_escolas")

    consulta = client.get(reverse("escolas:listar_escolas"))
    assert consulta.status_code == 200
    assert escola.nome in consulta.content.decode()

def test_ca02_2_consulta_de_detalhe_exibe_informacoes_da_escola(client, escola):
    response = client.get(
        reverse("escolas:detalhe_escola", kwargs={"pk": escola.pk})
    )

    assert response.status_code == 200
    conteudo = response.content.decode()
    for valor in (
        escola.nome,
        escola.endereco,
        escola.gestor,
        escola.telefone,
        escola.modalidade,
        escola.observacoes,
        str(escola.quantidade_alunos),
        str(escola.quantidade_alunos_pcd),
    ):
        assert valor in conteudo

def test_ca02_3_consulta_sem_escolas_informa_inexistencia_de_registros(client):
    response = client.get(reverse("escolas:listar_escolas"))

    assert response.status_code == 200
    assert "Nenhuma escola encontrada." in response.content.decode()

def test_ca03_1_registro_de_problematica_exige_escola_cadastrada(client):
    response = client.get(
        reverse("escolas:cadastrar_problematica", kwargs={"pk": 99999})
    )

    assert response.status_code == 404

def test_ca03_2_a_ca03_6_registra_problematica_vinculada_com_dados(
    client, escola, tipos_problematicas
):
    tipo = tipos_problematicas[0]
    dados = {
        "tipo_problematica": str(tipo.pk),
        "situacao": "EM_ACOMPANHAMENTO",
        "observacoes": "Aguardando reparo da iluminação externa.",
    }

    response = client.post(
        reverse("escolas:cadastrar_problematica", kwargs={"pk": escola.pk}),
        dados,
    )

    assert response.status_code == 302
    assert response.url == reverse(
        "escolas:detalhe_escola", kwargs={"pk": escola.pk}
    )
    problematica = EscolaProblematica.objects.get()
    assert problematica.escola == escola
    assert problematica.tipo_problematica == tipo
    assert problematica.situacao == dados["situacao"]
    assert problematica.observacoes == dados["observacoes"]

def test_ca03_3_uma_escola_pode_ter_mais_de_uma_problematica(
    client, escola, tipos_problematicas
):
    url = reverse("escolas:cadastrar_problematica", kwargs={"pk": escola.pk})
    for tipo in tipos_problematicas:
        response = client.post(
            url,
            {
                "tipo_problematica": str(tipo.pk),
                "situacao": "ATIVA",
                "observacoes": "Registro de teste.",
            },
        )
        assert response.status_code == 302

    assert escola.problematicas.count() == 2

def test_ca04_1_ca04_2_e_ca04_4_consulta_exibe_apenas_problematicas_da_escola(
    client, escola, tipos_problematicas, dados_escola
):
    outra_escola = Escola.objects.create(
        **{**dados_escola, "nome": "Escola Municipal Aurora"}
    )
    exibida = EscolaProblematica.objects.create(
        escola=escola,
        tipo_problematica=tipos_problematicas[0],
        situacao="RESOLVIDA",
        observacoes="Lâmpadas substituídas.",
    )
    EscolaProblematica.objects.create(
        escola=outra_escola,
        tipo_problematica=tipos_problematicas[1],
        observacoes="Não deve aparecer nesta consulta.",
    )

    response = client.get(
        reverse("escolas:detalhe_escola", kwargs={"pk": escola.pk})
    )

    assert response.status_code == 200
    conteudo = response.content.decode()
    assert exibida.tipo_problematica.nome in conteudo
    assert exibida.get_situacao_display() in conteudo
    assert exibida.observacoes in conteudo
    assert tipos_problematicas[1].nome not in conteudo
    assert "Não deve aparecer nesta consulta." not in conteudo

def test_ca04_3_escola_sem_problematicas_informa_inexistencia_de_registros(
    client, escola
):
    response = client.get(
        reverse("escolas:detalhe_escola", kwargs={"pk": escola.pk})
    )

    assert response.status_code == 200
    assert "Nenhuma problemática registrada para esta escola." in response.content.decode()