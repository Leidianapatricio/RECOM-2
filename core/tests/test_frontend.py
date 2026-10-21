from datetime import date, time
import os

import pytest
from django.conf import settings

from escolas.models import Escola, EscolaProblematica, TipoProblematica
from usuarios.models import Usuario
from visitas.models import RondaVisita

selenium = pytest.importorskip("selenium")

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.selenium]


@pytest.fixture
def coordenador(django_user_model):
    conta = django_user_model.objects.create_user(
        username="20001",
        password="senha-segura-123",
    )
    Usuario.objects.create(
        user=conta,
        nome="Coordenador Selenium",
        matricula="20001",
        perfil="COORDENADOR",
        primeiro_acesso=False,
    )
    return conta


@pytest.fixture
def navegador(live_server, client, coordenador):
    """Abre o Chrome com uma sessão de coordenador autenticada."""
    client.force_login(coordenador)
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


def valor_indicador(navegador, rotulo):
    """Obtém o número exibido no cartão associado a um rótulo."""
    cartao = navegador.find_element(
        By.XPATH,
        "//div[contains(@class, 'recom-stat-card')]"
        f"[.//*[normalize-space()='{rotulo}']]",
    )
    return cartao.find_element(By.CLASS_NAME, "recom-stat-number").text.strip()


def criar_cenario():
    """Cria registros usados pelos testes visuais do dashboard."""
    primeira = Escola.objects.create(
        nome="Escola Municipal Horizonte",
        polo=1,
        endereco="Rua das Acácias, 100",
    )
    segunda = Escola.objects.create(
        nome="Escola Municipal Aurora",
        polo=2,
        endereco="Rua Secundária, 20",
    )
    for indice, escola in enumerate((primeira, segunda), start=1):
        RondaVisita.objects.create(
            escola=escola,
            equipe="A",
            data_visita=date(2026, 10, 20),
            horario=time(8 + indice, 0),
        )
    tipo = TipoProblematica.objects.create(nome="Vandalismo")
    EscolaProblematica.objects.create(
        escola=primeira, tipo_problematica=tipo
    )
    EscolaProblematica.objects.create(
        escola=segunda, tipo_problematica=tipo
    )


def test_dashboard_exibe_indicadores_e_principais_problematicas(
    navegador, live_server
):
    """Valida os indicadores e problemáticas apresentados na interface."""
    criar_cenario()
    navegador.get(f"{live_server.url}/dashboard/coordenador/")

    assert valor_indicador(navegador, "Total de Escolas") == "2"
    assert valor_indicador(navegador, "Total de Visitas") == "2"
    conteudo = navegador.find_element(By.TAG_NAME, "body").text
    assert "Vandalismo" in conteudo
    assert "Escolas Problemáticas por Tipo" in conteudo


def test_dashboard_sem_dados_exibe_zeros_e_mensagens(navegador, live_server):
    """Valida a apresentação visual dos indicadores sem registros."""
    navegador.get(f"{live_server.url}/dashboard/coordenador/")

    assert valor_indicador(navegador, "Total de Escolas") == "0"
    assert valor_indicador(navegador, "Total de Visitas") == "0"
    conteudo = navegador.find_element(By.TAG_NAME, "body").text
    assert "Nenhuma escola encontrada." in conteudo
    assert "Nenhuma problemática cadastrada." in conteudo


def test_dashboard_atualiza_indicadores_apos_novos_registros(
    navegador, espera, live_server
):
    """Valida a atualização dos indicadores ao recarregar a visão."""
    url = f"{live_server.url}/dashboard/coordenador/"
    navegador.get(url)
    assert valor_indicador(navegador, "Total de Escolas") == "0"

    criar_cenario()
    navegador.refresh()
    espera.until(
        lambda driver: valor_indicador(driver, "Total de Escolas") == "2"
    )

    assert valor_indicador(navegador, "Total de Visitas") == "2"
    assert "Vandalismo" in navegador.find_element(By.TAG_NAME, "body").text
