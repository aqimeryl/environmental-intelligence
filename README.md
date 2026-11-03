# AQIMERYL Environmental Intelligence — Build 1.0.1 (GitHub repair)

**This package is NOT Healthcare Intelligence.** It is a separate Streamlit dashboard. The existing 1.0 package was different from Healthcare, so the appearance of a healthcare dashboard in the environmental GitHub repo points to a likely incorrect upload or deployed repository/entrypoint.

## Repair `aqimeryl/environmental-intelligence`

1. In your environmental GitHub repository, inspect the root `app.py`. If it says **Toronto Healthcare Service Distribution**, it is the wrong file.
2. Remove the old Healthcare files from this repository, particularly `app.py`, `data/facilities.csv`, and any duplicate nested `app.py`. Do not delete anything from `aqimeryl/healthcare-explorer`.
3. Upload **the contents of this extracted directory** into the root of `aqimeryl/environmental-intelligence`: `app.py`, `requirements.txt`, `README.md`, `APP_IDENTITY.txt`, `data/`, `.streamlit/`.
4. Commit changes to `main`. Check GitHub `app.py` contains **Environmental Intelligence Explorer** and `APP_IDENTITY.txt` exists.
5. In Streamlit Community Cloud, confirm the environmental app points to `aqimeryl/environmental-intelligence`, branch `main`, file `app.py`, and reboot/redeploy if needed. It must not point to the healthcare repo.
6. When successful the page heading must read **Environmental Intelligence Explorer**, and sidebar **Environmental Intelligence · Build 1.0.1**. The app should not show Healthcare service filters or facility counts.

## About environmental measurements
This version has 158 neighbourhoods and Census 2021 metrics, plus support for CSV upload of *verified* tree-canopy and land-surface-temperature observations. It deliberately contains **no pre-filled environmental measurements**. It does not claim environmental-health outcomes or patient risk. Download the template from the app and add measured values with observation year and source URL. No secrets are needed.

## Local run

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Included assets
`app.py`, `requirements.txt`, `.streamlit/config.toml`, `data/neighbourhoods.csv` (158), `data/boundaries.geojson`, `data/environmental_data_template.csv`, `APP_IDENTITY.txt`. None of the healthcare facility files belongs in this repository.
## Project Status
AQIMERYL Environmental Intelligence is an exploratory research application developed under Nuvanitic. Source code is publicly visible for demonstration purposes. No open-source license is granted.
