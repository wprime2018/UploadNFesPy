@echo off
REM compile.bat - Script para compilar o projeto em EXE
echo ============================================
echo    COMPILADOR NFe UPLOADER PARA EXE
echo ============================================
echo.

REM Verificar se está no ambiente virtual
if not exist nfe_venv (
    echo ERRO: Ambiente virtual não encontrado!
    echo Execute build.bat primeiro para criar o ambiente
    pause
    exit /b 1
)

REM Ativar ambiente virtual
echo Ativando ambiente virtual...
call nfe_venv\Scripts\activate.bat

REM Instalar PyInstaller se não estiver instalado
pip list | findstr PyInstaller >nul
if errorlevel 1 (
    echo Instalando PyInstaller...
    pip install pyinstaller
)

echo.
echo Compilando projeto para EXE...
echo.

REM Criar arquivo de especificação de forma mais simples
(
echo import sys
echo from PyInstaller.building.build_main import main
echo 
echo if __name__ == '__main__':
echo     sys.argv = [
echo         'pyinstaller',
echo         '--name=NFe_Uploader',
echo         '--onefile',
echo         '--windowed',
echo         '--icon=icon.ico',
echo         '--add-data=config.json;.',
echo         '--hidden-import=google.auth.transport.requests',
echo         '--hidden-import=google.oauth2.credentials',
echo         '--hidden-import=google_auth_oauthlib.flow',
echo         '--hidden-import=googleapiclient.discovery',
echo         '--hidden-import=googleapiclient.http',
echo         '--hidden-import=tkinter',
echo         '--hidden-import=tkinter.ttk',
echo         '--hidden-import=tkinter.filedialog',
echo         '--hidden-import=tkinter.messagebox',
echo         'main.py'
echo     ]
echo     main()
) > compile_script.py

REM Compilar usando o método direto
echo Compilando com PyInstaller...
pyinstaller --name=NFe_Uploader ^
    --onefile ^
    --windowed ^
    --add-data "config.json;." ^
    --hidden-import "google.auth.transport.requests" ^
    --hidden-import "google.oauth2.credentials" ^
    --hidden-import "google_auth_oauthlib.flow" ^
    --hidden-import "googleapiclient.discovery" ^
    --hidden-import "googleapiclient.http" ^
    --hidden-import "tkinter" ^
    --hidden-import "tkinter.ttk" ^
    --hidden-import "tkinter.filedialog" ^
    --hidden-import "tkinter.messagebox" ^
    --hidden-import "logging.handlers" ^
    --hidden-import "io" ^
    --hidden-import "pickle" ^
    --hidden-import "json" ^
    --hidden-import "threading" ^
    --hidden-import "time" ^
    --hidden-import "pathlib" ^
    --hidden-import "datetime" ^
    main.py

if errorlevel 1 (
    echo ERRO: Falha na compilacao!
    pause
    exit /b 1
)

REM Copiar arquivos necessários para a pasta dist
echo Copiando arquivos adicionais...
if exist config.json (
    copy config.json dist\ /Y >nul
)
if exist credentials.json (
    copy credentials.json dist\ /Y >nul
)

REM Criar atalho na área de trabalho
echo Criando atalho...
echo Set oWS = WScript.CreateObject("WScript.Shell") > create_shortcut.vbs
echo sLinkFile = "%USERPROFILE%\Desktop\NFe Uploader.lnk" >> create_shortcut.vbs
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> create_shortcut.vbs
echo oLink.TargetPath = "%~dp0dist\NFe_Uploader.exe" >> create_shortcut.vbs
echo oLink.WorkingDirectory = "%~dp0dist" >> create_shortcut.vbs
echo oLink.Description = "NFe Uploader para Google Drive" >> create_shortcut.vbs
echo oLink.Save >> create_shortcut.vbs

cscript //nologo create_shortcut.vbs
del create_shortcut.vbs

echo.
echo ============================================
echo    COMPILACAO CONCLUIDA COM SUCESSO!
echo ============================================
echo.
echo Arquivos gerados:
echo   - dist\NFe_Uploader.exe
echo   - Atalho na area de trabalho
echo.
echo Pressione qualquer tecla para abrir a pasta do executavel...
pause >nul

REM Abrir pasta do executável
explorer "dist"

echo.
echo Para distribuir o programa, envie o arquivo:
echo   NFe_Uploader.exe
echo E o arquivo de configuracao:
echo   config.json
echo.
pause