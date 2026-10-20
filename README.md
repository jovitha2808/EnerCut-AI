# EnerCut AI Website (Flask)

A browser-based Flask interface for the EnerCut AI top-three machining-condition recommender. It is designed for deployment from GitHub to a Python web host such as Render; it does not use Streamlit.

## Files
- `app.py`: Flask web application and CSV download route.
- `src/optimizer.py`: Kienzle + GPR recommendation logic.
- `data/Ti6Al4V_ELI_turning_experimental_dataset.xlsx`: bundled dataset.
- `templates/index.html`: responsive web interface.
- `requirements.txt`: Python dependencies.
- `Procfile`: production start command for compatible hosts.

## Run locally on Windows
```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000.

## Deploy using GitHub + Render
1. Create a GitHub repository (public if using a straightforward free deployment) and upload the contents of this folder. `app.py`, `requirements.txt`, `Procfile`, `src/`, `templates/`, and `data/` must be at the repository root as shown.
2. In Render, create a **New Web Service** and connect the repository.
3. Use environment `Python 3`; build command `pip install -r requirements.txt`; start command `gunicorn app:app`.
4. Choose a plan and deploy. After a successful deployment, Render provides a URL ending in `onrender.com` that you can share.

## Model caveats
Recommendations rank observed parameter combinations by lowest estimated cutting-interface power, with material removal rate as a secondary tie-breaker. The source dataset contains 36 usable rows. Force and power are derived estimates rather than independently measured targets. The model is an academic prototype and is not validated for direct CNC control.
