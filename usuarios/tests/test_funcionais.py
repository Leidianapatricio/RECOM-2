import pytest
from django.contrib.auth import authenticate
from django.contrib.messages import get_messages
from django.urls import reverse

from usuarios.models import Usuario

pytestmark = pytest.mark.django_db


def criar_perfil(
    django_user_model,
    matricula,
    senha="senha-segura-123",
    perfil="MEDIADOR",
    ativo=True,
    primeiro_acesso=False,
    cpf=None,
):
    """Cria uma conta autenticável e seu perfil RECOM."""
    conta = django_user_model.objects.create_user(
        username=matricula,
        password=senha,
    )
    usuario = Usuario.objects.create(
        user=conta,
        nome=f"Usuário {matricula}",
        matricula=matricula,
        perfil=perfil,
        cpf=cpf,
        ativo=ativo,
        primeiro_acesso=primeiro_acesso,
    )
    return conta, usuario


@pytest.fixture
def administrador(django_user_model):
    return django_user_model.objects.create_superuser(
        username="admin_usuarios",
        password="senha-segura-123",
        email="admin.usuarios@example.com",
    )


@pytest.fixture
def cliente_administrador(client, administrador):
    client.force_login(administrador)
    return client


@pytest.fixture
def dados_usuario():
    return {
        "nome": "Maria da Silva",
        "matricula": "50001",
        "cpf": "123.456.789-00",
        "sexo": "F",
        "telefone": "(83) 99999-0001",
        "email": "maria@example.com",
        "perfil": "MEDIADOR",
        "equipe": "",
        "funcao_equipe": "",
    }


def mensagens_da_resposta(response):
    """Retorna as mensagens Django produzidas pela requisição."""
    return [str(mensagem) for mensagem in get_messages(response.wsgi_request)]


def test_ca10_1_ca10_3_ca10_6_formulario_apresenta_campos_e_perfis(
    cliente_administrador
):
    """CA10.1, CA10.3 e CA10.6: apresenta dados básicos, opcionais e perfis."""
    response = cliente_administrador.get(reverse("usuarios:criar"))
    formulario = response.context["form"]

    assert response.status_code == 200
    assert {
        "nome",
        "matricula",
        "perfil",
        "cpf",
        "sexo",
        "telefone",
        "email",
    } <= set(formulario.fields)
    assert {valor for valor, _ in formulario.fields["perfil"].choices if valor} == {
        "ADMIN",
        "COORDENADOR",
        "GCM",
        "MEDIADOR",
    }


def test_bdd_cadastro_dados_validos_registra_usuario_ativo(
    cliente_administrador, dados_usuario, django_user_model
):
    """BDD cadastro válido; CA10.1, CA10.3, CA10.6 e CA10.7."""
    response = cliente_administrador.post(
        reverse("usuarios:criar"), dados_usuario
    )

    assert response.status_code == 302
    assert response.url == reverse("usuarios:listar")
    usuario = Usuario.objects.get(matricula="50001")
    conta = django_user_model.objects.get(username="50001")
    assert usuario.user == conta
    assert usuario.nome == dados_usuario["nome"]
    assert usuario.perfil == "MEDIADOR"
    assert usuario.ativo is True
    assert usuario.cpf == dados_usuario["cpf"]
    assert usuario.sexo == dados_usuario["sexo"]
    assert usuario.telefone == dados_usuario["telefone"]
    assert usuario.email == dados_usuario["email"]


@pytest.mark.parametrize("campo", ["nome", "matricula", "perfil"])
def test_bdd_campos_obrigatorios_impedem_cadastro(
    cliente_administrador, dados_usuario, campo
):
    """BDD campos obrigatórios; CA10.2 e CA10.9: não cria registro inválido."""
    dados = dados_usuario.copy()
    dados[campo] = ""

    response = cliente_administrador.post(reverse("usuarios:criar"), dados)

    assert response.status_code == 200
    assert campo in response.context["form"].errors
    assert Usuario.objects.count() == 0


def test_bdd_matricula_ja_cadastrada_informa_duplicidade(
    cliente_administrador, django_user_model, dados_usuario
):
    """BDD matrícula cadastrada; CA10.4 e CA10.9: impede a duplicidade."""
    criar_perfil(django_user_model, "50001")

    response = cliente_administrador.post(
        reverse("usuarios:criar"), dados_usuario
    )

    assert response.status_code == 200
    erros = response.context["form"].errors["matricula"]
    assert any("Já existe" in erro for erro in erros)
    assert Usuario.objects.filter(matricula="50001").count() == 1


def test_ca10_5_cpf_duplicado_impede_cadastro(
    cliente_administrador, django_user_model, dados_usuario
):
    """CA10.5 e CA10.9: informa e impede o cadastro com CPF duplicado."""
    criar_perfil(
        django_user_model,
        "50000",
        cpf=dados_usuario["cpf"],
    )

    response = cliente_administrador.post(
        reverse("usuarios:criar"), dados_usuario
    )

    assert response.status_code == 200
    erros = response.context["form"].errors["cpf"]
    assert any("Já existe" in erro for erro in erros)
    assert Usuario.objects.count() == 1


def test_bdd_definicao_senha_inicial_configura_1234_e_primeiro_acesso(
    cliente_administrador, dados_usuario
):
    """BDD senha inicial; CA10.8: define 1234 e exige sua substituição."""
    response = cliente_administrador.post(
        reverse("usuarios:criar"), dados_usuario
    )

    assert response.status_code == 302
    usuario = Usuario.objects.get(matricula="50001")
    assert usuario.user.check_password("1234")
    assert usuario.primeiro_acesso is True
    assert authenticate(username="50001", password="1234") == usuario.user


def test_bdd_autenticacao_valida_permite_acesso(
    client, django_user_model
):
    """BDD autenticação válida; CA11.1 e CA11.2: autentica pela matrícula."""
    conta, _ = criar_perfil(
        django_user_model,
        "50001",
        senha="5678",
        perfil="MEDIADOR",
    )
    client.raise_request_exception = False

    response = client.post(
        reverse("core:login"),
        {"matricula": "50001", "senha": "5678"},
        follow=True,
    )

    assert response.status_code == 200
    assert response.redirect_chain[-1][0] == reverse("core:dashboard_mediador")
    assert client.session.get("_auth_user_id") == str(conta.pk)


def test_primeiro_acesso_com_senha_1234_solicita_nova_senha(
    client, django_user_model
):
    """CA10.8 e CA11.2: autentica a senha inicial e solicita sua troca."""
    criar_perfil(
        django_user_model,
        "50001",
        senha="1234",
        primeiro_acesso=True,
    )

    response = client.post(
        reverse("core:login"),
        {"matricula": "50001", "senha": "1234"},
    )

    assert response.status_code == 302
    assert response.url == reverse("core:primeiro_acesso")


@pytest.mark.parametrize(
    ("matricula", "senha"),
    [("99999", "5678"), ("50001", "senha-incorreta")],
)
def test_bdd_matricula_ou_senha_invalida_impede_autenticacao_e_informa(
    client, django_user_model, matricula, senha
):
    """BDD credencial inválida; CA11.3 e CA11.4: recusa e informa o erro."""
    criar_perfil(django_user_model, "50001", senha="5678")

    response = client.post(
        reverse("core:login"),
        {"matricula": matricula, "senha": senha},
    )

    assert response.status_code == 200
    assert "Matrícula ou senha inválidos." in mensagens_da_resposta(response)
    assert "_auth_user_id" not in client.session


def test_bdd_usuario_inativo_impede_acesso_e_informa(
    client, django_user_model
):
    """BDD usuário inativo; CA11.5 e CA11.6: bloqueia e informa a situação."""
    criar_perfil(
        django_user_model,
        "50001",
        senha="5678",
        ativo=False,
    )

    response = client.post(
        reverse("core:login"),
        {"matricula": "50001", "senha": "5678"},
    )

    assert response.status_code == 200
    assert "Este usuário está inativo. Procure o administrador." in mensagens_da_resposta(
        response
    )
    assert "_auth_user_id" not in client.session
