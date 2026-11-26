# SAFA

Sistema de Apoio Financeiro e Administrativo de um escritório de advocacia trabalhista e previdenciária. Acompanha o dinheiro desde o contrato com o cliente até o repasse da parte dele e a bonificação do advogado.

Projeto da disciplina de Programação Web Back-End (IFMT, Tecnologia em Sistemas para Internet), feito em Django.

## Casos de uso

1. Cadastrar contrato: procura o cliente pelo CPF e grava o contrato, que aguarda o protocolo do processo.
2. Cadastrar processo: liga o processo protocolado ao contrato do cliente.
3. Registrar honorários: grava o recebimento e gera o repasse do cliente e a bonificação do advogado.

## Como rodar

```powershell
python -m venv virtual
virtual\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Abrir `http://127.0.0.1:8000/`.
