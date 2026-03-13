@echo off
echo Creating conda environment: rait-assessment (Python 3.10)
conda create -n rait-assessment python=3.10 -y
echo Activating environment...
call conda activate rait-assessment
echo Installing dependencies...
pip install -r requirements.txt
echo.
echo Setup complete. To start:
echo   conda activate rait-assessment
echo   copy .env.example .env
echo   (Edit .env with your API key)
echo   streamlit run src/app/streamlit_app.py
