
from django import forms

from .models import RondaVisita


class RondaVisitaForm(forms.ModelForm):

    class Meta:
        model = RondaVisita

        fields = [
            "escola",
            "equipe",
            "data_visita",
            "horario",
            "tipo_visita",
            "situacao",
            "relato",
            "orientacoes",
        ]

        labels = {
            "escola": "Escola",
            "equipe": "Equipe responsável",
            "data_visita": "Data da visita",
            "horario": "Horário",
            "tipo_visita": "Tipo de visita",
            "situacao": "Situação encontrada",
            "relato": "Relato da visita",
            "orientacoes": "Orientações / providências",
        }

        widgets = {

            # ==========================================
            # ESCOLA
            # ==========================================

            "escola": forms.Select(
                attrs={
                    "class": "form-select select-escola",
                    "id": "id_escola",
                    "data-placeholder": "Digite o nome da escola...",
                }
            ),

            # ==========================================
            # EQUIPE
            # ==========================================

            "equipe": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            # ==========================================
            # DATA
            # ==========================================

            "data_visita": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),

            # ==========================================
            # HORÁRIO
            # ==========================================

            "horario": forms.TimeInput(
                format="%H:%M",
                attrs={
                    "class": "form-control",
                    "type": "time",
                }
            ),

            # ==========================================
            # TIPO DE VISITA
            # ==========================================

            "tipo_visita": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            # ==========================================
            # SITUAÇÃO
            # ==========================================

            "situacao": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            # ==========================================
            # RELATO
            # ==========================================

            "relato": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": (
                        "Descreva o que foi observado ou realizado "
                        "durante a visita."
                    ),
                }
            ),

            # ==========================================
            # ORIENTAÇÕES / PROVIDÊNCIAS
            # ==========================================

            "orientacoes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": (
                        "Informe as orientações ou providências adotadas, "
                        "quando houver."
                    ),
                }
            ),
        }

    def __init__(
        self,
        *args,
        missao=None,
        **kwargs
    ):

        super().__init__(*args, **kwargs)

        # ==========================================
        # ESCOLAS ATIVAS
        # ==========================================

        escolas = (
            self.fields["escola"]
            .queryset
            .filter(ativa=True)
            .order_by("nome")
        )

        # Preserva a escola de um registro antigo
        # durante a edição, mesmo que esteja inativa.
        if self.instance.pk and self.instance.escola_id:
            escolas = (
                self.fields["escola"]
                .queryset
                .filter(
                    pk=self.instance.escola_id
                ) | escolas
            )

            escolas = escolas.distinct().order_by("nome")

        self.fields["escola"].queryset = escolas

        self.fields["escola"].empty_label = (
            "Digite ou selecione uma escola"
        )

        # ==========================================
        # CAMPOS OBRIGATÓRIOS
        # ==========================================

        for campo in [
            "escola",
            "equipe",
            "data_visita",
            "horario",
            "tipo_visita",
            "situacao",
        ]:
            self.fields[campo].required = True

        # ==========================================
        # VISITA VINCULADA AO CARTÃO PROGRAMA
        # ==========================================

        if missao is not None:

            escola = missao.escola

            # A escola da missão deve estar disponível
            # no queryset, inclusive se foi desativada
            # após o planejamento do cartão.
            self.fields["escola"].queryset = (
                self.fields["escola"]
                .queryset.model.objects.filter(
                    pk=escola.pk
                )
            )

            self.fields["escola"].initial = escola.pk

            # O Django ignora alterações enviadas
            # pelo navegador para campos desabilitados.
            self.fields["escola"].disabled = True

            self.fields["escola"].help_text = (
                "Escola definida automaticamente "
                "pela missão do Cartão Programa."
            )

            # Sugere a data do plantão no cadastro.
            # O usuário poderá corrigir a data real
            # caso a visita tenha ocorrido em outro dia.
            if not self.is_bound and not self.instance.pk:
                self.fields["data_visita"].initial = (
                    missao.cartao.plantao.data
                )

        # ==========================================
        # VISITAS AVULSAS
        # ==========================================

        else:
            self.fields["escola"].disabled = False
