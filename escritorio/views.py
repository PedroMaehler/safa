from django.contrib import messages
from django.shortcuts import redirect, render

from escritorio.forms import (AdvogadoForm, BonificacaoForm, ClienteForm,
                              ContratoForm, ProcessoAtualizarForm, ProcessoForm,
                              RecebimentoForm, RepasseForm)
from escritorio.models import (Advogado, Bonificacao, Cliente,
                               ContratoDeHonorarios, Processo, Recebimento,
                               Repasse)


# ------------------------------------------------------------------
# Regras de negócio que o formulário sozinho não confere.
# Cada função devolve a mensagem de erro, ou None se estiver tudo certo.
# ------------------------------------------------------------------

def erroDoCliente(cliente):
    if cliente.tipoPessoa not in ('fisica', 'juridica'):
        return 'Tipo de pessoa deve ser fisica ou juridica.'
    if not cliente.validarCpfCnpj():
        return 'CPF ou CNPJ incorreto: o CPF tem 11 números e o CNPJ tem 14.'
    # RN-02: compara só os números, então 123.456.789-01 e 12345678901
    # são o mesmo CPF.
    existente = cliente.buscarPorCpfCnpj(cliente.somenteNumeros())
    if existente is not None and existente.pk != cliente.pk:
        return f'Já existe um cliente com esse CPF ou CNPJ: {existente}.'
    return None


def erroDoContrato(contrato):
    if contrato.area not in ('trabalhista', 'previdenciario'):
        return 'Área deve ser trabalhista ou previdenciario.'
    if contrato.origem not in ('comercial', 'advogado'):
        return 'Origem deve ser comercial ou advogado.'
    if contrato.situacao not in ('ativo', 'encerrado'):
        return 'Situação deve ser ativo ou encerrado.'
    if contrato.percentualCliente < 0 or contrato.percentualEscritorio < 0:
        return 'Percentual não pode ser negativo.'                      # RN-04
    if not contrato.percentuaisSomam100():
        return 'O percentual do cliente somado ao do escritório precisa dar 100%.'  # RN-06
    if contrato.percentualEscritorio < 20 or contrato.percentualEscritorio > 30:
        return 'O percentual do escritório fica entre 20% e 30%.'
    return None


def erroDoProcesso(processo, contratos):
    if processo.tipo not in ('individual', 'coletivo'):
        return 'Tipo deve ser individual ou coletivo.'
    if processo.situacao not in ('ativo', 'encerrado'):
        return 'Situação deve ser ativo ou encerrado.'
    if processo.via not in (None, '', 'administrativa', 'judicial'):
        return 'Via deve ser administrativa ou judicial, ou ficar em branco.'
    if processo.tipo == 'individual' and len(contratos) != 1:
        return 'Processo individual tem um contrato só.'
    clientes = []
    for contrato in contratos:
        if contrato.cliente in clientes:
            return f'{contrato.cliente} aparece em dois contratos: escolha um só por cliente.'
        clientes.append(contrato.cliente)
        if contrato.possuiProcesso() and contrato.processo != processo:
            return f'O contrato de {contrato.cliente} já tem processo.'   # RN-16
        if contrato.area == 'previdenciario' and processo.via not in ('administrativa', 'judicial'):
            return 'No contrato previdenciário, a via deve ser administrativa ou judicial.'
    if processo.via != 'administrativa' and processo.valorCausa is None:
        return 'Informe o valor pedido na petição inicial.'
    if processo.valorCausa is not None and processo.valorCausa < 0:
        return 'O valor pedido não pode ser negativo.'                   # RN-04
    return None


# Passos 3 e 4 dos casos de uso 1 e 2: confere o CPF ou CNPJ digitado e
# procura o cliente. Devolve duas coisas: o cliente encontrado (ou None) e
# a mensagem para mostrar na tela (ou None).
def procurarCliente(cpfCnpj):
    procura = Cliente(cpfCnpj=cpfCnpj)
    if not procura.validarCpfCnpj():
        return None, 'CPF ou CNPJ incorreto: o CPF tem 11 números e o CNPJ tem 14.'   # [3a]
    cliente = procura.buscarPorCpfCnpj(procura.somenteNumeros())
    if cliente is None:
        return None, 'Nenhum cliente cadastrado com esse CPF ou CNPJ.'                  # [4a]
    return cliente, None


def erroDoRecebimento(recebimento, valorGanho, pagamento):
    if valorGanho < 0 or recebimento.valor < 0:
        return 'Valor não pode ser negativo.'                            # RN-04
    if recebimento.valor == 0:
        return 'O valor recebido precisa ser maior que zero.'
    if recebimento.formaPagamento not in ('integral', 'destaque'):
        return 'Forma de pagamento deve ser integral ou destaque.'
    if not recebimento.contrato.podeReceber():
        return 'Este contrato não pode receber valores: ele ou o processo está encerrado.'
    return erroDoPagamento(recebimento, valorGanho, pagamento)


# ------------------------------------------------------------------
# Clientes
# ------------------------------------------------------------------

def listarClientes(request):
    clientes = Cliente.objects.all()
    return render(request, 'escritorio/clientes/listagem.html', {'clientes': clientes})


def criarCliente(request):
    form = ClienteForm(request.POST or None)
    erro = None
    if form.is_valid():
        cliente = form.save(commit=False)
        erro = erroDoCliente(cliente)
        if erro is None:
            cliente.cpfCnpj = cliente.somenteNumeros()
            cliente.save()
            messages.success(request, 'Cliente cadastrado.')
            return redirect('cliente_listar')
    contexto = {'formulario': form, 'erro': erro}
    return render(request, 'escritorio/clientes/criar.html', contexto)


def atualizarCliente(request, pk=None):
    cliente = Cliente.objects.get(pk=pk)
    form = ClienteForm(request.POST or None, instance=cliente)
    erro = None
    if form.is_valid():
        cliente = form.save(commit=False)
        erro = erroDoCliente(cliente)
        if erro is None:
            cliente.cpfCnpj = cliente.somenteNumeros()
            cliente.save()
            messages.success(request, 'Cliente atualizado.')
            return redirect('cliente_listar')
    contexto = {'formulario': form, 'erro': erro}
    return render(request, 'escritorio/clientes/atualizar.html', contexto)


def deletarCliente(request, pk=None):
    cliente = Cliente.objects.get(pk=pk)
    if request.method == 'POST':
        if cliente.contratodehonorarios_set.count() > 0:
            messages.warning(request, 'Não é possível apagar: o cliente tem contrato.')
        else:
            cliente.delete()
            messages.success(request, 'Cliente apagado.')
        return redirect('cliente_listar')
    return render(request, 'escritorio/clientes/deletar.html', {'cliente': cliente})


def visualizarCliente(request, pk=None):
    cliente = Cliente.objects.get(pk=pk)
    return render(request, 'escritorio/clientes/visualizar.html', {'cliente': cliente})


# ------------------------------------------------------------------
# Advogados
# ------------------------------------------------------------------

def listarAdvogados(request):
    advogados = Advogado.objects.all()
    return render(request, 'escritorio/advogados/listagem.html', {'advogados': advogados})


def criarAdvogado(request):
    form = AdvogadoForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Advogado cadastrado.')
        return redirect('advogado_listar')
    return render(request, 'escritorio/advogados/criar.html', {'formulario': form})


def atualizarAdvogado(request, pk=None):
    advogado = Advogado.objects.get(pk=pk)
    form = AdvogadoForm(request.POST or None, instance=advogado)
    if form.is_valid():
        form.save()
        messages.success(request, 'Advogado atualizado.')
        return redirect('advogado_listar')
    return render(request, 'escritorio/advogados/atualizar.html', {'formulario': form})


def deletarAdvogado(request, pk=None):
    advogado = Advogado.objects.get(pk=pk)
    if request.method == 'POST':
        if advogado.processo_set.count() > 0:
            messages.warning(request, 'Não é possível apagar: o advogado é responsável por processo.')
        else:
            advogado.delete()
            messages.success(request, 'Advogado apagado.')
        return redirect('advogado_listar')
    return render(request, 'escritorio/advogados/deletar.html', {'advogado': advogado})


def visualizarAdvogado(request, pk=None):
    advogado = Advogado.objects.get(pk=pk)
    return render(request, 'escritorio/advogados/visualizar.html', {'advogado': advogado})


# ------------------------------------------------------------------
# Contratos (caso de uso 1: Cadastrar contrato)
# ------------------------------------------------------------------

def listarContratos(request):
    contratos = ContratoDeHonorarios.objects.all()
    return render(request, 'escritorio/contratos/listagem.html', {'contratos': contratos})


# Passos 2 a 4: o ator digita o CPF e clica em Procurar. O formulário do
# contrato só aparece depois que o cliente é encontrado.
def criarContrato(request):
    cpf = request.GET.get('cpf', '').strip()
    cliente = None
    aviso = None
    if cpf != '':
        cliente, aviso = procurarCliente(cpf)
    form = ContratoForm(request.POST or None)
    erro = None
    if cliente is not None and form.is_valid():
        contrato = form.save(commit=False)
        contrato.cliente = cliente
        erro = erroDoContrato(contrato)
        if erro is None:
            contrato.save()
            messages.success(request, 'Contrato cadastrado. Ele aguarda o protocolo do processo.')
            return redirect('contrato_listar')
    contexto = {'formulario': form, 'erro': erro, 'cpf': cpf, 'cliente': cliente, 'aviso': aviso}
    return render(request, 'escritorio/contratos/criar.html', contexto)


def atualizarContrato(request, pk=None):
    contrato = ContratoDeHonorarios.objects.get(pk=pk)
    form = ContratoForm(request.POST or None, instance=contrato)
    erro = None
    if form.is_valid():
        contrato = form.save(commit=False)
        erro = erroDoContrato(contrato)
        if erro is None:
            contrato.save()
            messages.success(request, 'Contrato atualizado.')
            return redirect('contrato_listar')
    contexto = {'formulario': form, 'erro': erro, 'contrato': contrato}
    return render(request, 'escritorio/contratos/atualizar.html', contexto)


def deletarContrato(request, pk=None):
    contrato = ContratoDeHonorarios.objects.get(pk=pk)
    if request.method == 'POST':
        if contrato.possuiProcesso():
            messages.warning(request, 'Não é possível apagar: o contrato já tem processo.')
        else:
            contrato.delete()
            messages.success(request, 'Contrato apagado.')
        return redirect('contrato_listar')
    return render(request, 'escritorio/contratos/deletar.html', {'contrato': contrato})


def visualizarContrato(request, pk=None):
    contrato = ContratoDeHonorarios.objects.get(pk=pk)
    return render(request, 'escritorio/contratos/visualizar.html', {'contrato': contrato})


# ------------------------------------------------------------------
# Processos (caso de uso 2: Cadastrar processo)
# ------------------------------------------------------------------

def listarProcessos(request):
    processos = Processo.objects.all()
    return render(request, 'escritorio/processos/listagem.html', {'processos': processos})


# Passos 2 a 4: o ator digita o CPF, o sistema procura o cliente e mostra
# o contrato dele que aguarda processo (possuiProcesso() falso). O
# formulário do processo só aparece se houver esse contrato.
def criarProcesso(request):
    cpf = request.GET.get('cpf', '').strip()
    cliente = None
    aviso = None
    contratosDoCliente = []
    if cpf != '':
        cliente, aviso = procurarCliente(cpf)
    if cliente is not None:
        contratosDoCliente = cliente.contratodehonorarios_set.filter(situacao='ativo', processo=None)
        if len(contratosDoCliente) == 0:
            aviso = 'Este cliente não tem contrato ativo aguardando processo.'      # [4a]
    form = ProcessoForm(request.POST or None, initial={'contratos': contratosDoCliente})
    erro = None
    if len(contratosDoCliente) > 0 and form.is_valid():
        processo = form.save(commit=False)
        contratos = form.cleaned_data['contratos']
        erro = erroDoProcesso(processo, contratos)
        if erro is None:
            processo.save()
            for contrato in contratos:
                contrato.vincularProcesso(processo)
            messages.success(request, 'Processo cadastrado e vinculado ao contrato.')
            return redirect('processo_listar')
    contexto = {'formulario': form, 'erro': erro, 'cpf': cpf, 'cliente': cliente,
                'aviso': aviso, 'contratosDoCliente': contratosDoCliente}
    return render(request, 'escritorio/processos/criar.html', contexto)


def atualizarProcesso(request, pk=None):
    processo = Processo.objects.get(pk=pk)
    form = ProcessoAtualizarForm(request.POST or None, instance=processo)
    erro = None
    if form.is_valid():
        processo = form.save(commit=False)
        contratos = processo.contratodehonorarios_set.all()
        erro = erroDoProcesso(processo, contratos)
        if erro is None:
            processo.save()
            messages.success(request, 'Processo atualizado.')
            return redirect('processo_listar')
    contexto = {'formulario': form, 'erro': erro}
    return render(request, 'escritorio/processos/atualizar.html', contexto)


# Apagar um processo sem recebimento desfaz o caso de uso 2: os contratos
# voltam a ficar sem processo, aguardando o protocolo.
def deletarProcesso(request, pk=None):
    processo = Processo.objects.get(pk=pk)
    if request.method == 'POST':
        if processo.recebimento_set.count() > 0:
            messages.warning(request, 'Não é possível apagar: o processo já tem recebimento.')
        else:
            for contrato in processo.contratodehonorarios_set.all():
                contrato.vincularProcesso(None)
            processo.delete()
            messages.success(request, 'Processo apagado. Os contratos voltaram a aguardar o protocolo.')
        return redirect('processo_listar')
    return render(request, 'escritorio/processos/deletar.html', {'processo': processo})


def visualizarProcesso(request, pk=None):
    processo = Processo.objects.get(pk=pk)
    return render(request, 'escritorio/processos/visualizar.html', {'processo': processo})


# ------------------------------------------------------------------
# Recebimentos (caso de uso 3: Registrar honorários)
# Não há tela de atualizar: mudar o valor depois desmancharia os repasses
# já calculados. Se errar, apaga e registra de novo.
# ------------------------------------------------------------------

def listarRecebimentos(request):
    recebimentos = Recebimento.objects.all()
    return render(request, 'escritorio/recebimentos/listagem.html', {'recebimentos': recebimentos})


# Passos 2 a 4: o ator digita o número do processo e o sistema mostra o
# processo. No processo com um cliente só, o cliente já vem escolhido; no
# coletivo, o ator clica no cliente de quem é o dinheiro.
def criarRecebimento(request):
    numero = request.GET.get('numero', '').strip()
    escolhido = request.GET.get('contrato', '')
    processo = None
    aviso = None
    contratos = []
    contrato = None
    if numero != '':
        processo = Processo.objects.filter(numero=numero).first()
        if processo is None:
            aviso = 'Nenhum processo cadastrado com esse número.'
        elif not processo.podeReceber():
            aviso = 'Este processo não pode receber valores: está encerrado ou sem contrato ativo.'  # [4a]
    if processo is not None and aviso is None:
        contratos = processo.contratodehonorarios_set.filter(situacao='ativo')
        if len(contratos) == 1:
            contrato = contratos[0]
        elif escolhido != '':
            contrato = contratos.filter(pk=escolhido).first()
    form = RecebimentoForm(request.POST or None)
    erro = None
    if contrato is not None and form.is_valid():
        recebimento = form.save(commit=False)
        recebimento.processo = processo
        recebimento.contrato = contrato
        valorGanho = form.cleaned_data['valorGanho']
        erro = erroDoRecebimento(recebimento, valorGanho, form.cleaned_data['pagamento'])
        if erro is None:
            contrato.valorGanho = valorGanho          # o valor decidido fica no contrato
            contrato.save()
            recebimento.numeroParcela = contrato.proximaParcela()
            recebimento.save()
            recebimento.gerarRepasses()               # repasse do cliente
            recebimento.gerarBonificacao()            # bonificação do advogado
            messages.success(request, 'Honorários registrados. Repasse e bonificação gerados.')
            return redirect('recebimento_visualizar', recebimento.pk)
    contexto = {'formulario': form, 'erro': erro, 'numero': numero, 'processo': processo,
                'aviso': aviso, 'contratos': contratos, 'contrato': contrato}
    return render(request, 'escritorio/recebimentos/criar.html', contexto)


# Apagar o recebimento apaga junto o repasse e a bonificação dele
# (CASCADE no model). O valor decidido continua gravado no contrato.
def deletarRecebimento(request, pk=None):
    recebimento = Recebimento.objects.get(pk=pk)
    if request.method == 'POST':
        recebimento.delete()
        messages.success(request, 'Recebimento, repasse e bonificação apagados.')
        return redirect('recebimento_listar')
    return render(request, 'escritorio/recebimentos/deletar.html', {'recebimento': recebimento})


def visualizarRecebimento(request, pk=None):
    recebimento = Recebimento.objects.get(pk=pk)
    contexto = {
        'recebimento': recebimento,
        'honorarios': recebimento.calcularHonorariosEscritorio(),
        'liquido': recebimento.calcularLiquidoEscritorio(),
        'repasses': recebimento.repasse_set.all(),
        'bonificacoes': recebimento.bonificacao_set.all(),
    }
    return render(request, 'escritorio/recebimentos/visualizar.html', contexto)


# ------------------------------------------------------------------
# Repasses (criados pelo caso de uso 3; aqui só se marca como pago)
# ------------------------------------------------------------------

def listarRepasses(request):
    repasses = Repasse.objects.all()
    return render(request, 'escritorio/repasses/listagem.html', {'repasses': repasses})


def atualizarRepasse(request, pk=None):
    repasse = Repasse.objects.get(pk=pk)
    form = RepasseForm(request.POST or None, instance=repasse)
    erro = None
    if form.is_valid():
        repasse = form.save(commit=False)
        if repasse.situacao not in ('pendente', 'pago'):
            erro = 'Situação deve ser pendente ou pago.'
        else:
            repasse.save()
            messages.success(request, 'Repasse atualizado.')
            return redirect('repasse_listar')
    contexto = {'formulario': form, 'erro': erro, 'repasse': repasse}
    return render(request, 'escritorio/repasses/atualizar.html', contexto)


def visualizarRepasse(request, pk=None):
    repasse = Repasse.objects.get(pk=pk)
    return render(request, 'escritorio/repasses/visualizar.html', {'repasse': repasse})


# ------------------------------------------------------------------
# Bonificações (criadas pelo caso de uso 3; aqui só se marca como paga)
# ------------------------------------------------------------------

def listarBonificacoes(request):
    bonificacoes = Bonificacao.objects.all()
    return render(request, 'escritorio/bonificacoes/listagem.html', {'bonificacoes': bonificacoes})


def atualizarBonificacao(request, pk=None):
    bonificacao = Bonificacao.objects.get(pk=pk)
    form = BonificacaoForm(request.POST or None, instance=bonificacao)
    erro = None
    if form.is_valid():
        bonificacao = form.save(commit=False)
        if bonificacao.situacao not in ('pendente', 'pago'):
            erro = 'Situação deve ser pendente ou pago.'
        else:
            bonificacao.save()
            messages.success(request, 'Bonificação atualizada.')
            return redirect('bonificacao_listar')
    contexto = {'formulario': form, 'erro': erro, 'bonificacao': bonificacao}
    return render(request, 'escritorio/bonificacoes/atualizar.html', contexto)


def visualizarBonificacao(request, pk=None):
    bonificacao = Bonificacao.objects.get(pk=pk)
    return render(request, 'escritorio/bonificacoes/visualizar.html', {'bonificacao': bonificacao})


# Caso de uso 3. Pagamento único: o valor decidido chega todo de uma vez,
# numa parcela só. Parcelado: cada recebimento é uma parte do valor decidido.
def erroDoPagamento(recebimento, valorGanho, pagamento):
    if pagamento not in ('unico', 'parcelado'):
        return 'Pagamento deve ser unico ou parcelado.'
    if pagamento == 'unico' and recebimento.contrato.recebimento_set.count() > 0:
        return 'Este cliente já tem parcela registrada, então o pagamento não é único.'
    if pagamento == 'unico' and recebimento.valor != valorGanho:
        return 'No pagamento único, o valor desta parcela é o valor decidido pelo juiz.'
    if pagamento == 'parcelado' and recebimento.valor >= valorGanho:
        return 'No pagamento parcelado, a parcela é menor que o valor decidido. Se veio tudo, use unico.'
    return None
