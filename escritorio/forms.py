from django import forms

from escritorio.models import (Advogado, Cliente, ContratoDeHonorarios,
                               Processo, Recebimento, Repasse, Bonificacao)


# Campo de data que abre o calendário do navegador. O format faz a data
# aparecer preenchida na tela de atualizar.
def campoData():
    return forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'})


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = '__all__'
        labels = {'tipoPessoa': 'Tipo de pessoa', 'cpfCnpj': 'CPF ou CNPJ', 'email': 'E-mail'}
        widgets = {
            'nome': forms.TextInput(attrs={'placeholder': 'nome completo ou razão social'}),
            'tipoPessoa': forms.Select(choices=[('fisica', 'física'), ('juridica', 'jurídica')]),
            'cpfCnpj': forms.TextInput(attrs={'placeholder': 'pode digitar com ou sem pontos'}),
            'telefone': forms.TextInput(attrs={'placeholder': '(65) 99999-9999'}),
        }

    def __init__(self, *args, **kwargs):
        super(ClienteForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'


class AdvogadoForm(forms.ModelForm):
    class Meta:
        model = Advogado
        fields = '__all__'
        labels = {'oab': 'OAB'}
        widgets = {
            'nome': forms.TextInput(attrs={'placeholder': 'nome completo'}),
            'oab': forms.TextInput(attrs={'placeholder': 'MT 12345'}),
        }

    def __init__(self, *args, **kwargs):
        super(AdvogadoForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'


# Caso de uso 1. O processo não aparece aqui: o contrato nasce sem processo.
# O cliente também não: ele é procurado pelo CPF antes (passos 2 a 4), e a
# view coloca no contrato o cliente encontrado.
class ContratoForm(forms.ModelForm):
    class Meta:
        model = ContratoDeHonorarios
        fields = ('dataAssinatura', 'area', 'origem',
                  'percentualCliente', 'percentualEscritorio', 'situacao')
        labels = {'dataAssinatura': 'Data de assinatura', 'area': 'Área', 'origem': 'Quem fechou o contrato',
                  'percentualCliente': 'Percentual do cliente (%)',
                  'percentualEscritorio': 'Percentual do escritório (%)', 'situacao': 'Situação'}
        widgets = {
            'dataAssinatura': campoData(),
            'area': forms.Select(choices=[('trabalhista', 'trabalhista'), ('previdenciario', 'previdenciário')]),
            'origem': forms.Select(choices=[('comercial', 'comercial'), ('advogado', 'advogado')]),
            'situacao': forms.Select(choices=[('ativo', 'ativo'), ('encerrado', 'encerrado')]),
        }

    def __init__(self, *args, **kwargs):
        super(ContratoForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'


# Caso de uso 2. O campo contratos não existe na classe Processo: ele
# serve para escolher quais contratos serão vinculados a este processo.
class ProcessoForm(forms.ModelForm):
    contratos = forms.ModelMultipleChoiceField(
        queryset=ContratoDeHonorarios.objects.filter(situacao='ativo', processo=None),
        help_text='O contrato do cliente procurado já vem marcado. No processo coletivo, '
                  'segure Ctrl e marque também os contratos dos outros clientes.',
    )

    class Meta:
        model = Processo
        fields = ('numero', 'dataProtocolo', 'tipo', 'via', 'valorCausa',
                  'situacao', 'advogado')
        labels = {'numero': 'Número do processo', 'dataProtocolo': 'Data do protocolo',
                  'valorCausa': 'Valor pedido na petição inicial (R$)',
                  'situacao': 'Situação', 'advogado': 'Advogado responsável'}
        widgets = {
            'numero': forms.TextInput(attrs={'placeholder': 'número gerado no protocolo'}),
            'dataProtocolo': campoData(),
            'tipo': forms.Select(choices=[('individual', 'individual'), ('coletivo', 'coletivo')]),
            'via': forms.Select(choices=[('', 'nenhuma (trabalhista)'), ('judicial', 'judicial'), ('administrativa', 'administrativa')]),
            'situacao': forms.Select(choices=[('ativo', 'ativo'), ('encerrado', 'encerrado')]),
        }

    def __init__(self, *args, **kwargs):
        super(ProcessoForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'


# Na tela de atualizar o processo os contratos já estão vinculados,
# então o formulário é o mesmo sem o campo contratos.
class ProcessoAtualizarForm(forms.ModelForm):
    class Meta:
        model = Processo
        fields = ('numero', 'dataProtocolo', 'tipo', 'via', 'valorCausa',
                  'situacao', 'advogado')
        labels = {'numero': 'Número do processo', 'dataProtocolo': 'Data do protocolo',
                  'valorCausa': 'Valor pedido na petição inicial (R$)',
                  'situacao': 'Situação', 'advogado': 'Advogado responsável'}
        widgets = {
            'numero': forms.TextInput(attrs={'placeholder': 'número gerado no protocolo'}),
            'dataProtocolo': campoData(),
            'tipo': forms.Select(choices=[('individual', 'individual'), ('coletivo', 'coletivo')]),
            'via': forms.Select(choices=[('', 'nenhuma (trabalhista)'), ('judicial', 'judicial'), ('administrativa', 'administrativa')]),
            'situacao': forms.Select(choices=[('ativo', 'ativo'), ('encerrado', 'encerrado')]),
        }

    def __init__(self, *args, **kwargs):
        super(ProcessoAtualizarForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'


# Caso de uso 3. O número da parcela não aparece: o sistema define.
# O processo e o cliente também não: eles são escolhidos antes (passos 2 a 4).
# O campo valorGanho não existe na classe Recebimento: ele é gravado no
# contrato do cliente. No primeiro recebimento a assistente digita o valor
# que o juiz decidiu; nos seguintes ele já vem preenchido.
class RecebimentoForm(forms.ModelForm):
    valorGanho = forms.DecimalField(max_digits=12, decimal_places=2,
                                    label='Valor decidido pelo juiz para este cliente (R$)')
    pagamento = forms.ChoiceField(choices=[('parcelado', 'parcelado'), ('unico', 'único')],
                                  initial='parcelado', label='Pagamento',
                                  help_text='único: o valor decidido chegou todo de uma vez. '
                                            'parcelado: este valor é uma das parcelas.')

    class Meta:
        model = Recebimento
        fields = ('valorGanho', 'pagamento', 'valor', 'data', 'formaPagamento')
        labels = {'valor': 'Valor bruto desta parcela (R$)', 'data': 'Data do recebimento',
                  'formaPagamento': 'Forma de pagamento'}
        help_texts = {
            'valor': 'A parte do cliente somada à do escritório, mesmo quando o juiz separa os valores.',
            'formaPagamento': 'integral: tudo caiu na conta do escritório, que repassa ao cliente. '
                              'destaque: o juiz separou, e a parte do cliente foi direto para ele. '
                              'Na via administrativa não faz diferença.',
        }
        widgets = {
            'data': campoData(),
            'formaPagamento': forms.Select(choices=[('integral', 'integral'), ('destaque', 'destaque')]),
        }

    def __init__(self, *args, **kwargs):
        super(RecebimentoForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'


# O repasse é criado pelo sistema no caso de uso 3. Na atualização só se
# muda a situação, para marcar que o repasse foi pago.
class RepasseForm(forms.ModelForm):
    class Meta:
        model = Repasse
        fields = ('situacao',)
        labels = {'situacao': 'Situação'}
        widgets = {
            'situacao': forms.Select(choices=[('pendente', 'pendente'), ('pago', 'pago')]),
        }

    def __init__(self, *args, **kwargs):
        super(RepasseForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'


# A bonificação também é criada pelo caso de uso 3. Aqui só se marca
# como paga, igual ao repasse.
class BonificacaoForm(forms.ModelForm):
    class Meta:
        model = Bonificacao
        fields = ('situacao',)
        labels = {'situacao': 'Situação'}
        widgets = {
            'situacao': forms.Select(choices=[('pendente', 'pendente'), ('pago', 'pago')]),
        }

    def __init__(self, *args, **kwargs):
        super(BonificacaoForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'
