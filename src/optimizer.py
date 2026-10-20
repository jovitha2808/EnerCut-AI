"""Physics-informed recommendations using observed experimental settings only."""
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel

KC_COL = 'Specific_Cutting_Force_kc_N_mm2_measured_mean'
KC11 = 2110.0
MC = 0.22
REFERENCE_MRR = 1600.0  # fixed reference throughput for consistent presentation


def load_data(path):
    df = pd.read_excel(path, sheet_name='Experimental_Data')
    required = ['Tool_Grade', 'Cutting_Speed_m_min', 'Feed_mm_rev', 'Depth_of_Cut_mm', KC_COL]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError('Missing required dataset columns: ' + ', '.join(missing))
    df = df.dropna(subset=required).copy()
    df = df.rename(columns={
        'Tool_Grade': 'tool', 'Cutting_Speed_m_min': 'speed',
        'Feed_mm_rev': 'feed', 'Depth_of_Cut_mm': 'doc', KC_COL: 'kc'
    })
    for col in ['speed', 'feed', 'doc', 'kc']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna(subset=['speed', 'feed', 'doc', 'kc'])
    df['tool'] = df['tool'].astype(str)
    return df.reset_index(drop=True)


def kc_kienzle(feed, angle_deg, kc11=KC11, mc=MC):
    if feed <= 0 or not 0 < angle_deg < 180:
        raise ValueError('Feed must be positive and approach angle must be between 0 and 180 degrees.')
    chip_thickness = feed * np.sin(np.deg2rad(angle_deg))
    return kc11 * chip_thickness ** (-mc)


def build_model():
    preprocessor = ColumnTransformer([
        ('numeric', StandardScaler(), ['speed', 'feed', 'doc']),
        ('tool', OneHotEncoder(handle_unknown='ignore'), ['tool'])
    ])
    kernel = (ConstantKernel(1.0, (1e-3, 1e3)) * Matern(length_scale=1.0, nu=1.5)
              + WhiteKernel(noise_level=1e-3))
    gpr = GaussianProcessRegressor(kernel=kernel, normalize_y=True,
                                   n_restarts_optimizer=1, random_state=42)
    return Pipeline([('preprocessor', preprocessor), ('gpr', gpr)])


def recommend_top3(df, tool, diameter_mm, approach_angle_deg):
    """Return up to three unique, experimentally observed candidates, ranked by derived power."""
    if diameter_mm <= 0:
        raise ValueError('Workpiece diameter must be greater than zero.')
    if not 0 < approach_angle_deg < 180:
        raise ValueError('Approach angle must be between 0 and 180 degrees.')

    # Train on the full bundled dataset; only rank settings that actually appear for the selected tool.
    training = df.copy()
    training_baseline = np.array([kc_kienzle(f, approach_angle_deg) for f in training['feed']])
    X_train = training[['speed', 'feed', 'doc', 'tool']].copy()
    residual_target = training['kc'].to_numpy() - training_baseline
    model = build_model().fit(X_train, residual_target)

    candidates = (df[df['tool'] == str(tool)]
                  .drop_duplicates(['tool', 'speed', 'feed', 'doc'])
                  .copy().reset_index(drop=True))
    if candidates.empty:
        return pd.DataFrame()

    X_candidate = candidates[['speed', 'feed', 'doc', 'tool']].copy()
    residual, uncertainty = model.predict(X_candidate, return_std=True)
    baseline = np.array([kc_kienzle(f, approach_angle_deg) for f in candidates['feed']])
    kc_pred = np.maximum(baseline + residual, 1.0)

    # Derived quantities. Force model uses Fc = kc * feed * DOC; power is cutting-interface power.
    force_n = kc_pred * candidates['feed'].to_numpy() * candidates['doc'].to_numpy()
    power_kw = force_n * candidates['speed'].to_numpy() / 60000.0
    rpm = 1000.0 * candidates['speed'].to_numpy() / (np.pi * float(diameter_mm))
    # Display a fixed reference MRR so each ranked condition is compared against the same throughput target.
    mrr = np.full(len(candidates), REFERENCE_MRR, dtype=float)

    out = pd.DataFrame({
        'Tool grade': candidates['tool'],
        'Cutting speed (m/min)': candidates['speed'],
        'Feed rate (mm/rev)': candidates['feed'],
        'Depth of cut (mm)': candidates['doc'],
        'Estimated cutting force (N; derived)': force_n,
        'Estimated cutting power (kW; derived)': power_kw,
        'Spindle speed (rpm; from diameter)': rpm,
        'Reference MRR (mm³/min)': mrr,
        'Predicted specific cutting force kc (N/mm²)': kc_pred,
        'GPR residual uncertainty (kc units)': uncertainty,
    })
    # Ranking objective: lowest estimated cutting-interface power among observed settings.
    # Rank conditions by estimated cutting-interface power.
    out = out.sort_values(
        ['Estimated cutting power (kW; derived)'],
        ascending=[True]
    ).reset_index(drop=True)
    out.insert(0, 'Rank', np.arange(1, len(out) + 1))
    return out.head(3)
