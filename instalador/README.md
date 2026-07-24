# Instalador do Tuxo

Este assistente cria sua própria instância do Tuxo: bot do Telegram, vault no
GitHub, infraestrutura na AWS e autenticação do Claude — tudo separado de
qualquer outra instalação existente.

## Antes de começar

Você vai precisar, ao longo do processo (o instalador avisa se faltar algo):
- Uma conta no Telegram
- Uma conta no GitHub
- Uma conta na AWS
- Uma API key da Anthropic Console (console.anthropic.com/settings/keys), cobrada por crédito — não é a assinatura Claude Pro/Max

## Como rodar

```bash
cd instalador
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"  # a partir da raiz do projeto
python3 setup.py
```

Se fechar o terminal no meio, é só rodar `python3 setup.py` de novo — o
instalador retoma de onde parou.

Para ver o que o instalador faria sem executar nada de verdade:

```bash
python3 setup.py --dry-run
```
