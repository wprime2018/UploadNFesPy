@echo off
REM setup.bat

echo Criando ambiente virtual...
python -m venv nfe_venv

echo Ativando ambiente virtual...
call nfe_venv\Scripts\activate.bat

echo Instalando dependências...
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client

echo Ambiente configurado! Execute: nfe_venv\Scripts\activate.bat
pause