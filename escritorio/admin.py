from django.contrib import admin

from escritorio.models import (Advogado, Bonificacao, Cliente,
                               ContratoDeHonorarios, Processo, Recebimento,
                               Repasse)


class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nome', 'tipoPessoa', 'cpfCnpj', 'telefone', 'email')

class AdvogadoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'oab')

class ContratoAdmin(admin.ModelAdmin):
    list_display = ('cliente', 'dataAssinatura', 'area', 'origem',
                    'percentualCliente', 'percentualEscritorio', 'situacao', 'processo',
                    'valorGanho')

class ProcessoAdmin(admin.ModelAdmin):
    list_display = ('numero', 'dataProtocolo', 'tipo', 'via', 'valorCausa',
                    'situacao', 'advogado')

class RecebimentoAdmin(admin.ModelAdmin):
    list_display = ('processo', 'contrato', 'numeroParcela', 'valor', 'data')

class RepasseAdmin(admin.ModelAdmin):
    list_display = ('cliente', 'recebimento', 'valor', 'dataLimite', 'situacao')

class BonificacaoAdmin(admin.ModelAdmin):
    list_display = ('advogado', 'recebimento', 'valor', 'situacao')


admin.site.register(Cliente, ClienteAdmin)
admin.site.register(Advogado, AdvogadoAdmin)
admin.site.register(ContratoDeHonorarios, ContratoAdmin)
admin.site.register(Processo, ProcessoAdmin)
admin.site.register(Recebimento, RecebimentoAdmin)
admin.site.register(Repasse, RepasseAdmin)
admin.site.register(Bonificacao, BonificacaoAdmin)
