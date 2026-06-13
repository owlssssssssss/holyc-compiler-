@echo off
setlocal EnableExtensions
set "HCC_HOME=%~dp0"
set "HCC_HOME=%HCC_HOME:~0,-1%"
python "%HCC_HOME%\hcc.py" %*
set "EXIT_CODE=%ERRORLEVEL%"
endlocal & exit /b %EXIT_CODE%