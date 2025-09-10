@echo off
REM build.bat - Script para compilar e executar o projeto no Windows
echo ============================================
echo    INSTALADOR E COMPILADOR NFe UPLOADER
echo ============================================
echo.

REM Verificar se Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo ERRO: Python não encontrado!
    echo Instale o Python em: https://www.python.org/downloads/
    echo Marque a opção "Add Python to PATH" durante a instalação
    pause
    exit /b 1
)

echo Python encontrado: 
python --version
echo.

REM Criar ambiente virtual
echo Criando ambiente virtual...
python -m venv nfe_venv
if errorlevel 1 (
    echo ERRO: Falha ao criar ambiente virtual
    pause
    exit /b 1
)

REM Ativar ambiente virtual
echo Ativando ambiente virtual...
call nfe_venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERRO: Falha ao ativar ambiente virtual
    pause
    exit /b 1
)

REM Instalar dependências
echo Instalando dependências...
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
if errorlevel 1 (
    echo ERRO: Falha ao instalar dependências
    pause
    exit /b 1
)

echo.
echo Instalação concluída com sucesso!
echo.

REM Criar arquivo de configuração padrão se não existir
if not exist config.json (
    echo Criando arquivo de configuração padrão...
    echo { > config.json
    echo     "credentials_file": "", >> config.json
    echo     "source_directory": "", >> config.json
    echo     "drive_folder": "NFes_XML", >> config.json
    echo     "update_interval": 300, >> config.json
    echo     "auto_start": false >> config.json
    echo } >> config.json
)

REM Criar script de execução automática
echo Criando script de execução...
echo @echo off > run.bat
echo call nfe_venv\Scripts\activate.bat >> run.bat
echo python main.py >> run.bat
echo pause >> run.bat

REM Criar atalho na área de trabalho
echo Criando atalho na área de trabalho...
echo Set oWS = WScript.CreateObject("WScript.Shell") > create_shortcut.vbs
echo sLinkFile = "%USERPROFILE%\Desktop\NFe Uploader.lnk" >> create_shortcut.vbs
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> create_shortcut.vbs
echo oLink.TargetPath = "cmd.exe" >> create_shortcut.vbs
echo oLink.Arguments = "/k cd /d "%~dp0" && call nfe_venv\Scripts\activate.bat && python main.py" >> create_shortcut.vbs
echo oLink.WorkingDirectory = "%~dp0" >> create_shortcut.vbs
echo oLink.Description = "NFe Uploader para Google Drive" >> create_shortcut.vbs
echo oLink.Save >> create_shortcut.vbs

cscript //nologo create_shortcut.vbs
del create_shortcut.vbs

echo.
echo ============================================
echo    INSTALAÇÃO CONCLUÍDA COM SUCESSO!
echo ============================================
echo.
echo Opções de execução:
echo 1. Duplo clique no atalho 'NFe Uploader' na área de trabalho
echo 2. Execute 'run.bat' nesta pasta
echo 3. Ou execute manualmente:
echo    call nfe_venv\Scripts\activate.bat
echo    python main.py
echo.
echo Pressione qualquer tecla para executar o programa agora...
pause >nul

REM Executar o programa
call nfe_venv\Scripts\activate.bat
python main.py