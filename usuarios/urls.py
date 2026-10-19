from django.urls import path
from . import views

app_name = "usuarios"

urlpatterns = [
    path("", views.listar_usuarios, name="listar"),
    path("novo/", views.criar_usuario, name="criar"),
    
    path(
    "minhas-notificacoes/",
    views.minhas_notificacoes,
    name="minhas_notificacoes",
    ),
    
    path(
    "<int:pk>/editar/",
    views.editar_usuario,
    name="editar"
    ),
]