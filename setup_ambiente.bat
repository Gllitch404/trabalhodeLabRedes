@echo off
setlocal EnableDelayedExpansion

title Configurador do Ambiente - Servidor HTTP/1.1 PUCRS

echo ======================================================================
echo    CONFIGURADOR AUTOMATICO DE AMBIENTE - LAB REDES PUCRS
echo ======================================================================
echo.

:: ----------------------------------------------------------------------
:: 1. VERIFICACAO DO PYTHON
:: ----------------------------------------------------------------------
echo [1/3] Verificando instalacao do Python...

set "PYTHON_CMD="
where python >nul 2>&1
if %ERRORLEVEL% equ 0 (
    for /f "tokens=*" %%v in ('python --version 2^>^&1') do set "PY_VER=%%v"
    echo   [OK] Python ja esta instalado: !PY_VER!
    set "PYTHON_CMD=python"
    goto PYTHON_CHECK_DONE
)

where py >nul 2>&1
if %ERRORLEVEL% equ 0 (
    for /f "tokens=*" %%v in ('py --version 2^>^&1') do set "PY_VER=%%v"
    echo   [OK] Python encontrado: !PY_VER!
    set "PYTHON_CMD=py"
    goto PYTHON_CHECK_DONE
)

echo   [AVISO] Python nao foi encontrado no sistema.
echo   Baixando Python 3.11 - instalador oficial 64-bit...

set "PY_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
set "PY_INSTALLER=%TEMP%\python_installer.exe"

curl.exe -L -o "%PY_INSTALLER%" "%PY_URL%"
if %ERRORLEVEL% neq 0 (
    echo   [ERRO] Falha ao baixar instalador do Python. Verifique a conexao.
    pause
    exit /b 1
)

echo   Instalando Python 3.11 em modo usuario...
"%PY_INSTALLER%" /passive InstallAllUsers=0 PrependPath=1 Include_test=0
del /f /q "%PY_INSTALLER%" >nul 2>&1

set "PATH=%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python311\Scripts;%PATH%"

where python >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo   [SUCESSO] Python instalado e configurado!
    set "PYTHON_CMD=python"
) else (
    echo   [AVISO] Python instalado em diretorio local.
    set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
)

:PYTHON_CHECK_DONE
echo.

:: ----------------------------------------------------------------------
:: 2. VERIFICACAO / INSTALACAO DO VISUAL STUDIO CODE
:: ----------------------------------------------------------------------
echo [2/3] Verificando Visual Studio Code...

set "VSCODE_CMD="
where code >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo   [OK] Visual Studio Code ja esta instalado e no PATH.
    set "VSCODE_CMD=code"
    goto VSCODE_CHECK_DONE
)

if exist "%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe" (
    echo   [OK] Visual Studio Code encontrado no diretorio de usuario.
    set "VSCODE_CMD=%LOCALAPPDATA%\Programs\Microsoft VS Code\bin\code.cmd"
    goto VSCODE_CHECK_DONE
)

echo   Visual Studio Code nao detectado.
choice /C SN /M "Deseja baixar e instalar o VS Code agora para visualizar o projeto? [S/N]"
if errorlevel 2 (
    echo   Instalacao do VS Code ignorada.
    goto VSCODE_CHECK_DONE
)

echo   Baixando VS Code User Installer oficial...
set "VS_URL=https://update.code.visualstudio.com/latest/win32-x64-user/stable"
set "VS_INSTALLER=%TEMP%\vscode_installer.exe"

curl.exe -L -o "%VS_INSTALLER%" "%VS_URL%"
if %ERRORLEVEL% neq 0 (
    echo   [AVISO] Falha ao baixar o instalador do VS Code. Prosseguindo sem ele.
) else (
    echo   Instalando Visual Studio Code silenciosamente...
    "%VS_INSTALLER%" /SILENT /MERGETASKS=!runcode,addtopath
    del /f /q "%VS_INSTALLER%" >nul 2>&1
    set "PATH=%LOCALAPPDATA%\Programs\Microsoft VS Code\bin;!PATH!"
    set "VSCODE_CMD=code"
    echo   [SUCESSO] Visual Studio Code instalado com sucesso!
)

:VSCODE_CHECK_DONE
echo.

:: ----------------------------------------------------------------------
:: 3. VERIFICACAO DOS ARQUIVOS DO PROJETO
:: ----------------------------------------------------------------------
echo [3/3] Verificando arquivos do projeto...
if not exist "www\index.html" (
    echo   Arquivos de teste em www\ ausentes. Gerando...
    %PYTHON_CMD% setup_www.py
)
if not exist "capturas\c1.pcap" (
    echo   Arquivos de captura ausentes. Gerando...
    %PYTHON_CMD% generate_captures.py
)
if not exist "RELATORIO.html" (
    echo   Gerando versao HTML do relatorio...
    %PYTHON_CMD% gerar_relatorio_html.py
)
echo   [OK] Arquivos do projeto prontos!
echo.

:: ----------------------------------------------------------------------
:: MENU PRINCIPAL
:: ----------------------------------------------------------------------
:MENU
echo ======================================================================
echo    MENU PRINCIPAL - SERVIDOR HTTP/1.1 SOCKET TCP
echo ======================================================================
echo  [1] Executar bateria completa de testes automatizados (test_server.py)
echo  [2] Iniciar o servidor HTTP/1.1 (server.py na porta 8080)
echo  [3] Executar o benchmark comparativo C1 vs C2 (benchmark.py)
echo  [4] Abrir o projeto no Visual Studio Code
echo  [5] Visualizar o Relatorio Tecnico no Navegador (RELATORIO.html)
echo  [0] Sair
echo ======================================================================

choice /C 123450 /M "Escolha uma opcao"

if errorlevel 6 (
    echo Saindo...
    exit /b 0
)
if errorlevel 5 goto OPCAO_5
if errorlevel 4 goto OPCAO_4
if errorlevel 3 goto OPCAO_3
if errorlevel 2 goto OPCAO_2
if errorlevel 1 goto OPCAO_1

:OPCAO_1
echo.
echo Executando testes automatizados...
%PYTHON_CMD% test_server.py
echo.
pause
goto MENU

:OPCAO_2
echo.
echo Iniciando servidor em http://localhost:8080 ...
echo Pressione Ctrl+C para encerrar o servidor e voltar ao menu.
echo.
%PYTHON_CMD% server.py --port 8080 --root ./www
echo.
pause
goto MENU

:OPCAO_3
echo.
echo Executando benchmark comparativo C1 vs C2...
echo (Certifique-se de que o servidor esta rodando em outro terminal se for testar agora)
%PYTHON_CMD% benchmark.py --port 8080
echo.
pause
goto MENU

:OPCAO_4
echo.
if defined VSCODE_CMD (
    echo Abrindo projeto no VS Code...
    start "" "%VSCODE_CMD%" .
) else (
    where code >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        start "" code .
    ) else (
        echo Visual Studio Code nao esta instalado nesta maquina.
    )
)
goto MENU

:OPCAO_5
echo.
echo Abrindo relatorio no navegador padrao...
echo (Para salvar em PDF: pressione Ctrl+P e selecione 'Salvar como PDF')
start "" "RELATORIO.html"
goto MENU
