
from django.urls import path
from . import views

app_name = "usuarios"

urlpatterns = [

    # LISTAR USUÁRIOS
    path(
        "",
        views.listar_usuarios,
        name="listar"
    ),

    # CADASTRAR USUÁRIO
    path(
        "novo/",
        views.criar_usuario,
        name="criar"
    ),

    # EDITAR USUÁRIO
    path(
        "<int:pk>/editar/",
        views.editar_usuario,
        name="editar"
    ),

    # REDEFINIR SENHA
    path(
        "<int:pk>/redefinir-senha/",
        views.redefinir_senha,
        name="redefinir_senha"
    ),

    # NOTIFICAÇÕES
    path(
        "minhas-notificacoes/",
        views.minhas_notificacoes,
        name="minhas_notificacoes"
    ),

]
