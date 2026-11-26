from django.urls import path

from escritorio import views


urlpatterns = [
    path('', views.listarContratos, name='inicio'),

    path('clientes/', views.listarClientes, name='cliente_listar'),
    path('clientes/novo/', views.criarCliente, name='cliente_criar'),
    path('clientes/<int:pk>/', views.visualizarCliente, name='cliente_visualizar'),
    path('clientes/<int:pk>/editar/', views.atualizarCliente, name='cliente_atualizar'),
    path('clientes/<int:pk>/deletar/', views.deletarCliente, name='cliente_deletar'),

    path('advogados/', views.listarAdvogados, name='advogado_listar'),
    path('advogados/novo/', views.criarAdvogado, name='advogado_criar'),
    path('advogados/<int:pk>/', views.visualizarAdvogado, name='advogado_visualizar'),
    path('advogados/<int:pk>/editar/', views.atualizarAdvogado, name='advogado_atualizar'),
    path('advogados/<int:pk>/deletar/', views.deletarAdvogado, name='advogado_deletar'),

    path('contratos/', views.listarContratos, name='contrato_listar'),
    path('contratos/novo/', views.criarContrato, name='contrato_criar'),
    path('contratos/<int:pk>/', views.visualizarContrato, name='contrato_visualizar'),
    path('contratos/<int:pk>/editar/', views.atualizarContrato, name='contrato_atualizar'),
    path('contratos/<int:pk>/deletar/', views.deletarContrato, name='contrato_deletar'),

    path('processos/', views.listarProcessos, name='processo_listar'),
    path('processos/novo/', views.criarProcesso, name='processo_criar'),
    path('processos/<int:pk>/', views.visualizarProcesso, name='processo_visualizar'),
    path('processos/<int:pk>/editar/', views.atualizarProcesso, name='processo_atualizar'),
    path('processos/<int:pk>/deletar/', views.deletarProcesso, name='processo_deletar'),

    path('recebimentos/', views.listarRecebimentos, name='recebimento_listar'),
    path('recebimentos/novo/', views.criarRecebimento, name='recebimento_criar'),
    path('recebimentos/<int:pk>/', views.visualizarRecebimento, name='recebimento_visualizar'),
    path('recebimentos/<int:pk>/deletar/', views.deletarRecebimento, name='recebimento_deletar'),

    path('repasses/', views.listarRepasses, name='repasse_listar'),
    path('repasses/<int:pk>/', views.visualizarRepasse, name='repasse_visualizar'),
    path('repasses/<int:pk>/editar/', views.atualizarRepasse, name='repasse_atualizar'),

    path('bonificacoes/', views.listarBonificacoes, name='bonificacao_listar'),
    path('bonificacoes/<int:pk>/', views.visualizarBonificacao, name='bonificacao_visualizar'),
    path('bonificacoes/<int:pk>/editar/', views.atualizarBonificacao, name='bonificacao_atualizar'),
]
