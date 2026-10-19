import json
import os
import sys

from dotenv import load_dotenv


# ============================================================
# CAMINHOS DOS ARQUIVOS
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ARQUIVO_ENV = os.path.join(
    BASE_DIR,
    ".env.supabase",
)

ARQUIVO_JSON = os.path.join(
    BASE_DIR,
    "recom_dados_utf8.json",
)


# ============================================================
# VERIFICA SE OS ARQUIVOS EXISTEM
# ============================================================

if not os.path.exists(ARQUIVO_ENV):
    print("ERRO: arquivo .env.supabase não encontrado.")
    sys.exit(1)


if not os.path.exists(ARQUIVO_JSON):
    print("ERRO: arquivo recom_dados_utf8.json não encontrado.")
    sys.exit(1)


# ============================================================
# CARREGA EXPLICITAMENTE O .ENV DO SUPABASE
# ============================================================

load_dotenv(
    ARQUIVO_ENV,
    override=True,
)


# ============================================================
# CONFIRMA QUE O HOST É DO SUPABASE
# ============================================================

host = os.getenv(
    "POSTGRES_HOST",
    "",
)


print("=" * 60)
print("VERIFICAÇÃO DA CONEXÃO")
print("=" * 60)

print(
    "Host:",
    host,
)


if "supabase.com" not in host.lower():

    print()
    print("OPERAÇÃO CANCELADA.")
    print(
        "O banco configurado não parece ser o Supabase."
    )

    sys.exit(1)


# ============================================================
# INICIALIZA O DJANGO
# SOMENTE DEPOIS DE CARREGAR .env.supabase
# ============================================================

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "recom.settings",
)

import django

django.setup()


# ============================================================
# IMPORTA OS MODELOS
# ============================================================

from django.db import transaction

from escolas.models import (
    Escola,
    EscolaProblematica,
    TipoProblematica,
)

from visitas.models import RondaVisita


# ============================================================
# CARREGA O JSON CORRETO EM UTF-8
# ============================================================

with open(
    ARQUIVO_JSON,
    "r",
    encoding="utf-8",
) as arquivo:

    dados = json.load(
        arquivo
    )


# ============================================================
# SEPARA OS DADOS POR MODELO
# ============================================================

dados_escolas = [
    item
    for item in dados
    if item["model"] == "escolas.escola"
]


dados_tipos_problematicas = [
    item
    for item in dados
    if item["model"] == "escolas.tipoproblematica"
]


dados_escolas_problematicas = [
    item
    for item in dados
    if item["model"] == "escolas.escolaproblematica"
]


dados_visitas = [
    item
    for item in dados
    if item["model"] == "visitas.rondavisita"
]


# ============================================================
# MOSTRA AS QUANTIDADES DO ARQUIVO
# ============================================================

print()

print("=" * 60)
print("REGISTROS ENCONTRADOS NO ARQUIVO")
print("=" * 60)


print(
    "Escolas:",
    len(dados_escolas),
)


print(
    "Tipos de problemática:",
    len(dados_tipos_problematicas),
)


print(
    "Problemáticas das escolas:",
    len(dados_escolas_problematicas),
)


print(
    "Visitas:",
    len(dados_visitas),
)


# ============================================================
# MOSTRA ALGUNS REGISTROS ATUAIS DO SUPABASE
# ============================================================

print()

print("=" * 60)
print("DADOS ATUAIS NO SUPABASE")
print("=" * 60)


for escola in Escola.objects.order_by("id")[:10]:

    print(
        escola.id,
        "|",
        escola.nome,
        "|",
        escola.bairro,
        "|",
        escola.gestor,
    )


# ============================================================
# VERIFICA SE O USUÁRIO PEDIU PARA APLICAR
# ============================================================

aplicar = "--aplicar" in sys.argv


# ============================================================
# MODO DE VERIFICAÇÃO
# ============================================================

if not aplicar:

    print()

    print("=" * 60)
    print("MODO DE VERIFICAÇÃO")
    print("=" * 60)

    print()
    print("Nenhum dado foi alterado.")

    print()
    print(
        "Confira se o host acima pertence ao Supabase."
    )

    print()
    print(
        "Se estiver correto, execute:"
    )

    print()

    print(
        "python -X utf8 corrigir_supabase_utf8.py --aplicar"
    )

    sys.exit(0)


# ============================================================
# INÍCIO DA CORREÇÃO
# ============================================================

print()

print("=" * 60)
print("INICIANDO CORREÇÃO")
print("=" * 60)


escolas_atualizadas = 0

tipos_atualizados = 0

problematicas_atualizadas = 0

visitas_atualizadas = 0

nao_encontrados = []


# ============================================================
# TRANSAÇÃO
#
# Se ocorrer erro durante a atualização,
# o Django desfaz as alterações dessa execução.
# ============================================================

with transaction.atomic():


    # ========================================================
    # ESCOLAS
    # ========================================================

    for item in dados_escolas:

        pk = item["pk"]

        campos = item["fields"]


        atualizado = Escola.objects.filter(
            pk=pk
        ).update(

            nome=campos.get(
                "nome",
                "",
            ),

            endereco=campos.get(
                "endereco",
                "",
            ),

            bairro=campos.get(
                "bairro",
                "",
            ),

            gestor=campos.get(
                "gestor",
                "",
            ),

            telefone=campos.get(
                "telefone",
                "",
            ),

            modalidade=campos.get(
                "modalidade",
                "",
            ),

            observacoes=campos.get(
                "observacoes",
                "",
            ),
        )


        if atualizado:

            escolas_atualizadas += 1

        else:

            nao_encontrados.append(
                f"Escola ID {pk}"
            )


    # ========================================================
    # TIPOS DE PROBLEMÁTICAS
    # ========================================================

    for item in dados_tipos_problematicas:

        pk = item["pk"]

        campos = item["fields"]


        atualizado = TipoProblematica.objects.filter(
            pk=pk
        ).update(

            nome=campos.get(
                "nome",
                "",
            ),

            descricao=campos.get(
                "descricao",
                "",
            ),
        )


        if atualizado:

            tipos_atualizados += 1

        else:

            nao_encontrados.append(
                f"TipoProblematica ID {pk}"
            )


    # ========================================================
    # PROBLEMÁTICAS DAS ESCOLAS
    # ========================================================

    for item in dados_escolas_problematicas:

        pk = item["pk"]

        campos = item["fields"]


        atualizado = EscolaProblematica.objects.filter(
            pk=pk
        ).update(

            observacoes=campos.get(
                "observacoes",
                "",
            ),
        )


        if atualizado:

            problematicas_atualizadas += 1

        else:

            nao_encontrados.append(
                f"EscolaProblematica ID {pk}"
            )



# ============================================================
# RESULTADO
# ============================================================

print()

print("=" * 60)
print("CORREÇÃO CONCLUÍDA")
print("=" * 60)


print(
    "Escolas atualizadas:",
    escolas_atualizadas,
)


print(
    "Tipos de problemática atualizados:",
    tipos_atualizados,
)


print(
    "Problemáticas atualizadas:",
    problematicas_atualizadas,
)




# ============================================================
# REGISTROS NÃO ENCONTRADOS
# ============================================================

if nao_encontrados:

    print()

    print(
        "Registros não encontrados no Supabase:"
    )

    for registro in nao_encontrados:

        print(
            "-",
            registro,
        )

else:

    print()

    print(
        "Todos os registros existentes foram encontrados."
    )


# ============================================================
# CONFERÊNCIA FINAL
# ============================================================

print()

print("=" * 60)
print("DADOS APÓS A CORREÇÃO")
print("=" * 60)


for escola in Escola.objects.order_by("id")[:10]:

    print(
        escola.id,
        "|",
        escola.nome,
        "|",
        escola.bairro,
        "|",
        escola.gestor,
    )