
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db import transaction
from django.shortcuts import redirect, render

from cartao_programa.models import IntegranteEquipe

from .forms import UsuarioForm
from .models import Usuario
from django.shortcuts import get_object_or_404, redirect, render
from cartao_programa.models import IntegranteEquipe



# =====================================================
# CRIAR USUÁRIO
# =====================================================

def criar_usuario(request):

    if request.method == "POST":
        form = UsuarioForm(request.POST)
    else:
        form = UsuarioForm()

    if request.method == "POST" and form.is_valid():

        matricula = form.cleaned_data["matricula"]
        perfil = form.cleaned_data["perfil"]

        equipe = form.cleaned_data.get("equipe")
        funcao_equipe = form.cleaned_data.get("funcao_equipe")

        # Verifica se a matrícula já está sendo
        # utilizada como login no Django.
        if User.objects.filter(
            username__iexact=matricula
        ).exists():

            form.add_error(
                "matricula",
                "Já existe um usuário com esta matrícula."
            )

        else:

            with transaction.atomic():

                # Cria a conta de autenticação.
                user = User.objects.create_user(
                    username=matricula,
                    password="1234",
                    email=form.cleaned_data.get("email") or ""
                )

                # Cria o usuário da RECOM.
                usuario = form.save(commit=False)

                usuario.user = user
                usuario.ativo = True
                usuario.primeiro_acesso = True

                usuario.save()

                # Se for GCM, vincula à equipe e função.
                if perfil == "GCM":

                    IntegranteEquipe.objects.create(
                        equipe=equipe,
                        gcm=usuario,
                        funcao_habitual=funcao_equipe
                    )

            messages.success(
                request,
                (
                    "Usuário cadastrado com sucesso. "
                    "A senha inicial para o primeiro acesso é 1234."
                )
            )

            return redirect("usuarios:listar")

    return render(
        request,
        "usuarios/form.html",
        {
            "form": form
        }
    )


# =====================================================
# LISTAR USUÁRIOS
# =====================================================

def listar_usuarios(request):

    usuarios = Usuario.objects.all().order_by("nome")

    paginator = Paginator(usuarios, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "usuarios/listar.html",
        {
            "page_obj": page_obj
        }
    )


# =====================================================
# EDITAR USUÁRIO
# =====================================================

def editar_usuario(request, pk):

    usuario = get_object_or_404(Usuario, pk=pk)

    form = UsuarioForm(
        request.POST if request.method == "POST" else None,
        instance=usuario
    )

    if request.method == "POST" and form.is_valid():

        matricula = form.cleaned_data["matricula"]
        perfil = form.cleaned_data["perfil"]

        # Verifica se a matrícula já pertence a outra conta.
        if User.objects.filter(
            username__iexact=matricula
        ).exclude(pk=usuario.user_id).exists():

            form.add_error(
                "matricula",
                "Esta matrícula já está sendo utilizada."
            )

        else:

            with transaction.atomic():

                usuario = form.save()

                # Atualiza também o login do Django.
                if usuario.user_id:
                    conta = usuario.user
                    conta.username = matricula
                    conta.email = usuario.email or ""
                    conta.save(
                        update_fields=["username", "email"]
                    )

                # Atualiza a equipe e função do GCM.
                if perfil == "GCM":

                    IntegranteEquipe.objects.update_or_create(
                        gcm=usuario,
                        defaults={
                            "equipe": form.cleaned_data["equipe"],
                            "funcao_habitual": form.cleaned_data["funcao_equipe"],
                        }
                    )

                else:
                    # Remove o vínculo de equipe se o usuário
                    # deixar de ter o perfil GCM.
                    IntegranteEquipe.objects.filter(
                        gcm=usuario
                    ).delete()

            messages.success(
                request,
                "Usuário atualizado com sucesso!"
            )

            return redirect("usuarios:listar")

    return render(
        request,
        "usuarios/form.html",
        {
            "form": form,
            "usuario": usuario,
            "edicao": True,
        }
    )


# =====================================================
# NOTIFICAÇÕES
# =====================================================

def minhas_notificacoes(request):

    return render(
        request,
        "usuarios/notificacoes.html"
    )
