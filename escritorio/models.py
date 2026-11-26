from datetime import timedelta
from decimal import Decimal

from django.db import models


# Classes de dados do SAFA. Partem do diagrama de classes da parte II
# (versão 2.0, 25/10/2026) e mudaram em 22/11/2026 com o que o escritório
# faz de verdade:
#   - cada cliente de um processo tem execução e valor próprios, então o
#     dinheiro é registrado no contrato de cada cliente;
#   - qualquer processo, individual ou coletivo, pode ser pago em parcelas;
#   - o advogado responsável recebe uma bonificação sobre os honorários.

# A bonificação do advogado é 10% da parte do escritório.
PERCENTUAL_BONIFICACAO = Decimal('10')


class Cliente(models.Model):
    nome = models.CharField(max_length=150)
    tipoPessoa = models.CharField(max_length=8)        # fisica ou juridica
    # Aceita até 18 caracteres porque o CNPJ digitado com pontos, barra e
    # traço tem 18. Antes de gravar, a view deixa só os números.
    cpfCnpj = models.CharField(max_length=18, unique=True)  # RN-02
    telefone = models.CharField(max_length=15)
    email = models.EmailField(null=True, blank=True)

    def __str__(self):
        return self.nome

    # Devolve o CPF ou CNPJ sem pontos, barra e traço.
    def somenteNumeros(self):
        numeros = ''
        for caractere in self.cpfCnpj:
            if caractere.isdigit():
                numeros = numeros + caractere
        return numeros

    # CPF tem 11 números e CNPJ tem 14.
    def validarCpfCnpj(self):
        numeros = self.somenteNumeros()
        return len(numeros) == 11 or len(numeros) == 14

    # Devolve o cliente que tem esse CPF ou CNPJ, ou None se não houver.
    def buscarPorCpfCnpj(self, cpfCnpj):
        return Cliente.objects.filter(cpfCnpj=cpfCnpj).first()


class Advogado(models.Model):
    nome = models.CharField(max_length=150)
    oab = models.CharField(max_length=15, unique=True)

    def __str__(self):
        return self.nome


class Processo(models.Model):
    numero = models.CharField(max_length=25, unique=True)   # RN-02
    dataProtocolo = models.DateField()
    tipo = models.CharField(max_length=10)                  # individual ou coletivo
    via = models.CharField(max_length=15, null=True, blank=True)  # administrativa ou judicial
    # O valor que o advogado calculou e pediu na petição inicial. O valor
    # que o juiz decide é outro e fica no contrato de cada cliente.
    valorCausa = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    situacao = models.CharField(max_length=10, default='ativo')
    # O advogado que fez a petição inicial e acompanha o processo. É ele
    # quem recebe a bonificação.
    advogado = models.ForeignKey(Advogado, on_delete=models.PROTECT)

    def __str__(self):
        return self.numero

    # RN-05: só recebe se estiver ativo e tiver contrato ativo.
    def podeReceber(self):
        if self.situacao != 'ativo':
            return False
        contratosAtivos = self.contratodehonorarios_set.filter(situacao='ativo')
        return contratosAtivos.count() > 0

    # Quantos recebimentos o processo teve, somando todos os clientes.
    def contarParcelasRecebidas(self):
        return self.recebimento_set.count()

    def ehAdministrativo(self):
        return self.via == 'administrativa'


class ContratoDeHonorarios(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT)
    dataAssinatura = models.DateField()
    area = models.CharField(max_length=15)          # trabalhista ou previdenciario
    origem = models.CharField(max_length=10)        # quem fechou: comercial ou advogado
    percentualCliente = models.DecimalField(max_digits=5, decimal_places=2)
    percentualEscritorio = models.DecimalField(max_digits=5, decimal_places=2)
    situacao = models.CharField(max_length=10, default='ativo')
    # O contrato nasce sem processo. O processo é ligado depois, no
    # cadastro do processo (caso de uso 2).
    processo = models.ForeignKey(Processo, on_delete=models.PROTECT, null=True, blank=True)
    # O valor que o juiz decidiu para este cliente. Nasce vazio: só se
    # sabe depois do julgamento, e é preenchido no primeiro recebimento.
    valorGanho = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f'{self.cliente} - {self.area} ({self.dataAssinatura:%d/%m/%Y})'

    # RN-06
    def percentuaisSomam100(self):
        return self.percentualCliente + self.percentualEscritorio == 100

    # RN-16: um contrato tem no máximo um processo.
    def possuiProcesso(self):
        return self.processo is not None

    def vincularProcesso(self, processo):
        self.processo = processo
        self.save()

    # Só recebe se o contrato estiver ativo e o processo dele puder receber.
    def podeReceber(self):
        if self.situacao != 'ativo' or not self.possuiProcesso():
            return False
        return self.processo.podeReceber()

    # Soma de tudo o que já foi recebido deste cliente.
    def totalRecebido(self):
        total = Decimal('0')
        for recebimento in self.recebimento_set.all():
            total = total + recebimento.valor
        return total

    # Quanto falta receber do valor decidido pelo juiz. None enquanto o
    # valor ainda não foi informado.
    def faltaReceber(self):
        if self.valorGanho is None:
            return None
        return self.valorGanho - self.totalRecebido()

    # O menor número de parcela que ainda não foi usado neste contrato. Se
    # a parcela 2 for apagada, a próxima volta a ser a 2.
    def proximaParcela(self):
        usados = []
        for recebimento in self.recebimento_set.all():
            usados.append(recebimento.numeroParcela)
        numero = 1
        while numero in usados:
            numero = numero + 1
        return numero


class Recebimento(models.Model):
    processo = models.ForeignKey(Processo, on_delete=models.PROTECT)
    # De qual cliente é este dinheiro. Num processo coletivo cada cliente
    # recebe o seu, em datas e valores próprios.
    contrato = models.ForeignKey(ContratoDeHonorarios, on_delete=models.PROTECT)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    data = models.DateField()
    numeroParcela = models.IntegerField()
    # Na via judicial o dinheiro chega de dois jeitos (cláusula 3.1 do contrato):
    #   integral: tudo cai na conta do escritório, que repassa a parte do cliente;
    #   destaque: o juiz separa, e a parte do cliente vai direto para a conta dele.
    formaPagamento = models.CharField(max_length=10, default='integral')   # integral ou destaque

    def __str__(self):
        return f'{self.processo} - {self.contrato.cliente} - parcela {self.numeroParcela}'

    # Só há repasse quando o dinheiro do cliente passou pela conta do
    # escritório: via judicial com pagamento integral. Na via administrativa
    # (RN-17) e no destaque de honorários, o cliente recebe direto.
    def temRepasse(self):
        if self.processo.ehAdministrativo():
            return False
        return self.formaPagamento == 'integral'

    # RN-10: a parte do escritório é o valor recebido vezes o percentual
    # do escritório no contrato (de 20% a 30%).
    def calcularHonorariosEscritorio(self):
        return round(self.valor * self.contrato.percentualEscritorio / 100, 2)

    # Na via administrativa do previdenciário não há bonificação.
    def temBonificacao(self):
        return not self.processo.ehAdministrativo()

    # O que sobra para o escritório depois de pagar a bonificação.
    def calcularLiquidoEscritorio(self):
        if not self.temBonificacao():
            return self.calcularHonorariosEscritorio()
        bonificacao = Bonificacao(recebimento=self)
        return self.calcularHonorariosEscritorio() - bonificacao.calcularValor()

    # Cria o repasse pendente do cliente deste recebimento, quando há
    # repasse (ver temRepasse).
    def gerarRepasses(self):
        repasses = []
        if not self.temRepasse():
            return repasses
        repasse = Repasse(recebimento=self, cliente=self.contrato.cliente)
        repasse.valor = repasse.calcularValor()
        repasse.dataLimite = cincoDiasUteisDepois(self.data)
        repasse.save()
        repasses.append(repasse)
        return repasses

    # Cria a bonificação pendente do advogado responsável pelo processo.
    # Na via administrativa devolve None: não há bonificação.
    def gerarBonificacao(self):
        if not self.temBonificacao():
            return None
        bonificacao = Bonificacao(recebimento=self, advogado=self.processo.advogado)
        bonificacao.valor = bonificacao.calcularValor()
        bonificacao.save()
        return bonificacao


class Repasse(models.Model):
    recebimento = models.ForeignKey(Recebimento, on_delete=models.CASCADE)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    dataLimite = models.DateField()
    situacao = models.CharField(max_length=10, default='pendente')   # pendente ou pago

    def __str__(self):
        return f'{self.cliente} - R$ {self.valor}'

    # RN-10: valor recebido multiplicado pelo percentual do cliente.
    def calcularValor(self):
        contrato = self.recebimento.contrato
        return round(self.recebimento.valor * contrato.percentualCliente / 100, 2)


# A parte do advogado responsável: 10% dos honorários do escritório.
# Exemplo: o escritório recebe R$ 30.000,00 de honorários, o advogado
# recebe R$ 3.000,00 e o escritório fica com R$ 27.000,00.
class Bonificacao(models.Model):
    recebimento = models.ForeignKey(Recebimento, on_delete=models.CASCADE)
    advogado = models.ForeignKey(Advogado, on_delete=models.PROTECT)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    situacao = models.CharField(max_length=10, default='pendente')   # pendente ou pago

    def __str__(self):
        return f'{self.advogado} - R$ {self.valor}'

    def calcularValor(self):
        honorarios = self.recebimento.calcularHonorariosEscritorio()
        return round(honorarios * PERCENTUAL_BONIFICACAO / 100, 2)


# RN-09: o repasse vence em até 5 dias úteis depois do recebimento.
# Sábado e domingo não contam. Feriado não está sendo considerado.
def cincoDiasUteisDepois(data):
    diasUteis = 0
    while diasUteis < 5:
        data = data + timedelta(days=1)
        if data.weekday() < 5:     # 0 a 4 = segunda a sexta
            diasUteis = diasUteis + 1
    return data
