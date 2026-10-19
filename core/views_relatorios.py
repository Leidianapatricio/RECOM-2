from django.core.paginator import Paginator
from django.db.models import (
    Case,
    IntegerField,
    Value,
    When,
)
from django.shortcuts import render

from escolas.models import (
    Escola,
    EscolaProblematica,
    TipoProblematica,
)
from usuarios.models import Usuario
from visitas.models import RondaVisita


# =============================================================
# PÁGINA PRINCIPAL DE RELATÓRIOS
# =============================================================

def relatorios(request):

    # =========================================================
    # INDICADORES GERAIS
    # =========================================================

    total_usuarios = Usuario.objects.count()

    total_escolas = Escola.objects.filter(
        ativa=True
    ).count()

    total_gcms = Usuario.objects.filter(
        perfil="GCM",
        ativo=True
    ).count()

    total_mediadores = Usuario.objects.filter(
        perfil="MEDIADOR",
        ativo=True
    ).count()


    # =========================================================
    # RESUMO DE PROBLEMÁTICAS
    # =========================================================

    total_problematicas = EscolaProblematica.objects.count()

    problematicas_ativas = EscolaProblematica.objects.filter(
        situacao="ATIVA"
    ).count()

    problematicas_em_acompanhamento = (
        EscolaProblematica.objects.filter(
            situacao="EM_ACOMPANHAMENTO"
        ).count()
    )

    problematicas_resolvidas = EscolaProblematica.objects.filter(
        situacao="RESOLVIDA"
    ).count()


    # =========================================================
    # RESUMO DE VISITAS
    # =========================================================

    total_visitas = RondaVisita.objects.count()

    visitas_sem_alteracao = RondaVisita.objects.filter(
        situacao="SEM_ALTERACAO"
    ).count()

    visitas_com_alteracao = RondaVisita.objects.filter(
        situacao="COM_ALTERACAO"
    ).count()


    # =========================================================
    # CONTEXTO
    # =========================================================

    contexto = {

        # Indicadores gerais
        "total_usuarios": total_usuarios,
        "total_escolas": total_escolas,
        "total_gcms": total_gcms,
        "total_mediadores": total_mediadores,

        # Problemáticas
        "total_problematicas": total_problematicas,
        "problematicas_ativas": problematicas_ativas,
        "problematicas_em_acompanhamento": (
            problematicas_em_acompanhamento
        ),
        "problematicas_resolvidas": problematicas_resolvidas,

        # Visitas
        "total_visitas": total_visitas,
        "visitas_sem_alteracao": visitas_sem_alteracao,
        "visitas_com_alteracao": visitas_com_alteracao,
    }

    return render(
        request,
        "relatorio/relatorios.html",
        contexto
    )


# =============================================================
# RELATÓRIO DETALHADO DE PROBLEMÁTICAS
# =============================================================

def relatorio_problematicas(request):

    # =========================================================
    # CONSULTA BASE
    # =========================================================

    problematicas = (
        EscolaProblematica.objects
        .select_related(
            "escola",
            "tipo_problematica"
        )
        .all()
        .order_by(
            "escola__nome",
            "tipo_problematica__nome"
        )
    )


    # =========================================================
    # FILTROS
    # =========================================================

    polo = request.GET.get(
        "polo",
        ""
    ).strip()

    escola_id = request.GET.get(
        "escola",
        ""
    ).strip()

    tipo_id = request.GET.get(
        "tipo",
        ""
    ).strip()

    situacao = request.GET.get(
        "situacao",
        ""
    ).strip()


    # =========================================================
    # APLICAÇÃO DOS FILTROS
    # =========================================================

    if polo:
        problematicas = problematicas.filter(
            escola__polo=polo
        )

    if escola_id:
        problematicas = problematicas.filter(
            escola_id=escola_id
        )

    if tipo_id:
        problematicas = problematicas.filter(
            tipo_problematica_id=tipo_id
        )

    if situacao:
        problematicas = problematicas.filter(
            situacao=situacao
        )


    # =========================================================
    # TOTAL
    # =========================================================

    total_problematicas = problematicas.count()


    # =========================================================
    # PAGINAÇÃO
    # =========================================================

    paginator = Paginator(
        problematicas,
        10
    )

    numero_pagina = request.GET.get(
        "page"
    )

    page_obj = paginator.get_page(
        numero_pagina
    )


    # =========================================================
    # ESCOLAS DO FILTRO
    # =========================================================

    escolas = Escola.objects.filter(
        ativa=True
    )

    if polo:
        escolas = escolas.filter(
            polo=polo
        )

    escolas = escolas.order_by(
        "nome"
    )


    # =========================================================
    # TIPOS DE PROBLEMÁTICA
    # =========================================================
    #
    # "Outras" permanece sempre por último.
    # =========================================================

    tipos_problematicas = (
        TipoProblematica.objects
        .filter(
            ativa=True
        )
        .annotate(
            ordem_outras=Case(
                When(
                    nome__iexact="Outras",
                    then=Value(1)
                ),
                default=Value(0),
                output_field=IntegerField()
            )
        )
        .order_by(
            "ordem_outras",
            "nome"
        )
    )


    # =========================================================
    # CONTEXTO
    # =========================================================

    contexto = {

        "page_obj": page_obj,

        "total_problematicas": total_problematicas,

        "polos": Escola.POLO_CHOICES,
        "escolas": escolas,
        "tipos_problematicas": tipos_problematicas,
        "situacoes": EscolaProblematica.SITUACAO_CHOICES,

        "polo_selecionado": polo,
        "escola_selecionada": escola_id,
        "tipo_selecionado": tipo_id,
        "situacao_selecionada": situacao,
    }

    return render(
        request,
        "relatorio/problematicas.html",
        contexto
    )


# =============================================================
# RELATÓRIO DETALHADO DE VISITAS
# =============================================================

def relatorio_visitas(request):

    # =========================================================
    # CONSULTA BASE
    # =========================================================

    visitas = (
        RondaVisita.objects
        .select_related(
            "escola"
        )
        .all()
        .order_by(
            "-data_visita",
            "-horario"
        )
    )


    # =========================================================
    # FILTROS
    # =========================================================

    polo = request.GET.get(
        "polo",
        ""
    ).strip()

    escola_id = request.GET.get(
        "escola",
        ""
    ).strip()

    equipe = request.GET.get(
        "equipe",
        ""
    ).strip()

    situacao = request.GET.get(
        "situacao",
        ""
    ).strip()

    data_inicial = request.GET.get(
        "data_inicial",
        ""
    ).strip()

    data_final = request.GET.get(
        "data_final",
        ""
    ).strip()


    # =========================================================
    # APLICAÇÃO DOS FILTROS
    # =========================================================

    if polo:
        visitas = visitas.filter(
            escola__polo=polo
        )

    if escola_id:
        visitas = visitas.filter(
            escola_id=escola_id
        )

    if equipe:
        visitas = visitas.filter(
            equipe=equipe
        )

    if situacao:
        visitas = visitas.filter(
            situacao=situacao
        )

    if data_inicial:
        visitas = visitas.filter(
            data_visita__gte=data_inicial
        )

    if data_final:
        visitas = visitas.filter(
            data_visita__lte=data_final
        )


    # =========================================================
    # TOTAL DE VISITAS
    # =========================================================

    total_visitas = visitas.count()


    # =========================================================
    # PAGINAÇÃO
    # =========================================================
    #
    # Exibe 10 visitas por página.
    # =========================================================

    paginator = Paginator(
        visitas,
        10
    )

    numero_pagina = request.GET.get(
        "page"
    )

    page_obj = paginator.get_page(
        numero_pagina
    )


    # =========================================================
    # ESCOLAS DISPONÍVEIS NO FILTRO
    # =========================================================

    escolas = Escola.objects.filter(
        ativa=True
    )

    if polo:
        escolas = escolas.filter(
            polo=polo
        )

    escolas = escolas.order_by(
        "nome"
    )


    # =========================================================
    # CONTEXTO
    # =========================================================

    contexto = {

        # Paginação
        "page_obj": page_obj,

        # Total encontrado
        "total_visitas": total_visitas,

        # Opções dos filtros
        "polos": Escola.POLO_CHOICES,
        "escolas": escolas,
        "equipes": RondaVisita.EQUIPE_CHOICES,
        "situacoes": RondaVisita.SITUACAO_CHOICES,

        # Valores selecionados
        "polo_selecionado": polo,
        "escola_selecionada": escola_id,
        "equipe_selecionada": equipe,
        "situacao_selecionada": situacao,
        "data_inicial": data_inicial,
        "data_final": data_final,
    }

    return render(
        request,
        "relatorio/visitas.html",
        contexto
    )