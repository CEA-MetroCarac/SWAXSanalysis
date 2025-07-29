@echo off
echo [CONSOLE LOG] : Searching for the python executable

for /f "delims=" %%i in ('where python 2^>nul ^| findstr /v /i "WindowsApps"') do (
    set "PYTHON_EXE=%%i"
    goto :found
)

echo [CONSOLE LOG] : Python is not installed or has not been added to PATH
pause
exit /b 1

:found
echo [CONSOLE LOG] : Python has been found in "%PYTHON_EXE%"

set BATCH_DIR=%~dp0

echo [CONSOLE LOG] : Testing .venv existence
if not exist "%BATCH_DIR%.venv\" (
	echo [CONSOLE LOG] : Creating venv in .venv
	call %PYTHON_EXE% -m venv "%BATCH_DIR%.venv"
) else (
	echo [CONSOLE LOG] : .venv already exists, skipping creation of .venv
)

echo [CONSOLE LOG] : Changing working directory to "%BATCH_DIR%.venv\Scripts"
cd "%BATCH_DIR%.venv\Scripts"

echo [CONSOLE LOG] : Activating venv
call .\activate

if not exist ".\jupyter.exe" (
	echo [CONSOLE LOG] : Installing jupyter and dependencies...
	call .\pip install jupyter
	call .\pip install ipympl
	call .\pip install SWAXSanalysis
	call .\pip install git+https://github.com/gfreychet/smi-analysis.git
) else (
	echo [CONSOLE LOG] : Jupyter is already installed, skipping install
)

echo [CONSOLE LOG] : Changing working directory to "%BATCH_DIR%"
cd "%BATCH_DIR%"

if not exist ".\NoteBook" (
	echo [CONSOLE LOG] : Creating NoteBook folder
	mkdir ".\NoteBook"
) else (
	echo [CONSOLE LOG] : NoteBook folder already exists, skipping creation
)

echo [CONSOLE LOG] : Launching jupyter notebook
pause
jupyter notebook --notebook-dir="%BATCH_DIR%NoteBook"