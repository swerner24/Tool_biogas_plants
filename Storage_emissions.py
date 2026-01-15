import geopandas as gpd
import pandas as pd
from nutrients import calculate_nitrogen
from potential_env_imp import calculate_potential_env_imp
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import datetime as dt
from scipy.integrate import cumulative_trapezoid  # SciPy-Variante verwenden
from scipy.optimize import curve_fit


#Methane conversion factors for different climate zones and storage systems

#"Liquid/slurry": {"14": 18.2,"15": 14.7,"26": 7.7,"27": 7.7,"29": 7.7}, Climate Zones
#"Liquid/slurry": {"14": 13.8,"15": 13.8,"26": 13.8,"27": 13.8,"29": 13.8}, IPCC Switzerland
#"Liquid/slurry": {"14": 14.6,"15": 11.7,"26": 6.2,"27": 6.2,"29": 6.2}, Climate zones with 0.8

# === Faktor-Sätze ============================================================
FACTORS_PRE = {
    # (Beispiel: deine bisherigen Pre-Storage-Werte; falls identisch, duplizieren)
    "MCF": {
        "Liquid/slurry": {"14": 18.2, "15": 14.7, "26": 7.7, "27": 7.7, "29": 7.7},
        "Solid storage": {"14": 4.0,  "15": 4.0,  "26": 2.0, "27": 2.0, "29": 2.0},
        "Deep litter":   {"14": 10.0, "15": 10.0, "26": 10.0,"27": 10.0,"29": 10.0},
        "Poultry system":{"14": 1.5,  "15": 1.5,  "26": 1.5, "27": 1.5, "29": 1.5},
    },
    "N2O": {  # als Anteil des Total-N (Direktemissionen im Lager)
        "Liquid/slurry": 0.002,
        "Solid storage": 0.005,
        "Deep litter":   0.010,
        "Poultry system":0.001,
    }
}

FACTORS_POST = {
    # === DEINE Post-Storage-Werte (aus deinem Snippet) =======================
    "MCF" : {
        "Solid storage": {"14": 4*0.33,"15": 4*0.33,"26": 2*0.33,"27": 2*0.33,"29": 2*0.33},
        "Liquid/slurry": {"14": 18.2*0.33,"15": 14.7*0.33,"26": 7.7*0.33,"27": 7.7*0.33,"29": 7.7*0.33},
        "Deep litter": {"14": 10*0.33,"15": 10*0.33,"26": 10*0.33,"27": 10*0.33,"29": 10*0.33},
        "Poultry system": {"14": 1.5*0.33,"15": 1.5*0.33,"26": 1.5*0.33,"27": 1.5*0.33,"29": 1.5*0.33},
    },

    "N2O" : {
        "Liquid/slurry": 0.002*1.41,
        "Solid storage": 0.005*1.41,
        "Deep litter": 0.01*1.41,
        "Poultry system": 0.001*1.41,
        #"Indirect emissions due to volatilisation": 0.026,
    }
}



MCF = {
    "Solid storage": {"14": 4,"15": 4,"26": 2,"27": 2,"29": 2},
    "Liquid/slurry": {"14": 18.2,"15": 14.7,"26": 7.7,"27": 7.7,"29": 7.7},
    "Deep litter": {"14": 10,"15": 10,"26": 10,"27": 10,"29": 10},
    "Poultry system": {"14": 1.5,"15": 1.5,"26": 1.5,"27": 1.5,"29": 1.5},
}
N2O = {
    "Liquid/slurry": 0.002,
    "Solid storage": 0.005,
    "Deep litter": 0.01,
    "Poultry system": 0.001,
    #"Indirect emissions due to volatilisation": 0.026,
}





#------------------Pre-storage emissions ------ die Funktionen time dependent

#Storage emissions basis Methane


# Modified Gompertz (Cárdenas 2021)
def gompertz(t, S, Rm, lam):
    e = np.exp(1)
    return S * np.exp(-np.exp((Rm * e / S) * (lam - t) + 1.0))  # mL CH4 / g VS

# Parameter aus Table 2 (Sommer / Winter)
S_su, Rm_su, lam_su = 191.116, 3.049, 45.056
S_wi, Rm_wi, lam_wi =   1.295, 0.086,  4.460

# CH4-Dichte bei STP
RHO_CH4_STP_g_per_mL = 0.000716  # g/mL

# Zeitachse
t = np.linspace(0, 250, 251)

# M(t) in mL CH4/g VS (nicht normalisiert)
M_su_mL = gompertz(t, S_su, Rm_su, lam_su)
M_wi_mL = gompertz(t, S_wi, Rm_wi, lam_wi)

# Umrechnung in g CH4/g VS (absolute Werte)
M_su_g = M_su_mL * RHO_CH4_STP_g_per_mL
M_wi_g = M_wi_mL * RHO_CH4_STP_g_per_mL

# Normierte Werte in %
M_su_pct = (M_su_mL / S_su) * 100
M_wi_pct = (M_wi_mL / S_wi) * 100



# 1) Digitalisierten Punkte (Fig.2, for Cattle)
t_days  = np.array( [0, 1, 4, 7, 15, 20, 30, 60, 110,170,190,235,325], dtype=float)
flux_mgN2O_N_per_t_per_h = np.array([90, 190, 399, 230, 300, 110, 120, 10, 10, 10, 5, 5, 2], dtype=float)

# 2) Auf tägliches Raster + Umrechnung mg/t/h -> mg/t/d
t_daily = np.arange(t_days.min(), t_days.max()+1, 1.0)
flux_mg_per_t_per_d = np.interp(t_daily, t_days, flux_mgN2O_N_per_t_per_h) * 24.0

# 3) Kumuliert (mg/t) -> kg/t
cum_mg_per_t = cumulative_trapezoid(flux_mg_per_t_per_d, t_daily, initial=0.0)
cum_kg_per_t = cum_mg_per_t / 1e6

# 4a) % der Gesamtemission (0..100)
cum_pct_of_total = 100.0 * cum_mg_per_t / (cum_mg_per_t[-1] if cum_mg_per_t[-1] > 0 else 1.0)

# 4b) % vom Total-N (wenn Total-N bekannt; Pig ~7.8, Cattle ~5.2 kg N/t)
TOTAL_N_KG_PER_T = 5.2
cum_pct_of_TotalN = 100.0 * (cum_kg_per_t / TOTAL_N_KG_PER_T)

# Optional scaling to reported end % of Total-N (Table 2a: ~4.32% for cattle FYM)
reported_end_percent = 4.32
scale = reported_end_percent / (cum_pct_of_TotalN[-1] if cum_pct_of_TotalN[-1] > 0 else 1.0)
cum_pct_of_TotalN_scaled = cum_pct_of_TotalN * scale
cum_kg_per_t_scaled = cum_kg_per_t * scale

# 5) Build calendar x-axis starting April 1st (choose year as needed)
start_date = dt.date(2024, 4, 1)  # first day = April 1
dates_daily = [start_date + dt.timedelta(days=int(d)) for d in t_daily]
dates_points = [start_date + dt.timedelta(days=int(d)) for d in t_days]



# Deine Berechnungsfunktion
def n2o_cum_pct_curves():
    # === Inputdaten ===
    t_days  = np.array([0, 1, 4, 7, 15, 20, 30, 60, 110, 170, 190, 235, 325], dtype=float)
    flux_mgN2O_N_per_t_per_h = np.array([90, 190, 399, 230, 300, 110, 120, 10, 10, 10, 5, 5, 2], dtype=float)

    # 1) Interpolation auf Tagesraster
    t_daily = np.arange(t_days.min(), t_days.max()+1, 1.0)
    flux_mg_per_t_per_d = np.interp(t_daily, t_days, flux_mgN2O_N_per_t_per_h) * 24.0

    # 2) Datumsarray ab 1. April
    start = dt.date(2024, 4, 1)
    dates = np.array([start + dt.timedelta(days=int(d)) for d in t_daily])

    # Sommer/Winter Maske
    SUMMER_START, SUMMER_END = (4, 1), (9, 30)
    def is_summer(d: dt.date) -> bool:
        md = (d.month, d.day)
        return SUMMER_START <= md <= SUMMER_END
    summer_mask = np.array([is_summer(d) for d in dates])
    winter_mask = ~summer_mask

    def season_days(dates_slice):
        d0 = dates_slice[0]
        return np.array([(d - d0).days for d in dates_slice], dtype=float)

    # Sommer
    dates_su = dates[summer_mask]
    t_su = season_days(dates_su)
    flux_su = flux_mg_per_t_per_d[summer_mask]
    cum_su = np.cumsum((flux_su[:-1] + flux_su[1:]) / 2.0)  # Trapezregel
    cum_su = np.insert(cum_su, 0, 0.0)
    cum_su_pct = 100.0 * cum_su / cum_su[-1]

    # Winter
    dates_wi = dates[winter_mask]
    t_wi = season_days(dates_wi)
    flux_wi = flux_mg_per_t_per_d[winter_mask]
    cum_wi = np.cumsum((flux_wi[:-1] + flux_wi[1:]) / 2.0)
    cum_wi = np.insert(cum_wi, 0, 0.0)
    cum_wi_pct = 100.0 * cum_wi / cum_wi[-1]

    return (t_su, cum_su_pct), (t_wi, cum_wi_pct)




# ---------------- Gompertz model (CDF-like, 0..1) ----------------
# F(t) = exp( -exp( -k * (t - t0) ) )
def gompertz_cdf(t, k, t0):
    t = np.asarray(t, dtype=float)
    return np.exp(-np.exp(-k * (t - t0)))

# ---------------- data prep: split into summer/winter -------------
def build_season_curves():
    # Example digitized data (Thorman 2007 style) – replace with yours if needed
    t_days  = np.array([0, 1, 4, 7, 15, 20, 30, 60, 110, 170, 190, 235, 325], dtype=float)
    flux_mgN2O_N_per_t_per_h = np.array([90, 190, 399, 230, 300, 110, 120, 10, 10, 10, 5, 5, 2], dtype=float)

    # Daily interpolation & unit conversion (mg/t/h -> mg/t/day)
    t_daily = np.arange(t_days.min(), t_days.max()+1, 1.0)
    flux_mg_per_t_per_d = np.interp(t_daily, t_days, flux_mgN2O_N_per_t_per_h) * 24.0

    # Start date 01.04. (April 1)
    start = dt.date(2024, 4, 1)
    dates = np.array([start + dt.timedelta(days=int(d)) for d in t_daily])

    SUMMER_START, SUMMER_END = (4, 1), (9, 30)
    def is_summer(d: dt.date) -> bool:
        md = (d.month, d.day)
        return SUMMER_START <= md <= SUMMER_END

    summer_mask = np.array([is_summer(d) for d in dates])
    winter_mask = ~summer_mask

    def season_days(dates_slice):
        d0 = dates_slice[0]
        return np.array([(d - d0).days for d in dates_slice], dtype=float)

    # simple cumulative trapezoid with Δt = 1 day
    def cum_trapz(y):
        c = np.cumsum((y[:-1] + y[1:]) * 0.5)  # Δt=1
        return np.insert(c, 0, 0.0)

    # --- summer ---
    dates_su = dates[summer_mask]
    t_su = season_days(dates_su)
    flux_su = flux_mg_per_t_per_d[summer_mask]
    cum_su = cum_trapz(flux_su)
    y_su = cum_su / (cum_su[-1] if cum_su[-1] > 0 else 1.0)  # normalize 0..1

    # --- winter ---
    dates_wi = dates[winter_mask]
    t_wi = season_days(dates_wi)
    flux_wi = flux_mg_per_t_per_d[winter_mask]
    cum_wi = cum_trapz(flux_wi)
    y_wi = cum_wi / (cum_wi[-1] if cum_wi[-1] > 0 else 1.0)

    return (t_su, y_su), (t_wi, y_wi)

def gompertz_rate(t, S, Rm, lam):
    """Ableitung der Gompertz-Funktion = Tagesrate"""
    e = np.exp(1)
    exp_term = np.exp((Rm * e / S) * (lam - t) + 1.0)
    return (Rm * exp_term * np.exp(-exp_term))  # mL CH4/gVS pro Tag

# Beispiel: Sommer-Parameter
t_days = np.arange(0, 250)
rate_su = gompertz_rate(t_days, S_su, Rm_su, lam_su)
rate_wi = gompertz_rate(t_days, S_wi, Rm_wi, lam_wi)

# Peak finden
peak_day_su = t_days[np.argmax(rate_su)]
peak_day_wi = t_days[np.argmax(rate_wi)]

#print("CH4-Peak Sommer:", peak_day_su, "Tage")
#print("CH4-Peak Winter:", peak_day_wi, "Tage")

def weibull_cdf(t, k, lam):
    t = np.asarray(t, dtype=float)
    k = float(k)
    lam = float(lam)
    # clamp to avoid numerical issues
    t = np.maximum(t, 0.0)
    lam = max(lam, 1e-12)
    return 1.0 - np.exp(-np.power(t / lam, k))

# ---------------- generic fitter (Weibull) ----------------
def fit_weibull(t, y):
    # ensure increasing t and y within (0,1)
    mask = np.isfinite(t) & np.isfinite(y)
    t = np.asarray(t)[mask]
    y = np.asarray(y)[mask]
    order = np.argsort(t)
    t, y = t[order], y[order]
    y = np.clip(y, 1e-6, 1 - 1e-6)

    # rough inits
    # lam ~ t where F ~ 0.63 (for k≈1 since 1-exp(-1)=0.632...), fallback to median(t)
    try:
        lam_guess = float(np.interp(0.632, y, t))
        if not np.isfinite(lam_guess):
            lam_guess = float(np.median(t[t > 0])) if np.any(t > 0) else 1.0
    except Exception:
        lam_guess = float(np.median(t[t > 0])) if np.any(t > 0) else 1.0
    # k (shape) controls steepness; 1.5 is a stable starter across many shapes
    k_guess = 1.5

    p0 = [k_guess, max(lam_guess, 1e-6)]
    bounds = ([1e-6, 1e-6], [50.0, 1e9])

    popt, pcov = curve_fit(weibull_cdf, t, y, p0=p0, bounds=bounds, maxfev=20000)

    yhat = weibull_cdf(t, *popt)

    # stats
    residuals = y - yhat
    ss_res = np.sum(residuals**2)
    ss_tot = np.sum((y - y.mean())**2) + 1e-12
    r2 = 1 - ss_res/ss_tot
    rmse = float(np.sqrt(np.mean(residuals**2)))
    mae = float(np.mean(np.abs(residuals)))
    bias = float(np.mean(residuals))

    stats = {"R2": float(r2), "RMSE": rmse, "MAE": mae, "Bias": bias}

    return popt, stats, (t, y, yhat)

def peak_from_cdf(F, max_days=365):
    t = np.arange(0, max_days)
    F_vals = F(t) / 100.0   # zurück in [0..1]
    rates = np.diff(F_vals, prepend=0)   # Tageszuwachs
    peak_day = t[np.argmax(rates)]
    return peak_day, rates

# ---------------- build callables + quick check info (Weibull) ---------------
def build_season_functions_weibull():
    (t_su, y_su), (t_wi, y_wi) = build_season_curves()

    # unpack according to: (popt, stats, (t, y, yhat))
    (popt_su, stats_su, (t_su, y_su, yhat_su)) = fit_weibull(t_su, y_su)
    (popt_wi, stats_wi, (t_wi, y_wi, yhat_wi)) = fit_weibull(t_wi, y_wi)

    k_su, lam_su = popt_su
    k_wi, lam_wi = popt_wi

    # return functions that output percent (0..100)
    f_summer = lambda t: 100.0 * weibull_cdf(t, k_su, lam_su)
    f_winter = lambda t: 100.0 * weibull_cdf(t, k_wi, lam_wi)

    info = {
        "summer": {
            "k": float(k_su), "lambda": float(lam_su),
            "stats": stats_su, "t": t_su, "y": y_su, "yhat": yhat_su
        },
        "winter": {
            "k": float(k_wi), "lambda": float(lam_wi),
            "stats": stats_wi, "t": t_wi, "y": y_wi, "yhat": yhat_wi
        },
    }
    return f_summer, f_winter, info

# ---------------- example usage & validation plot ------------------
f_summer, f_winter, info = build_season_functions_weibull()
#print("Summer fit:", info["summer"])
#print("Winter fit:", info["winter"])
#print("Summer stats:", info["summer"]["stats"])
#print("Winter stats:", info["winter"]["stats"])

# Erst die Funktionen bauen
f_su_n2o, f_wi_n2o, info_n2o = build_season_functions_weibull()

# Dann Peak bestimmen
peak_day_n2o_su, rates_su = peak_from_cdf(f_su_n2o, max_days=183)
peak_day_n2o_wi, rates_wi = peak_from_cdf(f_wi_n2o, max_days=182)



#--------Ab hier die daily Berechnung----------------------------------------------------------------------------------------


#def shift_curve_left(f_original, shift_days):
    #Verschiebt die Kurve um `shift_days` nach links.
    #-Beispiel: shift_days=25 → Start 25 Tage früher.

#    def f_shifted(t):
#        t = np.asarray(t, dtype=float)
#       return f_original(t + shift_days)
#    return f_shifted



def get_ch4_cum_funcs_from_cardenas():
    """
    Liefert zwei Callables f_su_ch4(t), f_wi_ch4(t),
    die für beliebiges t (Tage) kumulative CH4-% (0..100) zurückgeben.
    """
    def f_su_ch4(t):
        t = np.asarray(t, dtype=float)
        return 100.0 * gompertz(t, S_su, Rm_su, lam_su) / S_su

    def f_wi_ch4(t):
        t = np.asarray(t, dtype=float)
        return 100.0 * gompertz(t, S_wi, Rm_wi, lam_wi) / S_wi

    return f_su_ch4, f_wi_ch4

f_summer, f_winter, info = build_season_functions_weibull()

# --- Helpers needed by the daily distribution logic --------------------------
def season_masks(year: int = 2025):
    """
    Returns:
      dates: np.ndarray of datetime.date, length 365, starting on Apr 1 of `year`
      is_summer: boolean mask (Apr–Sep = True, Oct–Mar = False)
    """
    start = dt.date(year, 4, 1)
    dates = np.array([start + dt.timedelta(days=i) for i in range(365)])
    # Summer = April (4) .. September (9), inclusive
    is_summer = np.array([(d.month >= 4) and (d.month <= 9) for d in dates])
    return dates, is_summer


def build_calendar_masks(year: int = 2025):
    dates, is_summer = season_masks(year)  # uses your function
    su_idx = np.where(is_summer)[0]
    wi_idx = np.where(~is_summer)[0]
    return dates, su_idx, wi_idx

def windowed_weights_from_cdf(season_len_calendar: int,
                              storage_days: int,
                              F_cum,
                              renormalize: bool = False):   # default = False

    storage_days = int(max(storage_days, 0))
    storage_days = min(storage_days, season_len_calendar)
    if season_len_calendar <= 0 or storage_days == 0:
        return np.zeros(season_len_calendar, dtype=float)

    # --- Gitter der Zellkanten: [-0.5, 0.5, 1.5, ...]
    edges = np.arange(-0.5, season_len_calendar - 0.5 + 1.0, 1.0)

    # Kumulative Werte an den Zellkanten
    F_edges = np.asarray(F_cum(edges), dtype=float)


    # Start/Ende sauber normieren
    F_start = float(F_edges[0])
    F_end   = float(F_edges[-1])
    span = F_end - F_start

    if span <= 0:
        w_full = np.ones(season_len_calendar, dtype=float) / season_len_calendar
    else:
        F_edges = (F_edges - F_start) / span
        F_edges = np.clip(F_edges, 0.0, 1.0)

        w_full = np.diff(F_edges)  # Differenzen → Gewichte
        w_full = np.clip(w_full, 0.0, None)

        if renormalize:  # <--- optionales Renormalisieren
            s = w_full.sum()
            if s > 0:
                w_full = w_full / s

    out = np.zeros(season_len_calendar, dtype=float)
    out[:storage_days] = w_full[:storage_days]
    return out

def windowed_weights_from_cdf_peak(season_len_calendar: int,
                                   storage_days: int,
                                   F_cum,
                                   renormalize: bool = False):
    """
    Variante von windowed_weights_from_cdf:
    Schneidet die Gewichte vorne bis zum Peak ab,
    sodass die Kurve direkt beim Maximum startet.
    """
    # --- Original-Gewichte wie gehabt ---
    storage_days = int(max(storage_days, 0))
    storage_days = min(storage_days, season_len_calendar)
    if season_len_calendar <= 0 or storage_days == 0:
        return np.zeros(season_len_calendar, dtype=float)

    edges = np.arange(-0.5, season_len_calendar - 0.5 + 1.0, 1.0)
    F_edges = np.asarray(F_cum(edges), dtype=float)

    F_start, F_end = float(F_edges[0]), float(F_edges[-1])
    span = F_end - F_start

    if span <= 0:
        w_full = np.ones(season_len_calendar, dtype=float) / season_len_calendar
    else:
        F_edges = (F_edges - F_start) / span
        F_edges = np.clip(F_edges, 0.0, 1.0)
        w_full = np.diff(F_edges)
        w_full = np.clip(w_full, 0.0, None)
        if renormalize:
            s = w_full.sum()
            if s > 0:
                w_full = w_full / s

    # --- Peak-Schnitt ---
    peak_idx = int(np.argmax(w_full))
    w_cut = w_full[peak_idx:storage_days]

    # Optional: Renormalisierung
    if renormalize and w_cut.sum() > 0:
        w_cut = w_cut / w_cut.sum()

    # --- Neues Array auf Länge season_len_calendar ---
    out = np.zeros(season_len_calendar, dtype=float)
    out[:len(w_cut)] = w_cut
    return out

def windowed_weights_from_cdf_offset(season_len_calendar, storage_days, F_cum,
                                         offset_days, renormalize=False):
    edges = np.arange(-0.5, season_len_calendar - 0.5 + 1.0, 1.0)
    F_edges = np.asarray(F_cum(edges), dtype=float)

    # Gewichte aus kumulativer Kurve
    F_start, F_end = float(F_edges[0]), float(F_edges[-1])
    span = F_end - F_start
    if span <= 0:
        w_full = np.ones(season_len_calendar) / season_len_calendar
    else:
        F_edges = (F_edges - F_start) / span
        w_full = np.diff(F_edges)
        w_full = np.clip(w_full, 0.0, None)

    # Peak finden
    peak_idx = int(np.argmax(w_full))

    # Fall A: Peak ganz am Anfang (0 oder 1) → Stall-Cut
    if peak_idx <= 1:
        start_idx = min(offset_days, len(w_full))  # Stalltage wegschneiden
    else:
        # Fall B: normaler Offset vor Peak
        start_idx = max(0, peak_idx - offset_days)

    # Zuschneiden
    w_cut = w_full[start_idx:storage_days]

    if renormalize and w_cut.sum() > 0:
        w_cut = w_cut / w_cut.sum()

    out = np.zeros(season_len_calendar, dtype=float)
    out[:len(w_cut)] = w_cut
    return out






def precompute_weights(days_summer, days_winter, f_su_ch4, f_wi_ch4, f_su_n2o, f_wi_n2o):
    # CH4 = Offset
    w_su_ch4 = windowed_weights_from_cdf_offset(183, 183, f_su_ch4, offset_days=20, renormalize=False)
    w_wi_ch4 = windowed_weights_from_cdf_offset(182, 182, f_wi_ch4, offset_days=2, renormalize=False)

    # N2O = Original
    w_su_n2o = windowed_weights_from_cdf_offset(183, 183, f_su_n2o, offset_days=3, renormalize=False)
    w_wi_n2o = windowed_weights_from_cdf_offset(182, 182, f_wi_n2o, offset_days=3, renormalize=False)

    return w_su_ch4, w_wi_ch4, w_su_n2o, w_wi_n2o


def seasonal_split(E_year, ratio_su_to_wi):
    alpha_su = ratio_su_to_wi / (ratio_su_to_wi + 1)
    alpha_wi = 1 / (ratio_su_to_wi + 1)
    return E_year * alpha_su, E_year * alpha_wi




def compute_daily_emissions_for_system(
        storage_type: str,
        climate_zone: str,
        year: int,
        ch4_potential: float,
        ch4_potential_unit: str = "Nm3_CH4",
        total_N_kg_y: float = 0.0,
        CH4_density_kg_per_m3: float = 0.67,
        days_summer: int = 0,
        days_winter: int = 0,
        n2o_is_N2O_N: bool = True,
        ch4_cum_funcs: tuple | None = None,  # (f_su_ch4, f_wi_ch4)
        n2o_cum_funcs: tuple | None = None,  # (f_su_n2o, f_wi_n2o)
        ch4_su_to_wi: float = 15,
        n2o_su_to_wi: float = 44.0,
        factors: dict | None = None,
):
    if factors is None:
        factors = FACTORS_PRE  # default
    mcf_table = factors["MCF"]
    n2o_table = factors["N2O"]


    # --- Cum-Funktionen auswählen ---
    if ch4_cum_funcs is None:
        f_su_ch4, f_wi_ch4 = get_ch4_cum_funcs_from_cardenas()
    else:
        f_su_ch4, f_wi_ch4 = ch4_cum_funcs

    if n2o_cum_funcs is None:
        f_su_n2o, f_wi_n2o, _ = build_season_functions_weibull()
    else:
        f_su_n2o, f_wi_n2o = n2o_cum_funcs

    # --- Kalender ---
    dates, su_idx, wi_idx = build_calendar_masks(year)
    n_su, n_wi = len(su_idx), len(wi_idx)

    # --- Annual CH4 (kg) ---
    mcf_percent = float(mcf_table[storage_type][climate_zone])
    mcf_decimal = mcf_percent / 100.0

    if ch4_potential_unit.lower() == "nm3_ch4":
        CH4_annual_kg = ch4_potential * mcf_decimal * CH4_density_kg_per_m3
    elif ch4_potential_unit.lower() == "kg_ch4":
        CH4_annual_kg = ch4_potential * mcf_decimal
    else:
        raise ValueError("ch4_potential_unit must be 'Nm3_CH4' or 'kg_CH4'")

    # --- Annual N2O (kg) ---
    n2o_frac = float(n2o_table[storage_type])
    if n2o_is_N2O_N:
        N2O_N_annual_kg = total_N_kg_y * n2o_frac
        N2O_annual_kg = N2O_N_annual_kg * (44.0 / 28.0)
    else:
        N2O_annual_kg = total_N_kg_y * n2o_frac
        N2O_N_annual_kg = N2O_annual_kg * (28.0 / 44.0)

    # --- Split summer/winter totals ---
    CH4_su_total, CH4_wi_total = seasonal_split(CH4_annual_kg, ch4_su_to_wi)
    N2O_su_total, N2O_wi_total = seasonal_split(N2O_annual_kg, n2o_su_to_wi)

    # --- Saisonkurven (Form; Peak-Cut optional, aber am Ende SUMME=1) ---

    w_su_ch4_full = windowed_weights_from_cdf_offset(183, 183, f_su_ch4,
                                                     offset_days=20, renormalize=False)
    w_wi_ch4_full = windowed_weights_from_cdf_offset(182, 182, f_wi_ch4,
                                                     offset_days=2, renormalize=False)
    w_su_n2o_full = windowed_weights_from_cdf_offset(n_su, n_su, f_su_n2o,
                                                     offset_days=3, renormalize=False)
    w_wi_n2o_full = windowed_weights_from_cdf_offset(n_wi, n_wi, f_wi_n2o,
                                                     offset_days=3, renormalize=False)

    # --- Cuts (falls du < volle Saison abbildest) + RENORMALISIEREN AUF 1 ---
    w_su_ch4 = w_su_ch4_full[:days_summer]
    w_wi_ch4 = w_wi_ch4_full[:days_winter]
    w_su_n2o = w_su_n2o_full[:days_summer]
    w_wi_n2o = w_wi_n2o_full[:days_winter]

    # --- Absolute Tageswerte (nur Split-Mengen × Form) ---
    ch4_daily = np.zeros(365)
    n2o_daily = np.zeros(365)

    ch4_daily[su_idx[:len(w_su_ch4)]] = CH4_su_total * w_su_ch4
    ch4_daily[wi_idx[:len(w_wi_ch4)]] = CH4_wi_total * w_wi_ch4

    n2o_daily[su_idx[:len(w_su_n2o)]] = N2O_su_total * w_su_n2o
    n2o_daily[wi_idx[:len(w_wi_n2o)]] = N2O_wi_total * w_wi_n2o



    return {
        "dates": dates,
        "ch4_kg_daily": ch4_daily,
        "n2o_kg_daily": n2o_daily,
        "annual": {"ch4_kg": float(CH4_annual_kg), "n2o_kg": float(N2O_annual_kg)},
        "n2o_n_kg": float(N2O_N_annual_kg),
        "meta": {
            "storage_type": storage_type,
            "climate_zone": climate_zone,
            "mcf_percent": mcf_percent,
            "days_summer": days_summer,
            "days_winter": days_winter,
            "ch4_su_to_wi": ch4_su_to_wi,
            "n2o_su_to_wi": n2o_su_to_wi,
        }
    }

def debug_plot_daily_weights(f_su, f_wi, days_summer=150, days_winter=215, offset_days=2):
    """
    Debug-Plot für Tagesgewichte aus kumulativer Kurve:
      (a) Original-Verteilung
      (b) Peak-Cut-Verteilung
      (c) Offset-Verteilung (Lag-Phase abgeschnitten, z.B. 10 Tage)
    """
    # Kalenderlängen (Sommer/ Winter)
    n_su, n_wi = 183, 182  # oder dein calendar_masks

    # --- Original-Gewichte ---
    w_su = windowed_weights_from_cdf(n_su, days_summer, f_su, renormalize=False)
    w_wi = windowed_weights_from_cdf(n_wi, days_winter, f_wi, renormalize=False)

    # --- Peak-Cut-Gewichte ---
    w_su_peak = windowed_weights_from_cdf_peak(n_su, days_summer, f_su, renormalize=True)
    w_wi_peak = windowed_weights_from_cdf_peak(n_wi, days_winter, f_wi, renormalize=True)

    # --- Offset-Gewichte ---
    w_su_offset = windowed_weights_from_cdf_offset(n_su, days_summer, f_su,
                                               offset_days=2, renormalize=False)
    w_wi_offset = windowed_weights_from_cdf_offset(n_wi, days_winter, f_wi,
                                               offset_days=2, renormalize=False)






def debug_plot_offset(f_wi, days_winter=215, offset=2):
    w_orig  = windowed_weights_from_cdf(215, days_winter, f_wi, renormalize=False)
    w_peak  = windowed_weights_from_cdf_peak(215, days_winter, f_wi, renormalize=False)
    w_off   = windowed_weights_from_cdf_offset(215, days_winter, f_wi,
                                               pre_peak_offset=offset,
                                               renormalize=False)





f_su_ch4, f_wi_ch4 = get_ch4_cum_funcs_from_cardenas()
debug_plot_daily_weights(f_su_ch4, f_wi_ch4, days_summer=175, days_winter=215)

f_su_n2o, f_wi_n2o, _ = build_season_functions_weibull()
debug_plot_daily_weights(f_su_n2o, f_wi_n2o, days_summer=175, days_winter=215)






# --- 2) multi-system wrapper ---------------------------------------------------
def compute_daily_storage_emissions_multi(systems, year=2025):
    totals_ch4 = np.zeros(365)
    totals_n2o = np.zeros(365)
    total_annual = {"ch4_kg": 0.0, "n2o_kg": 0.0, "n2o_n_kg": 0.0}
    per_system = {}
    dates = None

    for sys in systems:
        res = compute_daily_emissions_for_system(
            storage_type=sys["storage_type"],
            climate_zone=sys["climate_zone"],
            year=year,
            ch4_potential=sys["ch4_potential"],
            ch4_potential_unit=sys.get("ch4_potential_unit","Nm3_CH4"),
            total_N_kg_y=sys["total_N_kg_y"],
            CH4_density_kg_per_m3=sys.get("CH4_density_kg_per_m3", 0.67),
            days_summer=sys["days_summer"],
            days_winter=sys["days_winter"],
            n2o_is_N2O_N=sys.get("n2o_is_N2O_N", True),
            ch4_cum_funcs=sys.get("ch4_cum_funcs", None),
            n2o_cum_funcs=sys.get("n2o_cum_funcs", None),
            factors=sys.get("factors", None),
        )
        if dates is None:
            dates = res["dates"]
        per_system[sys["storage_type"]] = res

        totals_ch4 += res["ch4_kg_daily"]
        totals_n2o += res["n2o_kg_daily"]
        total_annual["ch4_kg"]  += res["annual"]["ch4_kg"]
        total_annual["n2o_kg"]  += res["annual"]["n2o_kg"]

    return {
        "dates": dates,
        "total": {"ch4_kg_daily": totals_ch4, "n2o_kg_daily": totals_n2o},
        "annual_total": total_annual,         # <-- sums across systems
        "systems": per_system
    }
#-------------------Test Aufruf------------------

## CH4-Kurven aus Cárdenas

f_su_ch4, f_wi_ch4 = get_ch4_cum_funcs_from_cardenas()
#f_su_ch4, f_wi_ch4 = get_ch4_cum_funcs_from_cardenas()
#f_su_ch4_shifted = shift_curve_left(f_su_ch4, shift_days=46)
#f_wi_ch4_shifted = shift_curve_left(f_wi_ch4, shift_days=5)
# N2O-Kurven aus Thorman-Fit
f_su_n2o, f_wi_n2o, info_n2o = build_season_functions_weibull()

# Eine Anlage/System rechnen
res = compute_daily_emissions_for_system(
    storage_type="Liquid/slurry",
    climate_zone="14",
    year=2025,
    ch4_potential=7.15,            # z.B. Nm3 CH4 / Jahr
    ch4_potential_unit="Nm3_CH4",      # oder "kg_CH4"
    total_N_kg_y=9.63,
    days_summer=30,
    days_winter=180,
    ch4_cum_funcs=(f_su_ch4, f_wi_ch4),     # CH4-Form
    n2o_cum_funcs=(f_su_n2o, f_wi_n2o),     # N2O-Form
)

# -> Arrays aus dem Ergebnis holen
dates     = res["dates"]
ch4_daily = res["ch4_kg_daily"]
n2o_daily = res["n2o_kg_daily"]



#print("Annual CH4 total (kg):", round(float(ch4_daily.sum()), 2))
#print("Annual N2O total (kg):", round(float(n2o_daily.sum()), 2))












# -------Mehrere Systeme
systems = [

    {
        "storage_type": "Liquid/slurry",
        "climate_zone": "14",
        "ch4_potential": 13.8*0.74,
        "ch4_potential_unit": "Nm3_CH4",
        "total_N_kg_y":5.0*0.74,
        "days_summer": 90,
        "days_winter": 180,
        "ch4_cum_funcs": (f_su_ch4, f_wi_ch4),  # <--- hier mitgeben!
        "n2o_cum_funcs": (f_su_n2o, f_wi_n2o),
    },
    {
        "storage_type": "Solid storage",
        "climate_zone": "14",
        "ch4_potential": 50.6*0.22,
        "ch4_potential_unit": "Nm3_CH4",
        "total_N_kg_y": 5.0*0.22,
        "days_summer": 90,
        "days_winter": 180,
        "ch4_cum_funcs": (f_su_ch4, f_wi_ch4),  # <--- hier mitgeben!
        "n2o_cum_funcs": (f_su_n2o, f_wi_n2o),
    },
    {
        "storage_type": "Deep litter",
        "climate_zone": "14",
        "ch4_potential": 50.6 * 0.04,
        "ch4_potential_unit": "Nm3_CH4",
        "total_N_kg_y": 5* 0.04,
        "days_summer": 90,
        "days_winter": 180,
        "ch4_cum_funcs": (f_su_ch4, f_wi_ch4),  # <--- hier mitgeben!
        "n2o_cum_funcs": (f_su_n2o, f_wi_n2o),
    },

]

res_multi = compute_daily_storage_emissions_multi(systems, year=2025)

# -> Arrays aus dem Ergebnis holen
dates     = res_multi["dates"]
total_ch4 = res_multi["total"]["ch4_kg_daily"]
total_n2o = res_multi["total"]["n2o_kg_daily"]


#print("Annual CH4 total_cattle (kg):", round(float(total_ch4.sum()), 2))
#print("Annual N2O total_cattle (kg):", round(float(total_n2o.sum()), 2))






def build_systems_for_polygon(row, days_summer, days_winter):
    systems = []
    total_ch4 = row.Total_biomethane_yield_available_m3
    total_N = row.Total_avail_N_kg

    systems.append({
        "storage_type": "Liquid/slurry",
        "climate_zone": str(row.climate_zone),
        "ch4_potential": total_ch4 * row.Share_liquid_slurry,
        "ch4_potential_unit": "Nm3_CH4",
        "total_N_kg_y": total_N * row.Share_liquid_slurry,
        "days_summer": days_summer,
        "days_winter": days_winter,
    })

    systems.append({
        "storage_type": "Solid storage",
        "climate_zone": str(row.climate_zone),
        "ch4_potential": total_ch4 * row.Share_solid_storage,
        "ch4_potential_unit": "Nm3_CH4",
        "total_N_kg_y": total_N * row.Share_solid_storage,
        "days_summer": days_summer,
        "days_winter": days_winter,
    })

    systems.append({
        "storage_type": "Deep litter",
        "climate_zone": str(row.climate_zone),
        "ch4_potential": total_ch4 * row.Share_deep_litter,
        "ch4_potential_unit": "Nm3_CH4",
        "total_N_kg_y": total_N * row.Share_deep_litter,
        "days_summer": days_summer,
        "days_winter": days_winter,
    })

    systems.append({
        "storage_type": "Poultry system",
        "climate_zone": str(row.climate_zone),
        "ch4_potential": total_ch4 * row.Share_poultry_system,
        "ch4_potential_unit": "Nm3_CH4",
        "total_N_kg_y": total_N * row.Share_poultry_system,
        "days_summer": days_summer,
        "days_winter": days_winter,
    })

    return systems


def emissions_for_polygon(row, weights, days_summer, days_winter):
    w_su_ch4, w_wi_ch4, w_su_n2o, w_wi_n2o = weights

    total_ch4_sum, total_n2o_sum = 0.0, 0.0

    systems = {
        "Liquid/slurry": "Share_liquid_slurry",
        "Solid storage": "Share_solid_storage",
        "Deep litter": "Share_deep_litter",
        "Poultry system": "Share_poultry_system",
    }

    for sys, share_col in systems.items():
        share = getattr(row, share_col, 0.0)
        if share <= 0:
            continue

        # --- Jahrespotenziale ---
        ch4_total = (
            row.Total_biomethane_yield_available_m3
            * share
            * 0.67
            * (MCF[sys][row.climate_zone] / 100)
        )
        n2o_total = (
            row.Total_avail_N_kg
            * share
            * N2O[sys]
            * (44 / 28)
        )

        # --- Saison-Split ---
        ch4_su_total, ch4_wi_total = seasonal_split(ch4_total, 15)
        n2o_su_total, n2o_wi_total = seasonal_split(n2o_total, 44)

        # --- Jetzt Anteil statt absolute Summe ---
        frac_su_ch4 = w_su_ch4[:days_summer].sum()
        frac_wi_ch4 = w_wi_ch4[:days_winter].sum()
        frac_su_n2o = w_su_n2o[:days_summer].sum()
        frac_wi_n2o = w_wi_n2o[:days_winter].sum()

        total_ch4_sum += ch4_su_total * frac_su_ch4 + ch4_wi_total * frac_wi_ch4
        total_n2o_sum += n2o_su_total * frac_su_n2o + n2o_wi_total * frac_wi_n2o

    return total_ch4_sum, total_n2o_sum



def debug_seasonal_split(E_year, ratio_su_to_wi, label="Emission"):
    """
    Debug-Funktion: Teilt eine Jahressumme in Sommer/Winter
    und zeigt, dass Summer + Winter = Year.
    """
    alpha_su = ratio_su_to_wi / (ratio_su_to_wi + 1.0)
    alpha_wi = 1.0 / (ratio_su_to_wi + 1.0)

    E_summer = E_year * alpha_su
    E_winter = E_year * alpha_wi

    # print(f"\n--- Debug Split für {label} ---")
    # print(f"Jahressumme:   {E_year:,.2f}")
    # print(f"Sommer total:  {E_summer:,.2f}  ({alpha_su:.2%} Anteil)")
    # print(f"Winter total:  {E_winter:,.2f}  ({alpha_wi:.2%} Anteil)")
    # print(f"Check: Summer + Winter = {E_summer + E_winter:,.2f}")

    return E_summer, E_winter


# Beispielaufrufe:
debug_seasonal_split(1000.0, 15, label="CH₄")
debug_seasonal_split(500.0, 44, label="N₂O")
# -------Post-storage emissions Digestate für beide (evtl annahme von Amon et al.2006, wie viel weniger dass es ist.)

