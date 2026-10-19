from django.urls import path

from . import views
from . import views_relatorios


app_name = "core"


urlpatterns = [

    path(
        "",
        views.home,
        name="home"
    ),

    path(
        "login/",
        views.login_view,
        name="login"
    ),

    path(
        "primeiro-acesso/",
        views.primeiro_acesso,
        name="primeiro_acesso"
    ),

    path(
        "logout/",
        views.logout_view,
        name="logout"
    ),

    path(
        "dashboard/admin/",
        views.dashboard_admin,
        name="dashboard_admin"
    ),

    path(
        "dashboard/coordenador/",
        views.dashboard_coordenador,
        name="dashboard_coordenador"
    ),

    path(
        "dashboard/gcm/",
        views.dashboard_gcm,
        name="dashboard_gcm"
    ),

    path(
        "dashboard/mediador/",
        views.dashboard_mediador,
        name="dashboard_mediador"
    ),

    # =========================================================
    # RELATÓRIOS
    # =========================================================

    # Página principal dos relatórios
    path(
        "relatorios/",
        views_relatorios.relatorios,
        name="relatorios"
    ),

    # Relatório de problemáticas
    path(
        "relatorios/problematicas/",
        views_relatorios.relatorio_problematicas,
        name="relatorio_problematicas"
    ),

    # Relatório de visitas
    path(
        "relatorios/visitas/",
        views_relatorios.relatorio_visitas,
        name="relatorio_visitas"
    ),
]