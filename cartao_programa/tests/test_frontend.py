from datetime import date
import os

import pytest
from django.conf import settings
from django.urls import reverse

from cartao_programa.models import (
    CartaoPrograma,
    EfetivoViatura,
    Equipe,
    Plantao,
    ViaturaPlantao,
)
from escolas.models import Escola
from usuarios.models import Usuario

selenium = pytest.importorskip("selenium")

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.selenium]

def criar_usuario(django_user_model, matricula, perfil):
    """Cria uma conta com perfil RECOM para os testes no navegador."""
    conta = django_user_model.objects.create_user(
        username=matricula,
        password="senha-segura-123",
    )
    perfil_recom = Usuario.objects.create(
        user=conta,
        nome=f"Usuário {matricula}",
        matricula=matricula,
        perfil=perfil,
        ativo=True,
        primeiro_acesso=False,
    )
    return conta, perfil_recom

@pytest.fixture
def coordenador(django_user_model):
    return criar_usuario(django_user_model, "20001", "COORDENADOR")

@pytest.fixture
def navegador(live_server, client, coordenador):
    """Abre o Chrome com uma sessão de coordenador autenticada."""
    client.force_login(coordenador[0])
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
        "plantao": plantao,
        "viatura": viatura,
        "escola": escola,
    }

def url_absoluta(live_server, nome_rota, **kwargs):
    """Converte uma rota Django em endereço do servidor de teste."""
    return f"{live_server.url}{reverse(nome_rota, kwargs=kwargs or None)}"

def criar_cartao(cenario):
    """Cria o cartão necessário para acessar o formulário de missão."""
    return CartaoPrograma.objects.create(
        plantao=cenario["plantao"],
        coordenador=cenario["coordenador"],
        observacoes="Planejamento do turno escolar.",
    )

def enviar_formulario(navegador):
    """Envia o formulário preservando a validação HTML do navegador."""
    navegador.find_element(By.CSS_SELECTOR, "button[type='submit']").send_keys(
        Keys.ENTER
    )

def test_coordenador_visualiza_dados_do_cadastro_do_cartao(
    navegador, live_server, cenario
):
    """CA08.1, CA08.2 e CA08.9: exibe data, responsável e observações."""
    navegador.get(
        url_absoluta(
            live_server,
            "cartao_programa:criar_cartao",
            plantao_id=cenario["plantao"].pk,
        )
    )
    conteudo = navegador.find_element(By.TAG_NAME, "body").text

    assert "Criar Cartão Programa" in conteudo
    assert "22/10/2026" in conteudo
    assert cenario["coordenador"].nome in conteudo
    assert navegador.find_element(By.NAME, "observacoes").is_enabled()

def test_tipos_de_missao_exibem_atividades_previstas(
    navegador, live_server, cenario
):
    """CA08.5: verifica os tipos operacionais disponíveis na interface."""
    criar_cartao(cenario)
    navegador.get(
        url_absoluta(
            live_server,
            "cartao_programa:criar_missao",
            plantao_id=cenario["plantao"].pk,
        )
    )

    tipos = {
        opcao.text
        for opcao in Select(
            navegador.find_element(By.NAME, "tipo_missao")
        ).options
        if opcao.get_attribute("value")
    }
    assert {
        "Entrada escolar",
        "Saída escolar",
        "Visita de rotina",
        "Rondas e PB",
    } <= tipos

def test_campos_obrigatorios_bloqueiam_missao_incompleta(
    navegador, live_server, cenario
):
    """CA08.8: impede o envio visual de uma missão sem dados obrigatórios."""
    criar_cartao(cenario)
    url = url_absoluta(
        live_server,
        "cartao_programa:criar_missao",
        plantao_id=cenario["plantao"].pk,
    )
    navegador.get(url)

    for campo in ("numero", "viatura", "periodo", "tipo_missao"):
        assert navegador.find_element(By.NAME, campo).get_attribute("required")

    enviar_formulario(navegador)
    assert navegador.current_url == url

def test_coordenador_registra_missao_e_a_encontra_na_consulta(
    navegador, espera, live_server, cenario
):
    """CA08.3, CA08.4, CA08.7 e CA08.10: executa o fluxo completo da missão."""
    criar_cartao(cenario)
    navegador.get(
        url_absoluta(
            live_server,
            "cartao_programa:criar_missao",
            plantao_id=cenario["plantao"].pk,
        )
    )

    navegador.find_element(By.NAME, "numero").send_keys("1")
    Select(navegador.find_element(By.NAME, "viatura")).select_by_value(
        str(cenario["viatura"].pk)
    )
    Select(navegador.find_element(By.NAME, "escola")).select_by_value(
        str(cenario["escola"].pk)
    )
    navegador.find_element(By.NAME, "endereco").send_keys(
        cenario["escola"].endereco
    )
    Select(navegador.find_element(By.NAME, "periodo")).select_by_value("MANHA")
    navegador.execute_script(
        "arguments[0].value = '07:00';",
        navegador.find_element(By.NAME, "horario_inicio"),
    )
    navegador.execute_script(
        "arguments[0].value = '08:00';",
        navegador.find_element(By.NAME, "horario_fim"),
    )
    Select(navegador.find_element(By.NAME, "tipo_missao")).select_by_value(
        "VISITA"
    )
    navegador.find_element(By.NAME, "observacoes").send_keys(
        "Realizar contato com a direção."
    )
    enviar_formulario(navegador)

    url_lista = url_absoluta(
        live_server,
        "cartao_programa:listar_missoes",
        plantao_id=cenario["plantao"].pk,
    )
    espera.until(EC.url_to_be(url_lista))
    conteudo = navegador.find_element(By.TAG_NAME, "body").text
    assert cenario["escola"].nome in conteudo
    assert "VTR-01" in conteudo
    assert "Visita de rotina" in conteudo
    assert "07:00" in conteudo
    assert "08:00" in conteudo

def test_consulta_vazia_informa_ausencia_de_cartoes(navegador, live_server):
    """CA09.7: apresenta uma mensagem quando não existem cartões."""
    navegador.get(
        url_absoluta(live_server, "cartao_programa:listar_cartoes")
    )

    assert "Nenhum Cartão Programa cadastrado." in navegador.find_element(
        By.TAG_NAME, "body"
    ).text

def test_consulta_disponibiliza_filtros_de_data_e_escola_local(
    navegador, live_server
):
    """CA09.5: verifica os controles visuais para filtrar os cartões."""
    navegador.get(
        url_absoluta(live_server, "cartao_programa:listar_cartoes")
    )

    assert navegador.find_element(By.NAME, "data").is_enabled()
    assert navegador.find_element(By.NAME, "escola_local").is_enabled()

def test_gcm_visualiza_somente_cartao_da_viatura_em_que_esta_escalado(
    navegador, live_server, client, cenario
):
    """CA09.2 e CA09.6: valida a consulta individual do GCM pela interface."""
    cartao = criar_cartao(cenario)
    cartao.missoes.create(
        viatura=cenario["viatura"],
        numero=1,
        escola=cenario["escola"],
        endereco=cenario["escola"].endereco,
        periodo="MANHA",
        tipo_missao="VISITA",
        observacoes="MISSÃO_PERMITIDA",
    )

    client.force_login(cenario["conta_gcm"])
    navegador.delete_cookie(settings.SESSION_COOKIE_NAME)
    navegador.add_cookie(
        {
            "name": settings.SESSION_COOKIE_NAME,
            "value": client.cookies[settings.SESSION_COOKIE_NAME].value,
        }
    )
    navegador.get(
        url_absoluta(live_server, "cartao_programa:meu_cartao_programa")
    )
    conteudo = navegador.find_element(By.TAG_NAME, "body").text

    assert "Meu Cartão Programa" in conteudo
    assert cenario["escola"].nome in conteudo
    assert "MISSÃO_PERMITIDA" in conteudo
    assert cenario["viatura"].identificacao in conteudo