#!/bin/bash
# setup.sh

echo "Criando ambiente virtual..."
python3 -m venv nfe_venv

echo "Ativando ambiente virtual..."
source nfe_venv/bin/activate

echo "Instalando dependências..."
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client

echo "Ambiente configurado! Execute: source nfe_venv/bin/activate"