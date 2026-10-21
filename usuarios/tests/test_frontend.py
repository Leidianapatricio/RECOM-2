import os

import pytest
from django.conf import settings
from django.urls import reverse

from usuarios.models import Usuario

selenium = pytest.importorskip("selenium")

from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.selenium]


def criar_perfil(
    django_user_model,
    matricula,
    senha="5678",
    perfil="MEDIADOR",
    ativo=True,
    primeiro_acesso=False,
):
    """Cria uma conta e seu perfil RECOM para os testes no navegador."""
    conta = django_user_model.objects.create_user(
        username=matricula,
        password=senha,
    )
    usuario = Usuario.objects.create(
        user=conta,
        nome=f"Usuário {matricula}",
        matricula=matricula,
        perfil=perfil,
        ativo=ativo,
        primeiro_acesso=primeiro_acesso,
    )
    return conta, usuario


@pytest.fixture
def administrador(django_user_model):
    return django_user_model.objects.create_superuser(
        username="admin_selenium_usuarios",
        password="senha-segura-123",
        email="admin.selenium.usuarios@example.com",
    )


@pytest.fixture
def navegador(live_server):
    """Abre o Chrome e garante seu encerramento ao final do teste."""
    opcoes = Options()
    if os.getenv("SELENIUM_HEADLESS", "1") != "0":
        opcoes.add_argument("--headless=new")
    opcoes.add_argument("--window-size=1440,1080")
    opcoes.add_argument("--no-sandbox")
    opcoes.add_argument("--disable-dev-shm-usage")

    try:
        driver = webdriver.Chrome(options=opcoes)
    except WebDriverException as erro:
        pytest.skip(f"Chrome ou WebDriver indisponível: {erro.msg}")

    driver.get(live_server.url)
    driver.implicitly_wait(2)
    yield driver
    driver.quit()


@pytest.fixture
def espera(navegador):
    return WebDriverWait(navegador, 10)


def url_absoluta(live_server, nome_rota):
    """Monta uma URL do servidor utilizado pelo Selenium."""
    return f"{live_server.url}{reverse(nome_rota)}"


def autenticar_navegador(navegador, live_server, client, conta):
    """Transfere para o Chrome uma sessão autenticada pelo cliente Django."""
    client.force_login(conta)
    navegador.get(live_server.url)
    navegador.delete_all_cookies()
    navegador.add_cookie(
        {
            "name": settings.SESSION_COOKIE_NAME,
            "value": client.cookies[settings.SESSION_COOKIE_NAME].value,
        }
    )


def preencher_cadastro(navegador, matricula="50001"):
    """Preenche um cadastro válido do perfil Mediador."""
    navegador.find_element(By.NAME, "nome").send_keys("Maria da Silva")
    navegador.find_element(By.NAME, "matricula").send_keys(matricula)
    navegador.find_element(By.NAME, "cpf").send_keys("123.456.789-00")
    Select(navegador.find_element(By.NAME, "sexo")).select_by_value("F")
    navegador.find_element(By.NAME, "telefone").send_keys("(83) 99999-0001")
    navegador.find_element(By.NAME, "email").send_keys("maria@example.com")
    Select(navegador.find_element(By.NAME, "perfil")).select_by_value("MEDIADOR")


def enviar_formulario(navegador):
    """Envia o formulário por teclado como faria o usuário."""
    navegador.find_element(By.CSS_SELECTOR, "button[type='submit']").send_keys(
        Keys.ENTER
    )


def preencher_login(navegador, matricula, senha):
    """Preenche e envia as credenciais da tela de login."""
    navegador.find_element(By.NAME, "matricula").send_keys(matricula)
    navegador.find_element(By.NAME, "senha").send_keys(senha)
    enviar_formulario(navegador)


def esperar_texto_da_pagina(espera, trecho):
    """Aguarda a nova página e evita ler elementos substituídos pelo navegador."""
    def obter_texto(driver):
        try:
            texto = driver.find_element(By.TAG_NAME, "body").text
            return texto if trecho in texto else False
        except StaleElementReferenceException:
            return False

    return espera.until(obter_texto)


def test_formulario_exibe_campos_obrigatorios_opcionais_e_perfis(
    navegador, live_server, client, administrador
):
    """CA10.1, CA10.2, CA10.3 e CA10.6: verifica o formulário visível."""
    autenticar_navegador(navegador, live_server, client, administrador)
    navegador.get(url_absoluta(live_server, "usuarios:criar"))

    for campo in (
        "nome",
        "matricula",
        "perfil",
        "cpf",
        "sexo",
        "telefone",
        "email",
    ):
        assert navegador.find_element(By.NAME, campo).is_enabled()

    for campo in ("nome", "matricula", "perfil"):
        assert navegador.find_element(By.NAME, campo).get_attribute("required")

    perfis = {
        opcao.get_attribute("value"): opcao.text
        for opcao in Select(navegador.find_element(By.NAME, "perfil")).options
        if opcao.get_attribute("value")
    }
    assert perfis == {
        "ADMIN": "Administrador",
        "COORDENADOR": "Coordenador RECOM",
        "GCM": "Guarda Civil Municipal",
        "MEDIADOR": "Mediador",
    }


def test_bdd_cadastro_valido_registra_usuario_e_exibe_na_consulta(
    navegador, espera, live_server, client, administrador
):
    """BDD cadastro válido: cadastra e apresenta o usuário na listagem."""
    autenticar_navegador(navegador, live_server, client, administrador)
    navegador.get(url_absoluta(live_server, "usuarios:criar"))
    preencher_cadastro(navegador)
    enviar_formulario(navegador)

    espera.until(EC.url_to_be(url_absoluta(live_server, "usuarios:listar")))
    conteudo = navegador.find_element(By.TAG_NAME, "body").text
    assert "Maria da Silva" in conteudo
    assert "50001" in conteudo
    assert "Mediador" in conteudo


def test_bdd_campos_obrigatorios_exibem_erros_e_impedem_cadastro(
    navegador, espera, live_server, client, administrador
):
    """BDD campos obrigatórios: mantém a tela e apresenta os erros."""
    autenticar_navegador(navegador, live_server, client, administrador)
    url = url_absoluta(live_server, "usuarios:criar")
    navegador.get(url)
    enviar_formulario(navegador)

    conteudo = esperar_texto_da_pagina(espera, "Este campo é obrigatório.")
    assert navegador.current_url == url
    assert conteudo.count("Este campo é obrigatório.") >= 3
    assert Usuario.objects.count() == 0


def test_bdd_matricula_duplicada_exibe_erro_e_impede_novo_registro(
    navegador, live_server, client, administrador, django_user_model
):
    """BDD matrícula cadastrada: informa a duplicidade pela interface."""
    criar_perfil(django_user_model, "50001")
    autenticar_navegador(navegador, live_server, client, administrador)
    navegador.get(url_absoluta(live_server, "usuarios:criar"))
    preencher_cadastro(navegador)
    enviar_formulario(navegador)

    conteudo = navegador.find_element(By.TAG_NAME, "body").text
    assert "Já existe um usuário cadastrado com esta matrícula." in conteudo
    assert Usuario.objects.filter(matricula="50001").count() == 1


def test_bdd_senha_inicial_permite_login_e_direciona_ao_primeiro_acesso(
    navegador, espera, live_server, client, administrador
):
    """BDD senha inicial: usa 1234 e solicita a definição de nova senha."""
    autenticar_navegador(navegador, live_server, client, administrador)
    navegador.get(url_absoluta(live_server, "usuarios:criar"))
    preencher_cadastro(navegador)
    enviar_formulario(navegador)
    espera.until(EC.url_to_be(url_absoluta(live_server, "usuarios:listar")))

    navegador.delete_all_cookies()
    navegador.get(url_absoluta(live_server, "core:login"))
    preencher_login(navegador, "50001", "1234")

    espera.until(EC.url_to_be(url_absoluta(live_server, "core:primeiro_acesso")))
    assert "Por segurança, cadastre uma nova senha" in navegador.find_element(
        By.TAG_NAME, "body"
    ).text


def test_bdd_autenticacao_valida_direciona_para_area_do_perfil(
    navegador, espera, live_server, django_user_model
):
    """BDD autenticação válida: permite o acesso com matrícula e senha."""
    criar_perfil(django_user_model, "50001", senha="5678")
    navegador.get(url_absoluta(live_server, "core:login"))
    preencher_login(navegador, "50001", "5678")

    espera.until(EC.url_to_be(url_absoluta(live_server, "core:dashboard_mediador")))
    assert "50001" in navegador.find_element(By.TAG_NAME, "body").text


@pytest.mark.parametrize(
    ("matricula", "senha"),
    [("99999", "5678"), ("50001", "senha-incorreta")],
)
def test_bdd_credenciais_invalidas_exibem_mensagem(
    navegador, espera, live_server, django_user_model, matricula, senha
):
    """BDD credencial inválida: bloqueia o acesso e informa o motivo."""
    criar_perfil(django_user_model, "50001", senha="5678")
    navegador.get(url_absoluta(live_server, "core:login"))
    preencher_login(navegador, matricula, senha)

    conteudo = esperar_texto_da_pagina(espera, "Matrícula ou senha inválidos.")
    assert navegador.current_url == url_absoluta(live_server, "core:login")
    assert "Matrícula ou senha inválidos." in conteudo


def test_bdd_usuario_inativo_tem_acesso_bloqueado_com_mensagem(
    navegador, espera, live_server, django_user_model
):
    """BDD usuário inativo: impede o acesso e informa sua situação."""
    criar_perfil(
        django_user_model,
        "50001",
        senha="5678",
        ativo=False,
    )
    navegador.get(url_absoluta(live_server, "core:login"))
    preencher_login(navegador, "50001", "5678")

    conteudo = esperar_texto_da_pagina(
        espera, "Este usuário está inativo. Procure o administrador."
    )
    assert navegador.current_url == url_absoluta(live_server, "core:login")
    assert "Este usuário está inativo. Procure o administrador." in conteudo
