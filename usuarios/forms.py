
from django import forms

from .models import Usuario
from cartao_programa.models import Equipe, IntegranteEquipe


class UsuarioForm(forms.ModelForm):

    equipe = forms.ModelChoiceField(
        queryset=Equipe.objects.none(),
        required=False,
        label="Equipe",
        empty_label="Selecione a equipe",
        widget=forms.Select(
            attrs={"class": "form-select"}
        ),
    )

    funcao_equipe = forms.ChoiceField(
        choices=[
            ("", "Selecione a função"),
            ("C", "C — Comandante"),
            ("M", "M — Motorista"),
            ("P1", "P1 — Patrulheiro 1"),
            ("P2", "P2 — Patrulheiro 2"),
        ],
        required=False,
        label="Função na equipe",
        widget=forms.Select(
            attrs={"class": "form-select"}
        ),
    )

    class Meta:
        model = Usuario
        fields = [
            "nome",
            "matricula",
            "cpf",
            "sexo",
            "telefone",
            "email",
            "perfil",
        ]

        widgets = {
            "nome": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Digite o nome completo",
                }
            ),
            "matricula": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Digite a matrícula",
                }
            ),
            "cpf": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Digite o CPF",
                }
            ),
            "sexo": forms.Select(
                attrs={"class": "form-select"}
            ),
            "telefone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Digite o telefone",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Digite o e-mail",
                }
            ),
            "perfil": forms.Select(
                attrs={"class": "form-select"}
            ),
        }

        labels = {
            "nome": "Nome",
            "matricula": "Matrícula",
            "cpf": "CPF",
            "sexo": "Sexo",
            "telefone": "Telefone",
            "email": "E-mail",
            "perfil": "Perfil",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["nome"].required = True
        self.fields["matricula"].required = True
        self.fields["perfil"].required = True

        self.fields["cpf"].required = False
        self.fields["sexo"].required = False
        self.fields["telefone"].required = False
        self.fields["email"].required = False

        self.fields["sexo"].empty_label = "Selecione"
        self.fields["perfil"].empty_label = "Selecione o perfil"

        # Utiliza as equipes já cadastradas no sistema.
        self.fields["equipe"].queryset = Equipe.objects.all()

        # Preenche os campos ao editar um GCM.
        if self.instance.pk:
            vinculo = IntegranteEquipe.objects.filter(
                gcm=self.instance
            ).select_related("equipe").first()

            if vinculo:
                self.fields["equipe"].initial = vinculo.equipe
                self.fields["funcao_equipe"].initial = vinculo.funcao_habitual

    def clean_matricula(self):
        matricula = self.cleaned_data["matricula"].strip()

        usuarios = Usuario.objects.filter(
            matricula__iexact=matricula
        )

        if self.instance.pk:
            usuarios = usuarios.exclude(pk=self.instance.pk)

        if usuarios.exists():
            raise forms.ValidationError(
                "Já existe um usuário cadastrado com esta matrícula."
            )

        return matricula

    def clean_cpf(self):
        cpf = self.cleaned_data.get("cpf")

        if not cpf:
            return None

        cpf = cpf.strip()

        usuarios = Usuario.objects.filter(cpf=cpf)

        if self.instance.pk:
            usuarios = usuarios.exclude(pk=self.instance.pk)

        if usuarios.exists():
            raise forms.ValidationError(
                "Já existe um usuário cadastrado com este CPF."
            )

        return cpf

    def clean_email(self):
        email = self.cleaned_data.get("email")

        if not email:
            return None

        return email.strip().lower()

    def clean(self):
        cleaned_data = super().clean()

        perfil = cleaned_data.get("perfil")
        equipe = cleaned_data.get("equipe")
        funcao = cleaned_data.get("funcao_equipe")

        if perfil == "GCM":

            if not equipe:
                self.add_error(
                    "equipe",
                    "Selecione a equipe do GCM."
                )

            if not funcao:
                self.add_error(
                    "funcao_equipe",
                    "Selecione a função do GCM."
                )

        return cleaned_data
