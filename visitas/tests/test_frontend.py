import os

import pytest
from django.conf import settings

from escolas.models import Escola

selenium = pytest.importorskip("selenium")

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.selenium]


@pytest.fixture
def escola():
    return Escola.objects.create(
        nome="Escola Municipal Horizonte",
        polo=1,
        endereco="Rua das Acácias, 100",
    )


@pytest.fixture
def navegador(live_server, client, django_user_model):
    """Abre o Chrome com uma sessão administrativa autenticada."""
    administrador = django_user_model.objects.create_superuser(
        username="admin_selenium_visitas",
        password="senha-segura-123",
        email="selenium.visitas@example.com",
    )
    client.force_login(administrador)

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
    driver.add_cookie(
        {
            "name": settings.SESSION_COOKIE_NAME,
            "value": client.cookies[settings.SESSION_COOKIE_NAME].value,
        }
    )
    driver.implicitly_wait(2)
    yield driver
    driver.quit()


@pytest.fixture
def espera(navegador):
    return WebDriverWait(navegador, 10)


def selecionar_escola(navegador, escola):
    """Seleciona uma escola mesmo quando o componente visual oculta o select."""
    campo = navegador.find_element(By.NAME, "escola")
    navegador.execute_script(
        "arguments[0].value = arguments[1]; "
        "arguments[0].dispatchEvent(new Event('change', {bubbles: true}));",
        campo,
        str(escola.pk),
    )


def preencher_visita(navegador, escola):
    """Preenche os dados usados no fluxo de registro da visita."""
    selecionar_escola(navegador, escola)
    Select(navegador.find_element(By.NAME, "equipe")).select_by_value("A")
    navegador.execute_script(
        "arguments[0].value = '2026-10-20';",
        navegador.find_element(By.NAME, "data_visita"),
    )
    navegador.execute_script(
        "arguments[0].value = '09:30';",
        navegador.find_element(By.NAME, "horario"),
    )
    Select(navegador.find_element(By.NAME, "tipo_visita")).select_by_value(
        "ROTINA"
    )
    Select(navegador.find_element(By.NAME, "situacao")).select_by_value(
        "COM_ALTERACAO"
    )
    navegador.find_element(By.NAME, "relato").send_keys(
        "Portão lateral danificado."
    )
    navegador.find_element(By.NAME, "orientacoes").send_keys(
        "A gestão foi orientada a solicitar o reparo."
    )


def enviar_formulario(navegador):
    """Aciona o formulário pelo teclado e preserva a validação do navegador."""
    botao = navegador.find_element(By.CSS_SELECTOR, "button[type='submit']")
    botao.send_keys(Keys.ENTER)


def test_formulario_de_visita_exibe_os_campos_previstos(navegador, live_server):
    """Valida os componentes visíveis no formulário de visita."""
    navegador.get(f"{live_server.url}/visitas/nova/")

    for campo in (
        "escola",
        "equipe",
        "data_visita",
        "horario",
        "tipo_visita",
        "situacao",
        "relato",
        "orientacoes",
    ):
        assert navegador.find_element(By.NAME, campo).is_enabled()


def test_escola_obrigatoria_bloqueia_envio_no_navegador(
    navegador, live_server
):
    """Valida que o navegador impeça o registro sem escola selecionada."""
    navegador.get(f"{live_server.url}/visitas/nova/")
    campo_escola = navegador.find_element(By.NAME, "escola")

    assert campo_escola.get_attribute("required")
    enviar_formulario(navegador)

    assert navegador.current_url == f"{live_server.url}/visitas/nova/"
    assert campo_escola.get_attribute("validationMessage")


def test_usuario_registra_visita_e_a_encontra_no_historico(
    navegador, espera, live_server, escola
):
    """Valida o registro e a inclusão da visita no histórico da escola."""
    navegador.get(f"{live_server.url}/visitas/nova/")
    preencher_visita(navegador, escola)
    enviar_formulario(navegador)

    url_historico = f"{live_server.url}/escolas/{escola.pk}/"
    espera.until(EC.url_to_be(url_historico))
    conteudo = navegador.find_element(By.TAG_NAME, "body").text
    assert "20/10/2026" in conteudo
    assert "09:30" in conteudo
    assert "Equipe A" in conteudo
    assert "Portão lateral danificado." in conteudo
    assert "A gestão foi orientada a solicitar o reparo." in conteudo


def test_historico_vazio_informa_ausencia_de_visitas(
    navegador, live_server, escola
):
    """Valida a mensagem exibida quando a escola não possui visitas."""
    navegador.get(f"{live_server.url}/escolas/{escola.pk}/")

    conteudo = navegador.find_element(By.TAG_NAME, "body").text
    assert "Nenhuma visita registrada para esta escola." in conteudo
