from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from cartao_programa.models import IntegranteEquipe

from .forms import UsuarioForm
from .models import Usuario


# =====================================================
# PERMISSÕES DE ACESSO
# =====================================================

def acesso_gestao_usuarios(view_func):
    """Permite a administração de cadastros por ADMIN e COORDENADOR."""

    @login_required(login_url="core:login")
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)

        usuario_logado = Usuario.objects.filter(
            user=request.user,
            ativo=True,
            perfil__in=["ADMIN", "COORDENADOR"],
        ).first()

        if usuario_logado is None:
            messages.error(
                request,
                "Você não possui permissão para gerenciar usuários.",
            )
            return redirect("core:home")

        if usuario_logado.primeiro_acesso:
            return redirect("core:primeiro_acesso")

        return view_func(request, *args, **kwargs)

    return wrapper


def acesso_administrador(view_func):
    """Restringe a redefinição de senhas a administradores ativos."""

    @login_required(login_url="core:login")
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)

        usuario_logado = Usuario.objects.filter(
            user=request.user,
            perfil="ADMIN",
            ativo=True,
        ).first()

        if usuario_logado is None:
            messages.error(
                request,
                "Você não possui permissão para redefinir senhas.",
            )
            return redirect("core:home")

        if usuario_logado.primeiro_acesso:
            return redirect("core:primeiro_acesso")

        return view_func(request, *args, **kwargs)

    return wrapper


# =====================================================
# CRIAR USUÁRIO
# =====================================================

@acesso_gestao_usuarios
def criar_usuario(request):
    form = UsuarioForm(request.POST if request.method == "POST" else None)

    if request.method == "POST" and form.is_valid():
        matricula = form.cleaned_data["matricula"]
        perfil = form.cleaned_data["perfil"]
        equipe = form.cleaned_data.get("equipe")
        funcao_equipe = form.cleaned_data.get("funcao_equipe")

        if User.objects.filter(username__iexact=matricula).exists():
            form.add_error("matricula", "Já existe um usuário com esta matrícula.")
        elif perfil == "GCM" and (not equipe or not funcao_equipe):
            if not equipe:
                form.add_error("equipe", "Selecione a equipe do GCM.")
            if not funcao_equipe:
                form.add_error("funcao_equipe", "Selecione a função do GCM.")
        else:
            with transaction.atomic():
                conta = User.objects.create_user(
                    username=matricula,
                    password="1234",
                    email=form.cleaned_data.get("email") or "",
                )

                usuario = form.save(commit=False)
                usuario.user = conta
                usuario.ativo = True
                usuario.primeiro_acesso = True
                usuario.save()
                form.save_m2m()

                if perfil == "GCM":
                    IntegranteEquipe.objects.create(
                        equipe=equipe,
                        gcm=usuario,
                        funcao_habitual=funcao_equipe,
                    )

            messages.success(
                request,
                "Usuário cadastrado com sucesso. "
                "A senha inicial para o primeiro acesso é 1234.",
            )
            return redirect("usuarios:listar")

    return render(request, "usuarios/form.html", {"form": form})


# =====================================================
# LISTAR USUÁRIOS
# =====================================================

@acesso_gestao_usuarios
def listar_usuarios(request):
    if request.user.is_superuser:
        perfil_logado = "ADMIN"
    else:
        perfil_logado = request.user.usuario.perfil

    usuarios = Usuario.objects.all().order_by("nome")
    paginator = Paginator(usuarios, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "usuarios/listar.html",
        {
            "page_obj": page_obj,
            "perfil_logado": perfil_logado,
        },
    )


# =====================================================
# EDITAR USUÁRIO
# =====================================================

@acesso_gestao_usuarios
def editar_usuario(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    form = UsuarioForm(
        request.POST if request.method == "POST" else None,
        instance=usuario,
    )

    if request.method == "POST" and form.is_valid():
        matricula = form.cleaned_data["matricula"]
        perfil = form.cleaned_data["perfil"]
        equipe = form.cleaned_data.get("equipe")
        funcao_equipe = form.cleaned_data.get("funcao_equipe")

        if User.objects.filter(username__iexact=matricula).exclude(
            pk=usuario.user_id
        ).exists():
            form.add_error("matricula", "Esta matrícula já está sendo utilizada.")
        elif perfil == "GCM" and (not equipe or not funcao_equipe):
            if not equipe:
                form.add_error("equipe", "Selecione a equipe do GCM.")
            if not funcao_equipe:
                form.add_error("funcao_equipe", "Selecione a função do GCM.")
        else:
            with transaction.atomic():
                usuario = form.save()

                if usuario.user_id:
                    conta = usuario.user
                    conta.username = matricula
                    conta.email = usuario.email or ""
                    conta.save(update_fields=["username", "email"])

                if perfil == "GCM":
                    IntegranteEquipe.objects.update_or_create(
                        gcm=usuario,
                        defaults={
                            "equipe": equipe,
                            "funcao_habitual": funcao_equipe,
                        },
                    )
                else:
                    IntegranteEquipe.objects.filter(gcm=usuario).delete()

            messages.success(request, "Usuário atualizado com sucesso!")
            return redirect("usuarios:listar")

    return render(
        request,
        "usuarios/form.html",
        {"form": form, "usuario": usuario, "edicao": True},
    )


# =====================================================
# NOTIFICAÇÕES
# =====================================================

@login_required(login_url="core:login")
def minhas_notificacoes(request):
    if not request.user.is_superuser:
        usuario_logado = Usuario.objects.filter(
            user=request.user, ativo=True
        ).first()
        if usuario_logado is None:
            messages.error(request, "Usuário sem acesso ativo ao sistema.")
            return redirect("core:login")
        if usuario_logado.primeiro_acesso:
            return redirect("core:primeiro_acesso")

    return render(request, "usuarios/notificacoes.html")


# =====================================================
# REDEFINIR SENHA — EXCLUSIVO DO ADMINISTRADOR
# =====================================================

@login_required(login_url="core:login")
@require_POST
@acesso_administrador
def redefinir_senha(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)

    if not usuario.user_id:
        messages.error(
            request,
            "Este usuário não possui uma conta de login vinculada.",
        )
        return redirect("usuarios:listar")

    if usuario.user_id == request.user.pk:
        messages.error(
            request,
            "Para alterar sua própria senha, utilize a opção de alteração de senha.",
        )
        return redirect("usuarios:listar")

    with transaction.atomic():
        conta = usuario.user
        conta.set_password("1234")
        conta.save(update_fields=["password"])

        usuario.primeiro_acesso = True
        usuario.save(update_fields=["primeiro_acesso"])

    messages.success(
        request,
        f"Senha de {usuario.nome} redefinida com sucesso. "
        "A senha provisória é 1234.",
    )
    return redirect("usuarios:listar")
