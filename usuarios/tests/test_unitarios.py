import pytest

from cartao_programa.models import Equipe
from usuarios.forms import UsuarioForm
from usuarios.models import Usuario

pytestmark = pytest.mark.django_db


def criar_perfil(django_user_model, matricula, **dados):
    """Cria uma conta e um perfil RECOM usados nas validações unitárias."""
    conta = django_user_model.objects.create_user(
        username=matricula,
        password="senha-segura-123",
    )
    return Usuario.objects.create(
        user=conta,
        nome=dados.get("nome", "Usuário Existente"),
        matricula=matricula,
        perfil=dados.get("perfil", "MEDIADOR"),
        cpf=dados.get("cpf"),
        ativo=dados.get("ativo", True),
        primeiro_acesso=dados.get("primeiro_acesso", False),
    )


@pytest.fixture
def dados_usuario():
    return {
        "nome": "Maria da Silva",
        "matricula": "50001",
        "cpf": "123.456.789-00",
        "sexo": "F",
        "telefone": "(83) 99999-0001",
        "email": "MARIA@EXAMPLE.COM",
        "perfil": "MEDIADOR",
        "equipe": "",
        "funcao_equipe": "",
    }


def test_ca10_1_e_ca10_3_formulario_disponibiliza_campos_previstos():
    """CA10.1 e CA10.3: valida os campos obrigatórios e opcionais."""
    formulario = UsuarioForm()

    assert {
        "nome",
        "matricula",
        "perfil",
        "cpf",
        "sexo",
        "telefone",
        "email",
    } <= set(formulario.fields)
    assert formulario.fields["nome"].required
    assert formulario.fields["matricula"].required
    assert formulario.fields["perfil"].required
    for campo in ("cpf", "sexo", "telefone", "email"):
        assert not formulario.fields[campo].required


@pytest.mark.parametrize("campo", ["nome", "matricula", "perfil"])
def test_ca10_2_formulario_rejeita_campos_obrigatorios_vazios(
    dados_usuario, campo
):
    """CA10.2: rejeita cada campo obrigatório quando não preenchido."""
    dados = dados_usuario.copy()
    dados[campo] = ""

    formulario = UsuarioForm(data=dados)

    assert not formulario.is_valid()
    assert campo in formulario.errors


def test_ca10_3_formulario_aceita_dados_opcionais_vazios(dados_usuario):
    """CA10.3: permite cadastrar CPF, sexo, telefone e e-mail em branco."""
    for campo in ("cpf", "sexo", "telefone", "email"):
        dados_usuario[campo] = ""

    formulario = UsuarioForm(data=dados_usuario)

    assert formulario.is_valid(), formulario.errors
    assert formulario.cleaned_data["cpf"] is None
    assert formulario.cleaned_data["email"] is None


def test_ca10_3_formulario_normaliza_email_informado(dados_usuario):
    """CA10.3: valida e normaliza o e-mail opcional informado."""
    formulario = UsuarioForm(data=dados_usuario)

    assert formulario.is_valid(), formulario.errors
    assert formulario.cleaned_data["email"] == "maria@example.com"


def test_ca10_4_formulario_rejeita_matricula_duplicada_sem_diferenciar_maiusculas(
    django_user_model, dados_usuario
):
    """CA10.4: impede reutilizar uma matrícula já cadastrada."""
    criar_perfil(django_user_model, "ABC001")
    dados_usuario["matricula"] = "abc001"

    formulario = UsuarioForm(data=dados_usuario)

    assert not formulario.is_valid()
    assert "matricula" in formulario.errors
    assert "Já existe um usuário cadastrado" in formulario.errors["matricula"][0]


def test_ca10_5_formulario_rejeita_cpf_duplicado(
    django_user_model, dados_usuario
):
    """CA10.5: impede associar o mesmo CPF a dois usuários."""
    criar_perfil(
        django_user_model,
        "50000",
        cpf="123.456.789-00",
    )

    formulario = UsuarioForm(data=dados_usuario)

    assert not formulario.is_valid()
    assert "cpf" in formulario.errors
    assert "Já existe um usuário cadastrado" in formulario.errors["cpf"][0]


def test_ca10_6_formulario_oferece_somente_os_quatro_perfis():
    """CA10.6: valida as opções de perfil definidas para o sistema."""
    formulario = UsuarioForm()
    escolhas = {
        valor: descricao
        for valor, descricao in formulario.fields["perfil"].choices
        if valor
    }

    assert escolhas == {
        "ADMIN": "Administrador",
        "COORDENADOR": "Coordenador RECOM",
        "GCM": "Guarda Civil Municipal",
        "MEDIADOR": "Mediador",
    }


def test_ca10_7_modelo_define_usuario_ativo_por_padrao(django_user_model):
    """CA10.7: valida a situação ativa como padrão do novo perfil."""
    conta = django_user_model.objects.create_user(username="50001")
    usuario = Usuario(
        user=conta,
        nome="Maria da Silva",
        matricula="50001",
        perfil="MEDIADOR",
    )

    assert usuario.ativo is True


def test_ca10_8_modelo_marca_primeiro_acesso_por_padrao(django_user_model):
    """CA10.8: identifica que a senha provisória deve ser trocada."""
    conta = django_user_model.objects.create_user(username="50001")
    usuario = Usuario(
        user=conta,
        nome="Maria da Silva",
        matricula="50001",
        perfil="MEDIADOR",
    )

    assert usuario.primeiro_acesso is True


def test_regra_adicional_gcm_exige_equipe_e_funcao(dados_usuario):
    """Valida a regra estrutural adicional aplicada ao perfil GCM."""
    dados_usuario["perfil"] = "GCM"

    formulario = UsuarioForm(data=dados_usuario)

    assert not formulario.is_valid()
    assert "equipe" in formulario.errors
    assert "funcao_equipe" in formulario.errors


def test_regra_adicional_gcm_aceita_equipe_e_funcao(dados_usuario):
    """Valida um GCM quando equipe e função também são informadas."""
    equipe = Equipe.objects.create(nome="Equipe Alfa")
    dados_usuario.update(
        perfil="GCM",
        equipe=str(equipe.pk),
        funcao_equipe="P1",
    )

    formulario = UsuarioForm(data=dados_usuario)

    assert formulario.is_valid(), formulario.errors
