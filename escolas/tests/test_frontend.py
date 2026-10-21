import os
import pytest

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
def navegador():
    """Abre o Chrome para um teste e garante seu encerramento."""
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

    driver.implicitly_wait(2)
    yield driver
    driver.quit()

@pytest.fixture
def espera(navegador):
    return WebDriverWait(navegador, 10)

def preencher_formulario_escola(navegador, nome="Escola Municipal Horizonte"):
    """Preenche os campos usados pelos testes da interface de cadastro."""
    navegador.find_element(By.NAME, "nome").send_keys(nome)
    Select(navegador.find_element(By.NAME, "polo")).select_by_value("1")
    navegador.find_element(By.NAME, "endereco").send_keys("Rua das Acácias, 100")
    navegador.find_element(By.NAME, "gestor").send_keys("Ana Souza")
    navegador.find_element(By.NAME, "telefone").send_keys("(83) 99999-0000")
    Select(navegador.find_element(By.NAME, "monitoramento")).select_by_value(
        "True"
    )
    Select(navegador.find_element(By.NAME, "botao_panico")).select_by_value(
        "False"
    )
    navegador.find_element(By.NAME, "quantidade_alunos").send_keys("320")
    navegador.find_element(By.NAME, "quantidade_alunos_pcd").send_keys("12")
    navegador.find_element(By.NAME, "modalidade").send_keys("Ensino Fundamental")
    navegador.find_element(By.NAME, "observacoes").send_keys(
        "Unidade atendida pela RECOM."
    )

def enviar_formulario(botao):
    """Aciona o botão pelo teclado e preserva a validação do navegador."""
    botao.send_keys(Keys.ENTER)

def test_formulario_de_escola_exibe_campos_e_opcoes(navegador, live_server):
    """Valida os campos e as opções visíveis no formulário de escola."""
    navegador.get(f"{live_server.url}/escolas/nova/")

    for nome_campo in (
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
    ):
        assert navegador.find_element(By.NAME, nome_campo).is_displayed()

    polos = Select(navegador.find_element(By.NAME, "polo")).options
    assert [opcao.text for opcao in polos if opcao.get_attribute("value")] == [
        f"Polo {numero}" for numero in range(1, 10)
    ]

    for campo in ("monitoramento", "botao_panico"):
        opcoes = Select(navegador.find_element(By.NAME, campo)).options
        assert [opcao.text for opcao in opcoes] == ["Sim", "Não"]

def test_campos_obrigatorios_bloqueiam_envio_no_navegador(navegador, live_server):
    """Valida a obrigatoriedade de nome, polo e endereço no navegador."""
    navegador.get(f"{live_server.url}/escolas/nova/")

    for campo in ("nome", "polo", "endereco"):
        assert navegador.find_element(By.NAME, campo).get_attribute("required")

    botao_salvar = navegador.find_element(
        By.CSS_SELECTOR, "button[name='salvar']"
    )
    enviar_formulario(botao_salvar)
    assert navegador.current_url == f"{live_server.url}/escolas/nova/"

def test_usuario_cadastra_escola_e_a_encontra_na_consulta(
    navegador, espera, live_server
):
    """Valida que uma escola cadastrada apareça na tela de consulta."""
    nome = "Escola Municipal Horizonte"
    navegador.get(f"{live_server.url}/escolas/nova/")
    preencher_formulario_escola(navegador, nome)

    botao_salvar = navegador.find_element(
        By.CSS_SELECTOR, "button[name='salvar']"
    )
    enviar_formulario(botao_salvar)
    espera.until(EC.url_to_be(f"{live_server.url}/escolas/"))
    conteudo = navegador.find_element(By.TAG_NAME, "body").text
    assert nome in conteudo

def test_usuario_registra_problematica_pela_interface(
    navegador, espera, live_server
):
    """Valida o registro e a consulta de uma problemática pela interface."""
    from escolas.models import TipoProblematica

    TipoProblematica.objects.create(nome="Iluminação insuficiente")
    nome = "Escola Municipal Horizonte"
    navegador.get(f"{live_server.url}/escolas/nova/")
    preencher_formulario_escola(navegador, nome)
    botao_salvar = navegador.find_element(
        By.CSS_SELECTOR, "button[name='salvar']"
    )
    enviar_formulario(botao_salvar)
    espera.until(EC.url_to_be(f"{live_server.url}/escolas/"))
    espera.until(EC.element_to_be_clickable((By.LINK_TEXT, "Visualizar"))).click()
    url_detalhe = navegador.current_url

    link_problematica = espera.until(
        EC.element_to_be_clickable((By.LINK_TEXT, "Registrar Problemática"))
    )
    link_problematica.click()
    Select(
        navegador.find_element(By.NAME, "tipo_problematica")
    ).select_by_visible_text("Iluminação insuficiente")
    Select(navegador.find_element(By.NAME, "situacao")).select_by_value(
        "EM_ACOMPANHAMENTO"
    )
    navegador.find_element(By.NAME, "observacoes").send_keys(
        "Aguardando reparo da iluminação externa."
    )
    botao_salvar = navegador.find_element(
        By.CSS_SELECTOR, "button[type='submit']"
    )
    enviar_formulario(botao_salvar)

    espera.until(EC.url_to_be(url_detalhe))
    conteudo = navegador.find_element(By.TAG_NAME, "body").text
    assert "Em acompanhamento" in conteudo
    assert "Iluminação insuficiente" in conteudo
    assert "Aguardando reparo da iluminação externa." in conteudo

def test_listagem_vazia_informa_que_nao_ha_escolas(navegador, live_server):
    """Valida a mensagem apresentada quando não existem escolas cadastradas."""
    navegador.get(f"{live_server.url}/escolas/")

    assert "Nenhuma escola encontrada." in navegador.find_element(
        By.TAG_NAME, "body"
    ).text
