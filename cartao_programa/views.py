from functools import wraps
from django import forms as django_forms

from django.contrib import messages
from django.db.models.deletion import ProtectedError, RestrictedError
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect

from django.contrib import messages
from django.db import transaction

from django.contrib.auth.decorators import login_required

from django.core.exceptions import (

    PermissionDenied,

    ValidationError,

)

from django.db.models import ProtectedError
from django.http import HttpResponseForbidden
from django.shortcuts import (

    render,

    redirect,

    get_object_or_404,

)

from usuarios.models import Usuario


from .models import (

    Equipe,

    IntegranteEquipe,

    Plantao,

    ViaturaPlantao,

    EfetivoViatura,

    CartaoPrograma,

    MissaoCartao,

)

from .forms import (

    EquipeForm,

    IntegranteEquipeForm,

    PlantaoForm,

    ViaturaPlantaoForm,

    EfetivoViaturaForm,

    CartaoProgramaForm,

    MissaoCartaoForm,
    MissoesEmLoteForm,

)
from cartao_programa import forms

# =====================================================

# CONTROLE DE ACESSO - GESTÃO DO CARTÃO PROGRAMA

# =====================================================

def acesso_gestao_equipes(view_func):

    @wraps(view_func)

    @login_required

    def wrapper(request, *args, **kwargs):

        # Superusuários ativos do Django possuem acesso.

        if (

            request.user.is_active

            and request.user.is_superuser

        ):

            return view_func(request, *args, **kwargs)

        # Verifica o perfil do usuário no RECOM.

        usuario = getattr(

            request.user,

            "usuario",

            None

        )

        if (

            not request.user.is_active

            or not usuario

            or not usuario.ativo

            or usuario.perfil not in [

                "ADMIN",

                "COORDENADOR"

            ]

        ):

            raise PermissionDenied(

                "Você não possui permissão "

                "para gerenciar equipes e plantões."

            )

        return view_func(request, *args, **kwargs)

    return wrapper

# =====================================================

# LISTAR EQUIPES

# =====================================================

def fluxo_cartao_ativo(request):
    return request.GET.get("fluxo") == "cartao"


def redirecionar_fluxo(request, rota, **kwargs):
    resposta = redirect(rota, **kwargs)
    if fluxo_cartao_ativo(request):
        resposta["Location"] += ("&" if "?" in resposta["Location"] else "?") + "fluxo=cartao"
    return resposta


@acesso_gestao_equipes
def listar_equipes(request):

    equipes = (

        Equipe.objects.all()

        .order_by("nome")

    )

    return render(

        request,

        "cartao_programa/equipes/listar.html",

        {

            "equipes": equipes

        }

    )

# =====================================================

# CADASTRAR EQUIPE

# =====================================================

@acesso_gestao_equipes

def criar_equipe(request):

    if request.method == "POST":

        form = EquipeForm(

            request.POST

        )

        if form.is_valid():

            form.save()

            messages.success(

                request,

                "Equipe cadastrada com sucesso!"

            )

            return redirect(

                "cartao_programa:listar_equipes"

            )

    else:

        form = EquipeForm()

    return render(

        request,

        "cartao_programa/equipes/form.html",

        {

            "form": form,

            "titulo": "Cadastrar Equipe"

        }

    )

# =====================================================

# EDITAR EQUIPE

# =====================================================

@acesso_gestao_equipes

def editar_equipe(request, pk):

    equipe = get_object_or_404(

        Equipe,

        pk=pk

    )

    if request.method == "POST":

        form = EquipeForm(

            request.POST,

            instance=equipe

        )

        if form.is_valid():

            form.save()

            messages.success(

                request,

                "Equipe atualizada com sucesso!"

            )

            return redirect(

                "cartao_programa:listar_equipes"

            )

    else:

        form = EquipeForm(

            instance=equipe

        )

    return render(

        request,

        "cartao_programa/equipes/form.html",

        {

            "form": form,

            "titulo": "Editar Equipe"

        }

    )

# =====================================================

# LISTAR INTEGRANTES DE UMA EQUIPE

# =====================================================

@acesso_gestao_equipes

def listar_integrantes(request, equipe_id):

    equipe = get_object_or_404(

        Equipe,

        pk=equipe_id

    )

    integrantes = (

        IntegranteEquipe.objects

        .filter(equipe=equipe)

        .select_related("gcm")

        .order_by("gcm__nome")

    )

    return render(

        request,

        "cartao_programa/equipes/integrantes.html",

        {

            "equipe": equipe,

            "integrantes": integrantes

        }

    )

# =====================================================

# ADICIONAR GCM A UMA EQUIPE

# =====================================================

@acesso_gestao_equipes

def adicionar_integrante(request, equipe_id):

    equipe = get_object_or_404(

        Equipe,

        pk=equipe_id,

        ativa=True

    )

    if request.method == "POST":

        form = IntegranteEquipeForm(

            request.POST

        )

    else:

        form = IntegranteEquipeForm()

    # A equipe é determinada pela URL.

    form.fields["equipe"].initial = equipe.pk

    form.fields["equipe"].disabled = True

    if (

        request.method == "POST"

        and form.is_valid()

    ):

        integrante = form.save(

            commit=False

        )

        integrante.equipe = equipe

        integrante.save()

        messages.success(

            request,

            "GCM vinculado à equipe com sucesso!"

        )

        return redirect(

            "cartao_programa:listar_integrantes",

            equipe_id=equipe.pk

        )

    return render(

        request,

        "cartao_programa/equipes/form_integrante.html",

        {

            "form": form,

            "equipe": equipe,

            "titulo": "Adicionar GCM",

            "edicao": False

        }

    )

# =====================================================

# EDITAR FUNÇÃO HABITUAL DO INTEGRANTE

# =====================================================

@acesso_gestao_equipes

def editar_integrante(request, equipe_id, pk):

    equipe = get_object_or_404(

        Equipe,

        pk=equipe_id

    )

    integrante = get_object_or_404(

        IntegranteEquipe,

        pk=pk,

        equipe=equipe

    )

    if request.method == "POST":

        form = IntegranteEquipeForm(

            request.POST,

            instance=integrante

        )

    else:

        form = IntegranteEquipeForm(

            instance=integrante

        )

    # Somente a função habitual pode ser alterada.

    form.fields["equipe"].disabled = True

    form.fields["gcm"].disabled = True

    if (

        request.method == "POST"

        and form.is_valid()

    ):

        form.save()

        messages.success(

            request,

            "Função habitual do GCM "

            "atualizada com sucesso!"

        )

        return redirect(

            "cartao_programa:listar_integrantes",

            equipe_id=equipe.pk

        )

    return render(

        request,

        "cartao_programa/equipes/form_integrante.html",

        {

            "form": form,

            "equipe": equipe,

            "integrante": integrante,

            "titulo": "Editar Integrante",

            "edicao": True

        }

    )

# =====================================================

# REMOVER INTEGRANTE DA EQUIPE FIXA

# =====================================================

@acesso_gestao_equipes

def remover_integrante(request, equipe_id, pk):

    equipe = get_object_or_404(

        Equipe,

        pk=equipe_id

    )

    integrante = get_object_or_404(

        IntegranteEquipe.objects.select_related("gcm"),

        pk=pk,

        equipe=equipe

    )

    # A remoção somente acontece após confirmação.

    if request.method == "POST":

        nome_gcm = integrante.gcm.nome

        # Remove apenas o vínculo com a equipe.

        integrante.delete()

        messages.success(

            request,

            f"O GCM {nome_gcm} foi removido "

            "da equipe com sucesso!"

        )

        return redirect(

            "cartao_programa:listar_integrantes",

            equipe_id=equipe.pk

        )

    return render(

        request,

        "cartao_programa/equipes/confirmar_remocao_integrante.html",

        {

            "equipe": equipe,

            "integrante": integrante

        }

    )

# =====================================================

# LISTAR PLANTÕES

# =====================================================

@acesso_gestao_equipes

def listar_plantoes(request):

    plantoes = (

        Plantao.objects.all()

        .order_by("-data", "-pk")

    )

    return render(

        request,

        "cartao_programa/plantoes/listar.html",

        {

            "plantoes": plantoes,
            "fluxo_cartao": fluxo_cartao_ativo(request)

        }

    )

# =====================================================

# CADASTRAR PLANTÃO

# =====================================================

@acesso_gestao_equipes

def criar_plantao(request):

    if request.method == "POST":

        form = PlantaoForm(

            request.POST

        )

        if form.is_valid():

            plantao = form.save()
            messages.success(request, "Plantão cadastrado com sucesso!")
            if fluxo_cartao_ativo(request):
                return redirecionar_fluxo(request, "cartao_programa:listar_viaturas", plantao_id=plantao.pk)
            return redirect("cartao_programa:listar_plantoes")

    else:

        form = PlantaoForm()

    return render(

        request,

        "cartao_programa/plantoes/form.html",

        {

            "form": form,

            "titulo": "Cadastrar Plantão",
            "fluxo_cartao": fluxo_cartao_ativo(request)

        }

    )

# =====================================================

# LISTAR VIATURAS DE UM PLANTÃO

# =====================================================

@acesso_gestao_equipes

def listar_viaturas(request, plantao_id):

    plantao = get_object_or_404(

        Plantao,

        pk=plantao_id

    )

    viaturas = (

        ViaturaPlantao.objects

        .filter(plantao=plantao)

        .select_related("equipe")

        .order_by("identificacao")

    )

    return render(

        request,

        "cartao_programa/viaturas/listar.html",

        {

            "plantao": plantao,

            "viaturas": viaturas,
            "fluxo_cartao": fluxo_cartao_ativo(request),
        }

    )

# =====================================================

# FUNÇÃO AUXILIAR - EXIBIR ERROS DO MODELO

# =====================================================

def adicionar_erros_validacao(form, erro):

    # Converte erros do full_clean() em erros

    # exibidos no próprio formulário.

    if hasattr(erro, "error_dict"):

        for campo, erros in erro.error_dict.items():

            # Erros gerais do modelo.

            if campo == "__all__":

                form.add_error(None, erros)

            # Erros de campos presentes no formulário.

            elif campo in form.fields:

                form.add_error(campo, erros)

            # Erros de campos não exibidos no formulário.

            else:

                form.add_error(None, erros)

    else:

        form.add_error(None, erro)

# =====================================================

# CADASTRAR VIATURA EM UM PLANTÃO

# =====================================================

@acesso_gestao_equipes

def criar_viatura(request, plantao_id):

    plantao = get_object_or_404(

        Plantao,

        pk=plantao_id

    )

    if request.method == "POST":

        # Passa o plantão para o formulário,

        # permitindo validar identificações duplicadas.

        form = ViaturaPlantaoForm(

            request.POST,

            plantao=plantao

        )

        if form.is_valid():

            viatura = form.save(

                commit=False

            )

            # O plantão é definido pela URL.

            viatura.plantao = plantao

            try:

                # Valida as regras do modelo.

                viatura.full_clean()

            except ValidationError as erro:

                # Exibe os erros no formulário.

                adicionar_erros_validacao(

                    form,

                    erro

                )

            else:

                viatura.save()

                messages.success(

                    request,

                    "Viatura cadastrada no plantão "

                    "com sucesso!"

                )

                if request.GET.get("fluxo") == "cartao":
                    resposta = redirect(
                        "cartao_programa:listar_efetivo",
                        plantao_id=plantao.pk,
                        viatura_id=viatura.pk
                    )
                    resposta["Location"] += ("&" if "?" in resposta["Location"] else "?") + "fluxo=cartao"
                    return resposta

                return redirecionar_fluxo(
                    request,
                    "cartao_programa:listar_viaturas",
                    plantao_id=plantao.pk
                )

    else:

        form = ViaturaPlantaoForm(

            plantao=plantao

        )

    return render(

        request,

        "cartao_programa/viaturas/form.html",

        {

            "form": form,

            "plantao": plantao,

            "titulo": "Cadastrar Viatura",
            "fluxo_cartao": fluxo_cartao_ativo(request),

            "edicao": False

        }

    )

# =====================================================

# EDITAR VIATURA DE UM PLANTÃO

# =====================================================

@acesso_gestao_equipes

def editar_viatura(request, plantao_id, pk):

    plantao = get_object_or_404(

        Plantao,

        pk=plantao_id

    )

    viatura = get_object_or_404(

        ViaturaPlantao,

        pk=pk,

        plantao=plantao

    )

    if request.method == "POST":

        # Mantém o plantão e a viatura original.

        form = ViaturaPlantaoForm(

            request.POST,

            instance=viatura,

            plantao=plantao

        )

        if form.is_valid():

            viatura_atualizada = form.save(

                commit=False

            )

            viatura_atualizada.plantao = plantao

            try:

                # Valida as regras do modelo.

                viatura_atualizada.full_clean()

            except ValidationError as erro:

                # Apresenta os erros no formulário.

                adicionar_erros_validacao(

                    form,

                    erro

                )

            else:

                viatura_atualizada.save()

                messages.success(

                    request,

                    "Viatura atualizada com sucesso!"

                )

                return redirecionar_fluxo(

                    request,

                    "cartao_programa:listar_viaturas",

                    plantao_id=plantao.pk

                )

    else:

        form = ViaturaPlantaoForm(

            instance=viatura,

            plantao=plantao

        )

    return render(

        request,

        "cartao_programa/viaturas/form.html",

        {

            "form": form,

            "plantao": plantao,

            "viatura": viatura,

            "titulo": "Editar Viatura",
            "fluxo_cartao": fluxo_cartao_ativo(request),

            "edicao": True

        }

    )

# =====================================================

# EFETIVO DE CADA VIATURA

# =====================================================

@acesso_gestao_equipes

def listar_efetivo(request, plantao_id, viatura_id):

    viatura = get_object_or_404(

        ViaturaPlantao.objects.select_related("plantao", "equipe"),

        pk=viatura_id,

        plantao_id=plantao_id,

    )

    integrantes = (

        EfetivoViatura.objects.filter(viatura=viatura)

        .select_related("gcm")

        .order_by("funcao", "gcm__nome")

    )

    funcoes = set(integrantes.values_list("funcao", flat=True))

    return render(

        request,

        "cartao_programa/efetivo/listar.html",

        {

            "plantao": viatura.plantao,

            "viatura": viatura,

            "integrantes": integrantes,

            "pode_adicionar": integrantes.count() < 4,

            "possui_comandante": "C" in funcoes,

            "possui_motorista": "M" in funcoes,
            "fluxo_cartao": fluxo_cartao_ativo(request),

        },

    )

def _validar_e_salvar_efetivo(form, viatura):

    """Aplica as validações do modelo antes de gravar o integrante."""

    integrante = form.save(commit=False)

    integrante.viatura = viatura

    # O limite de quatro pessoas vale para cada viatura.

    outros = EfetivoViatura.objects.filter(viatura=viatura).exclude(

        pk=integrante.pk

    )

    if outros.count() >= 4:

        form.add_error(None, "Esta viatura já possui quatro integrantes.")

        return False

    try:

        integrante.full_clean()

    except ValidationError as erro:

        adicionar_erros_validacao(form, erro)

        return False

    integrante.save()

    return True

@acesso_gestao_equipes

def adicionar_efetivo(request, plantao_id, viatura_id):

    viatura = get_object_or_404(

        ViaturaPlantao.objects.select_related("plantao"),

        pk=viatura_id,

        plantao_id=plantao_id,

    )

    if request.method == "POST":

        form = EfetivoViaturaForm(request.POST, viatura=viatura)

        if form.is_valid() and _validar_e_salvar_efetivo(form, viatura):

            messages.success(request, "GCM incluído no efetivo da viatura!")

            return redirecionar_fluxo(

                request,

                "cartao_programa:listar_efetivo",

                plantao_id=plantao_id,

                viatura_id=viatura_id,

            )

    else:

        form = EfetivoViaturaForm(viatura=viatura)

    return render(

        request,

        "cartao_programa/efetivo/form.html",

        {

            "plantao": viatura.plantao,

            "viatura": viatura,

            "form": form,

            "titulo": "Adicionar GCM à Viatura",
            "fluxo_cartao": fluxo_cartao_ativo(request),

            "edicao": False,

        },

    )

@acesso_gestao_equipes

def editar_efetivo(request, plantao_id, viatura_id, pk):

    viatura = get_object_or_404(

        ViaturaPlantao.objects.select_related("plantao"),

        pk=viatura_id,

        plantao_id=plantao_id,

    )

    integrante = get_object_or_404(

        EfetivoViatura,

        pk=pk,

        viatura=viatura,

    )

    if request.method == "POST":

        form = EfetivoViaturaForm(

            request.POST, instance=integrante, viatura=viatura

        )

        if form.is_valid() and _validar_e_salvar_efetivo(form, viatura):

            messages.success(request, "Efetivo da viatura atualizado com sucesso!")

            return redirecionar_fluxo(

                request,

                "cartao_programa:listar_efetivo",

                plantao_id=plantao_id,

                viatura_id=viatura_id,

            )

    else:

        form = EfetivoViaturaForm(instance=integrante, viatura=viatura)

    return render(

        request,

        "cartao_programa/efetivo/form.html",

        {

            "plantao": viatura.plantao,

            "viatura": viatura,

            "integrante": integrante,

            "form": form,

            "titulo": "Editar GCM da Viatura",
            "fluxo_cartao": fluxo_cartao_ativo(request),

            "edicao": True,

        },

    )

@acesso_gestao_equipes

def remover_efetivo(request, plantao_id, viatura_id, pk):

    viatura = get_object_or_404(

        ViaturaPlantao.objects.select_related("plantao"),

        pk=viatura_id,

        plantao_id=plantao_id,

    )

    integrante = get_object_or_404(

        EfetivoViatura.objects.select_related("gcm"),

        pk=pk,

        viatura=viatura,

    )

    if request.method == "POST":

        nome = integrante.gcm.nome

        integrante.delete()  # Não exclui o cadastro nem a equipe fixa do GCM.

        messages.success(request, f"{nome} foi removido do efetivo da viatura.")

        return redirecionar_fluxo(

            request,

            "cartao_programa:listar_efetivo",

            plantao_id=plantao_id,

            viatura_id=viatura_id,

        )

    return render(

        request,

        "cartao_programa/efetivo/confirmar_remocao.html",

        {

            "plantao": viatura.plantao,

            "viatura": viatura,

            "integrante": integrante,

        "fluxo_cartao": fluxo_cartao_ativo(request),
        },

    )

# =====================================================

# CARTÃO PROGRAMA - VISUALIZAR

# =====================================================

def _coordenador_automatico(request):
    """Define responsável sem escolher arbitrariamente entre vários coordenadores."""
    usuario = getattr(request.user, "usuario", None)
    if usuario is not None and usuario.ativo and usuario.perfil == "COORDENADOR":
        return usuario

    coordenadores = Usuario.objects.filter(perfil="COORDENADOR", ativo=True)
    # Se houver somente um, a escolha é inequívoca.
    if coordenadores.count() == 1:
        return coordenadores.first()
    return None


def _garantir_cartao(request, plantao):
    """Retorna o cartão existente ou cria um único cartão automaticamente.

    Se o administrador tiver vários coordenadores disponíveis, a seleção
    explícita permanece necessária para não atribuir responsabilidade errada.
    """
    cartao = CartaoPrograma.objects.filter(plantao=plantao).first()
    if cartao is not None:
        return cartao

    coordenador = _coordenador_automatico(request)
    if coordenador is None:
        return None

    with transaction.atomic():
        cartao, criado = CartaoPrograma.objects.get_or_create(
            plantao=plantao,
            defaults={"coordenador": coordenador},
        )
    if criado:
        messages.success(request, "Cartão Programa criado automaticamente. Cadastre as missões.")
    return cartao


@acesso_gestao_equipes
def visualizar_cartao(request, plantao_id):
    plantao = get_object_or_404(Plantao, pk=plantao_id)
    cartao = (
        CartaoPrograma.objects.filter(plantao=plantao)
        .select_related("coordenador", "plantao")
        .first()
    )
    if fluxo_cartao_ativo(request):
        return redirecionar_fluxo(
            request, "cartao_programa:listar_missoes", plantao_id=plantao.pk
        )

    viaturas = (
        ViaturaPlantao.objects.filter(plantao=plantao)
        .select_related("equipe")
        .prefetch_related("efetivo__gcm")
        .order_by("identificacao")
    )
    missoes = (
        MissaoCartao.objects.filter(cartao=cartao)
        .select_related("viatura", "escola")
        .order_by("numero")
        if cartao is not None
        else MissaoCartao.objects.none()
    )
    return render(request, "cartao_programa/cartoes/detalhe.html", {
        "plantao": plantao,
        "cartao": cartao,
        "viaturas": viaturas,
        "missoes": missoes,
        "fluxo_cartao": fluxo_cartao_ativo(request),
    })


# =====================================================
# CARTÃO PROGRAMA - CRIAR (SEM TELA EXTRA NO FLUXO)
# =====================================================

@acesso_gestao_equipes
def criar_cartao(request, plantao_id):
    plantao = get_object_or_404(Plantao, pk=plantao_id)

    # No fluxo guiado, nunca abrir o formulário se o cartão já existe
    # ou se pode ser criado automaticamente.
    if fluxo_cartao_ativo(request):
        cartao = _garantir_cartao(request, plantao)
        if cartao is not None:
            return redirecionar_fluxo(
                request, "cartao_programa:listar_missoes", plantao_id=plantao.pk
            )

    elif CartaoPrograma.objects.filter(plantao=plantao).exists():
        messages.info(request, "Este plantão já possui um Cartão Programa.")
        return redirect("cartao_programa:visualizar_cartao", plantao_id=plantao.pk)

    usuario = getattr(request.user, "usuario", None)
    if not request.user.is_active:
        raise PermissionDenied("Usuário inativo.")

    eh_admin = (
        request.user.is_superuser
        or request.user.is_staff
        or (usuario is not None and usuario.ativo and usuario.perfil == "ADMIN")
    )
    eh_coordenador = (
        usuario is not None and usuario.ativo and usuario.perfil == "COORDENADOR"
    )
    if not (eh_admin or eh_coordenador):
        raise PermissionDenied("Apenas administradores e coordenadores podem criar um Cartão Programa.")

    coordenadores = Usuario.objects.filter(
        perfil="COORDENADOR", ativo=True
    ).order_by("nome")
    selecionar_coordenador = eh_admin and not eh_coordenador

    form = CartaoProgramaForm(
        request.POST if request.method == "POST" else None,
        plantao=plantao,
    )
    if selecionar_coordenador:
        form.fields["coordenador"] = django_forms.ModelChoiceField(
            queryset=coordenadores,
            label="Coordenador responsável",
            required=True,
            empty_label="Selecione um coordenador",
            widget=django_forms.Select(attrs={"class": "form-select"}),
        )

    if request.method == "POST" and form.is_valid():
        cartao = form.save(commit=False)
        cartao.plantao = plantao
        cartao.coordenador = (
            form.cleaned_data["coordenador"] if selecionar_coordenador else usuario
        )
        try:
            cartao.full_clean()
        except ValidationError as erro:
            adicionar_erros_validacao(form, erro)
        else:
            cartao.save()
            messages.success(request, "Cartão Programa criado com sucesso!")
            destino = (
                "cartao_programa:listar_missoes"
                if fluxo_cartao_ativo(request)
                else "cartao_programa:visualizar_cartao"
            )
            return redirecionar_fluxo(request, destino, plantao_id=plantao.pk)

    return render(request, "cartao_programa/cartoes/form.html", {
        "plantao": plantao,
        "form": form,
        "coordenador": usuario if eh_coordenador else None,
        "coordenadores_disponiveis": coordenadores.exists(),
        "selecionar_coordenador": selecionar_coordenador,
        "titulo": "Criar Cartão Programa",
        "fluxo_cartao": fluxo_cartao_ativo(request),
        "edicao": False,
    })


# =====================================================
# CARTÃO PROGRAMA - EDITAR
# =====================================================

@acesso_gestao_equipes
def editar_cartao(request, plantao_id):

    plantao = get_object_or_404(Plantao, pk=plantao_id)

    cartao = get_object_or_404(
        CartaoPrograma.objects.select_related("coordenador"),
        plantao=plantao
    )

    form = CartaoProgramaForm(
        request.POST if request.method == "POST" else None,
        instance=cartao,
        plantao=plantao,
    )

    if request.method == "POST" and form.is_valid():

        atualizado = form.save(commit=False)

        atualizado.plantao = plantao

        # Preserva o coordenador originalmente responsável.
        # A edição não permite substituí-lo pelo formulário.
        atualizado.coordenador = cartao.coordenador

        try:
            atualizado.full_clean()

        except ValidationError as erro:
            adicionar_erros_validacao(form, erro)

        else:
            atualizado.save()

            messages.success(
                request,
                "Cartão Programa atualizado com sucesso!"
            )

            return redirecionar_fluxo(
                request,
                "cartao_programa:visualizar_cartao",
                plantao_id=plantao.pk
            )

    return render(
        request,
        "cartao_programa/cartoes/form.html",
        {
            "plantao": plantao,
            "cartao": cartao,
            "coordenador": cartao.coordenador,
            "form": form,
            "titulo": "Editar Cartão Programa",
            "fluxo_cartao": fluxo_cartao_ativo(request),
            "edicao": True,
        }
    )


# =====================================================

# MISSÕES - LISTAR

# =====================================================

@acesso_gestao_equipes
def listar_missoes(request, plantao_id):
    plantao = get_object_or_404(Plantao, pk=plantao_id)
    cartao = _garantir_cartao(request, plantao) if fluxo_cartao_ativo(request) else (
        CartaoPrograma.objects.filter(plantao=plantao).first()
    )

    if cartao is None:
        # Quando há vários coordenadores, somente a escolha explícita
        # permite identificar o responsável correto.
        if fluxo_cartao_ativo(request):
            messages.warning(
                request,
                "Selecione o coordenador responsável para iniciar as missões. "
                "Isso é necessário somente quando há mais de um coordenador ativo "
                "ou nenhum coordenador identificado.",
            )
        else:
            messages.info(request, "Antes de cadastrar missões, crie o Cartão Programa deste plantão.")
        return redirecionar_fluxo(
            request, "cartao_programa:criar_cartao", plantao_id=plantao.pk
        )

    missoes = (
        MissaoCartao.objects.filter(cartao=cartao)
        .select_related("viatura", "escola")
        .order_by("numero")
    )
    return render(request, "cartao_programa/missoes/listar.html", {
        "plantao": plantao,
        "cartao": cartao,
        "missoes": missoes,
        "fluxo_cartao": fluxo_cartao_ativo(request),
    })

# =====================================================

# MISSÕES - CRIAR

# =====================================================

@acesso_gestao_equipes

def criar_missao(request, plantao_id):

    plantao = get_object_or_404(Plantao, pk=plantao_id)

    cartao = get_object_or_404(CartaoPrograma, plantao=plantao)

    form = MissaoCartaoForm(

        request.POST if request.method == "POST" else None,

        cartao=cartao,

    )

    if request.method == "POST" and form.is_valid():

        missao = form.save(commit=False)

        missao.cartao = cartao

        try:

            missao.full_clean()

        except ValidationError as erro:

            adicionar_erros_validacao(form, erro)

        else:

            missao.save()

            messages.success(request, "Missão cadastrada com sucesso!")

            return redirecionar_fluxo(request, "cartao_programa:listar_missoes", plantao_id=plantao.pk)

    return render(request, "cartao_programa/missoes/form.html", {

        "plantao": plantao,

        "cartao": cartao,

        "form": form,

        "titulo": "Cadastrar Missão",
            "fluxo_cartao": fluxo_cartao_ativo(request),

        "edicao": False,

    })

# =====================================================

# MISSÕES - EDITAR

# =====================================================

@acesso_gestao_equipes

def editar_missao(request, plantao_id, pk):

    plantao = get_object_or_404(Plantao, pk=plantao_id)

    cartao = get_object_or_404(CartaoPrograma, plantao=plantao)

    missao = get_object_or_404(MissaoCartao, pk=pk, cartao=cartao)

    form = MissaoCartaoForm(

        request.POST if request.method == "POST" else None,

        instance=missao,

        cartao=cartao,

    )

    if request.method == "POST" and form.is_valid():

        atualizada = form.save(commit=False)

        atualizada.cartao = cartao

        try:

            atualizada.full_clean()

        except ValidationError as erro:

            adicionar_erros_validacao(form, erro)

        else:

            atualizada.save()

            messages.success(request, "Missão atualizada com sucesso!")

            return redirecionar_fluxo(request, "cartao_programa:listar_missoes", plantao_id=plantao.pk)

    return render(request, "cartao_programa/missoes/form.html", {

        "plantao": plantao,

        "cartao": cartao,

        "missao": missao,

        "form": form,

        "titulo": "Editar Missão",
            "fluxo_cartao": fluxo_cartao_ativo(request),

        "edicao": True,

    })

# =====================================================

# MISSÕES - REMOVER (SOMENTE POR POST)

# =====================================================

@acesso_gestao_equipes

def remover_missao(request, plantao_id, pk):

    plantao = get_object_or_404(Plantao, pk=plantao_id)

    cartao = get_object_or_404(CartaoPrograma, plantao=plantao)

    missao = get_object_or_404(MissaoCartao, pk=pk, cartao=cartao)

    if request.method == "POST":

        numero = missao.numero

        missao.delete()

        messages.success(request, f"Missão {numero} removida com sucesso!")

        return redirecionar_fluxo(request, "cartao_programa:listar_missoes", plantao_id=plantao.pk)

    return render(request, "cartao_programa/missoes/remocao.html", {

        "plantao": plantao,

        "cartao": cartao,

        "missao": missao,

        "fluxo_cartao": fluxo_cartao_ativo(request),
    })


# =====================================================
# MISSÕES - CADASTRO EM LOTE POR POLO
# =====================================================


@acesso_gestao_equipes
def criar_missoes_em_lote(request, plantao_id):
    """Cadastra uma missão por escola, de maneira atômica e sequencial."""

    plantao = get_object_or_404(Plantao, pk=plantao_id)
    cartao = get_object_or_404(CartaoPrograma, plantao=plantao)

    # Recupera o polo selecionado na página.
    polo_selecionado = request.GET.get("polo")

    # Cria o formulário mantendo o polo selecionado.
    if request.method == "POST":
        form = MissoesEmLoteForm(
            request.POST,
            cartao=cartao,
        )
    else:
        form = MissoesEmLoteForm(
            cartao=cartao,
            initial=(
                {"polo": polo_selecionado}
                if polo_selecionado
                else None
            ),
        )

    if request.method == "POST" and form.is_valid():
        dados = form.cleaned_data
        escolas = list(dados["escolas"].order_by("nome"))

        try:
            # Serializa os cadastros em lote para evitar números
            # repetidos em requisições simultâneas.
            with transaction.atomic():
                CartaoPrograma.objects.select_for_update().get(
                    pk=cartao.pk
                )

                ultimo_numero = (
                    MissaoCartao.objects.filter(cartao=cartao)
                    .order_by("-numero")
                    .values_list("numero", flat=True)
                    .first()
                ) or 0

                for indice, escola in enumerate(escolas, start=1):
                    missao = MissaoCartao(
                        cartao=cartao,
                        numero=ultimo_numero + indice,
                        viatura=dados["viatura"],
                        escola=escola,
                        local="",
                        endereco=escola.endereco or "",
                        periodo=dados["periodo"],
                        horario_inicio=dados.get("horario_inicio"),
                        horario_fim=dados.get("horario_fim"),
                        tipo_missao=dados["tipo_missao"],
                        observacoes=dados.get("observacoes") or "",
                    )

                    # Valida a missão antes de salvar.
                    missao.full_clean()
                    missao.save()

        except ValidationError as erro:
            adicionar_erros_validacao(form, erro)

        else:
            messages.success(
                request,
                f"{len(escolas)} missão(ões) cadastrada(s) com sucesso!",
            )

            return redirecionar_fluxo(
                request,
                "cartao_programa:listar_missoes",
                plantao_id=plantao.pk,
            )

    return render(
        request,
        "cartao_programa/missoes/form_lote.html",
        {
            "plantao": plantao,
            "cartao": cartao,
            "form": form,
            "titulo": "Cadastrar Missões por Polo",
            "fluxo_cartao": fluxo_cartao_ativo(request),
        },
    )

# =====================================================
# LISTAR CARTÕES PROGRAMA
# =====================================================

@acesso_gestao_equipes
def listar_cartoes(request):

    cartoes = (
        CartaoPrograma.objects
        .select_related("plantao", "coordenador")
        .order_by("-plantao__data", "-pk")
    )

    return render(
        request,
        "cartao_programa/cartoes/listar.html",
        {
            "cartoes": cartoes
        }
    )

# =====================================================
# EXCLUIR PLANTÃO
# =====================================================

@acesso_gestao_equipes
def excluir_plantao(request, plantao_id):

    if request.method != "POST":
        return HttpResponseForbidden(
            "A exclusão deve ser realizada pelo formulário."
        )

    plantao = get_object_or_404(
        Plantao,
        pk=plantao_id
    )

    # Impede excluir um plantão que já possui
    # viaturas ou Cartão Programa.
    if (
        plantao.viaturas.exists()
        or CartaoPrograma.objects.filter(
            plantao=plantao
        ).exists()
    ):
        messages.error(
            request,
            "Não é possível excluir este plantão porque "
            "ele possui viaturas ou Cartão Programa vinculados."
        )

        return redirect(
            "cartao_programa:listar_plantoes"
        )

    try:
        with transaction.atomic():
            plantao.delete()

        messages.success(
            request,
            "Plantão excluído com sucesso!"
        )

    except ProtectedError:
        messages.error(
            request,
            "Este plantão possui registros protegidos "
            "e não pode ser excluído."
        )

    return redirect(
        "cartao_programa:listar_plantoes"
    )
    
@acesso_gestao_equipes
def excluir_plantao(request, plantao_id):

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    plantao = get_object_or_404(
        Plantao,
        pk=plantao_id
    )

    data_plantao = plantao.data.strftime("%d/%m/%Y")

    try:
        with transaction.atomic():

            # Exclui o plantão e os registros relacionados
            # configurados com on_delete=CASCADE.
            plantao.delete()

    except (ProtectedError, RestrictedError):
        messages.error(
            request,
            "Não foi possível excluir o plantão porque "
            "existem registros protegidos vinculados."
        )

    else:
        messages.success(
            request,
            f"Plantão de {data_plantao} excluído com sucesso!"
        )

    return redirect(
        "cartao_programa:listar_plantoes"
    )


