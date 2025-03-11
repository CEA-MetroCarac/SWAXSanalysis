cd C:/Python310/envs/env_nxformat/Scripts
if exist jupyter.exe (
	echo jupyter already installed
) else ( 
	pip install jupyter
)

cd %~p0
jupyter notebook --notebook-dir="%~d0"
pause