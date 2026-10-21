import pytest
from django.db import IntegrityError, transaction
from escolas.forms import EscolaForm, EscolaProblematicaForm
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
def escola():
    return Escola.objects.create(
        nome="Escola Municipal Horizonte",
        polo=1,
        endereco="Rua das Acácias, 100",
    )

def test_escola_tem_valores_padrao_esperados():
    """Valida os valores iniciais definidos pelo modelo de escola."""
    escola = Escola.objects.create(
        nome="Escola Municipal Padrão",
        polo=1,
        endereco="Rua Principal, 10",
    )

    assert escola.ativa is True
    assert escola.monitoramento is False
    assert escola.botao_panico is False
    assert escola.quantidade_alunos == 0
    assert escola.quantidade_alunos_pcd == 0
    assert str(escola) == escola.nome

def test_formulario_de_escola_aceita_dados_validos_e_normaliza_nome(
    dados_escola,
):
    """Valida dados corretos e a remoção de espaços no nome da escola."""
    dados_escola["nome"] = "  Escola Municipal Horizonte  "

    formulario = EscolaForm(data=dados_escola)

    assert formulario.is_valid()
    assert formulario.cleaned_data["nome"] == "Escola Municipal Horizonte"

def test_formulario_de_escola_rejeita_nome_duplicado_sem_distinguir_caixa(
    dados_escola,
):
    """Valida que nomes iguais não sejam aceitos com letras diferentes."""
    Escola.objects.create(
        nome="ESCOLA MUNICIPAL HORIZONTE",
        polo=1,
        endereco="Rua Principal, 10",
    )
    dados_escola["nome"] = "escola municipal horizonte"

    formulario = EscolaForm(data=dados_escola)

    assert not formulario.is_valid()
    assert "nome" in formulario.errors

def test_formulario_de_escola_rejeita_quantidade_pcd_maior_que_total(
    dados_escola,
):
    """Valida que alunos PCD não superem o total de alunos informado."""
    dados_escola["quantidade_alunos"] = "10"
    dados_escola["quantidade_alunos_pcd"] = "11"

    formulario = EscolaForm(data=dados_escola)

    assert not formulario.is_valid()
    assert "quantidade_alunos_pcd" in formulario.errors

def test_formulario_de_escola_aceita_quantidades_iguais_a_zero(dados_escola):
    """Valida que as quantidades de alunos possam ser iguais a zero."""
    dados_escola["quantidade_alunos"] = "0"
    dados_escola["quantidade_alunos_pcd"] = "0"

    formulario = EscolaForm(data=dados_escola)

    assert formulario.is_valid()

def test_formulario_de_problematica_exibe_apenas_tipos_ativos_em_ordem():
    """Valida a seleção e a ordenação dos tipos ativos de problemática."""
    TipoProblematica.objects.create(nome="Vandalismo")
    TipoProblematica.objects.create(nome="Outras")
    TipoProblematica.objects.create(nome="Iluminação insuficiente")
    TipoProblematica.objects.create(nome="Tipo inativo", ativa=False)

    formulario = EscolaProblematicaForm()

    tipos = list(formulario.fields["tipo_problematica"].queryset)
    assert [tipo.nome for tipo in tipos] == [
        "Iluminação insuficiente",
        "Vandalismo",
        "Outras",
    ]

def test_formulario_de_problematica_converte_e_valida_situacao(escola):
    """Valida os valores de tipo e situação recebidos pelo formulário."""
    tipo = TipoProblematica.objects.create(nome="Vandalismo")
    formulario = EscolaProblematicaForm(
        data={
            "tipo_problematica": str(tipo.pk),
            "situacao": "RESOLVIDA",
            "observacoes": "Muro recuperado.",
        }
    )

    assert formulario.is_valid()
    assert formulario.cleaned_data["tipo_problematica"] == tipo
    assert formulario.cleaned_data["situacao"] == "RESOLVIDA"

def test_modelo_de_problematica_define_situacao_ativa_e_representacao(escola):
    """Valida a situação inicial e o texto representativo da problemática."""
    tipo = TipoProblematica.objects.create(nome="Vandalismo")

    problematica = EscolaProblematica.objects.create(
        escola=escola,
        tipo_problematica=tipo,
    )

    assert problematica.situacao == "ATIVA"
    assert str(problematica) == f"{escola.nome} - {tipo.nome}"

def test_mesmo_tipo_de_problematica_nao_pode_ser_duplicado_na_escola(escola):
    """Valida a restrição de tipo repetido em uma mesma escola."""
    tipo = TipoProblematica.objects.create(nome="Vandalismo")
    EscolaProblematica.objects.create(escola=escola, tipo_problematica=tipo)

    with pytest.raises(IntegrityError), transaction.atomic():
        EscolaProblematica.objects.create(escola=escola, tipo_problematica=tipo)

def test_mesmo_tipo_de_problematica_pode_existir_em_escolas_distintas(escola):
    """Valida que escolas distintas possam registrar o mesmo tipo."""
    outra_escola = Escola.objects.create(
        nome="Escola Municipal Aurora",
        polo=2,
        endereco="Rua Secundária, 20",
    )
    tipo = TipoProblematica.objects.create(nome="Vandalismo")

    EscolaProblematica.objects.create(escola=escola, tipo_problematica=tipo)
    EscolaProblematica.objects.create(
        escola=outra_escola,
        tipo_problematica=tipo,
    )

    assert EscolaProblematica.objects.filter(tipo_problematica=tipo).count() == 2
