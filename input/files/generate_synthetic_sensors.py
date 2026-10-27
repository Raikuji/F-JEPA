"""
Génération de signaux capteurs SYNTHÉTIQUES (température, vibration, courant)
couplés à la timeline OPE réelle de la Tablette mouleuse.

OBJECTIF : valider une démarche (pipeline, métriques, baselines vs JEPA) sur une
vérité terrain connue. Ces données NE SONT PAS des mesures. Aucune conclusion
industrielle ne peut en être tirée.

Ce qui vient des données RÉELLES : marche/arrêt, fermetures, cadence (événements
par minute), produit, fenêtres d'arrêt non planifié utilisées comme instants de panne.
Ce qui est INVENTÉ : toutes les valeurs de capteurs et les défauts (voir CFG).

Usage : python generate_synthetic_sensors.py <dossier_pickles> <dossier_sortie>
"""
import sys, os, json
import numpy as np, pandas as pd
from scipy.signal import lfilter, lfilter_zi

CFG = dict(
    seed=42,
    freq="1min",
    # --- Ordres de grandeur (hypothèses d'un technicien, NON mesurés) ---
    i_idle=4.5, i_nom=12.0,            # A : courant moteur à vide / en charge nominale
    t_rise_nom=30.0, tau_min=40.0,     # °C d'échauffement à charge nominale ; constante thermique (min)
    vib_base=1.1,                      # mm/s RMS machine saine en marche (zone « bonne » type ISO 10816)
    vib_floor=0.05,                    # mm/s bruit capteur à l'arrêt
    vib_sigma=0.08, i_sigma=0.25, t_sigma=0.15,
    # --- Défauts ---
    n_failures=dict(roulement=6, courroie=5, blocage=4, electrique_brutal=3),
    n_preventive=3,                    # dégradations stoppées par une maintenance préventive (censure)
    dur_days=dict(roulement=(14, 28), courroie=(5, 14), blocage=(2, 7), electrique_brutal=(0.0104, 0.0104)),
    min_stop_s=900,                    # panne placée au début d'un arrêt non planifié réel >= 15 min
    margin_days=2.0,                   # marge minimale entre fenêtres de défauts
    # --- Anomalies bénignes (ne doivent PAS être des alertes de panne) ---
    heatwave=("2025-09-15", "2025-09-20", 5.0),      # +5 °C ambiant (fenêtre libre de défauts ET machine active, seed 42)
    temp_drift=("2026-04-23", "2026-05-05", 3.0),    # dérive du capteur de température (°C), fenêtre libre
    n_dropouts=5, dropout_hours=(2, 6),
    stuck=("2026-05-20 08:00", 12),                  # capteur température figé 12 h, fenêtre libre
)

def ar1(n, phi, rng):
    e = rng.standard_normal(n)
    x = lfilter([1.0], [1.0, -phi], e)
    return x / x.std()

def paint(mask, df, t0, col_start="Commencé à", col_end="Terminé à"):
    s = ((df[col_start] - t0).dt.total_seconds() // 60).astype(int).to_numpy()
    e = np.ceil((df[col_end] - t0).dt.total_seconds() / 60).astype(int).to_numpy()
    n = len(mask)
    for a, b in zip(s, e):
        a, b = max(a, 0), min(b, n)
        if b > a:
            mask[a:b] = True

def main(src, out):
    rng = np.random.default_rng(CFG["seed"])
    P = pd.read_pickle(os.path.join(src, "perf_clean.pkl"))
    E = pd.read_pickle(os.path.join(src, "events.pkl")).sort_values("Event At")
    P = P[P["Durée"] > 0]
    t0 = pd.Timestamp("2025-09-01 00:00")
    t1 = P["Terminé à"].max().floor("min")
    idx = pd.date_range(t0, t1, freq=CFG["freq"]); n = len(idx)

    # ---------- contexte RÉEL ----------
    closed = np.zeros(n, bool); stop = np.zeros(n, bool)
    paint(closed, P[P["Niveau 0"] == "Fermeture"], t0)
    paint(stop, P[P["Niveau 0"] == "Arrêts non planifiés"], t0)
    cnt = E["Event At"].dt.floor("min").value_counts().reindex(idx, fill_value=0).sort_index()
    rate = cnt.rolling(5, center=True, min_periods=1).mean().to_numpy()
    running = (~closed) & (~stop) & (rate > 0.3)
    speed = np.clip(rate / 2.07, 0, 1.3) * running          # 2.07 evt/min = 1 cycle / 29 s (médiane réelle)
    prod = pd.merge_asof(pd.DataFrame({"t": idx}),
                         E[["Event At", "Product Name"]].rename(columns={"Event At": "t"}),
                         on="t", tolerance=pd.Timedelta("3h"))["Product Name"].fillna("inconnu")
    codes = {p: i for i, p in enumerate(sorted(prod.unique()))}
    fprod_tab = {p: 0.90 + 0.25 * np.random.default_rng(CFG["seed"] + codes[p]).random() for p in codes}
    fprod = prod.map(fprod_tab).to_numpy()                   # facteur de charge par produit (HYPOTHÈSE)
    chg = (prod != prod.shift()).to_numpy()
    since_chg = np.arange(n) - np.maximum.accumulate(np.where(chg, np.arange(n), 0))
    transient = np.exp(-since_chg / 8.0)                     # transitoire après changement de produit

    # ---------- défauts ----------
    cand = P[(P["Niveau 0"] == "Arrêts non planifiés") & (P["Durée"] >= CFG["min_stop_s"])]
    cand_idx = (((cand["Commencé à"] - t0).dt.total_seconds() // 60).astype(int)).to_numpy()
    cand_idx = np.unique(cand_idx[(cand_idx > 0) & (cand_idx < n - 1)])
    jobs = [(k, False) for k, c in CFG["n_failures"].items() for _ in range(c)]
    types_prev = ["roulement", "courroie"]
    jobs += [(types_prev[i % 2], True) for i in range(CFG["n_preventive"])]
    jobs.sort(key=lambda j: -CFG["dur_days"][j[0]][1])        # placer les plus longs d'abord
    margin = int(CFG["margin_days"] * 1440)
    taken, faults = [], []
    for ftype, prev in jobs:
        lo, hi = CFG["dur_days"][ftype]
        for _ in range(400):
            D = int(rng.uniform(lo, hi) * 1440)
            onset_back = int(D * (0.8 if prev else 1.0))
            ti = int(rng.choice(cand_idx))
            on = ti - onset_back
            if on < 0: continue
            if any(not (ti + margin < a or on - margin > b) for a, b in taken): continue
            taken.append((on, ti)); faults.append(dict(type=ftype, preventive=prev, onset=on, end=ti, D=D)); break
        else:
            print("WARN: placement impossible pour", ftype)
    faults.sort(key=lambda f: f["onset"])
    sev = {k: np.zeros(n) for k in CFG["n_failures"]}
    fid = np.array([""] * n, dtype=object); ftype_arr = np.array([""] * n, dtype=object)
    prec = np.zeros(n, np.int8); prevf = np.zeros(n, np.int8); sev_max = np.zeros(n)
    for j, f in enumerate(faults):
        f["id"] = f"F{j+1:02d}"
        k = np.arange(f["onset"], f["end"]); frac = (k - f["onset"]) / max(f["end"] - f["onset"], 1)
        if f["preventive"]: frac = frac * 0.8
        if f["type"] == "roulement": p = frac ** 2.5
        elif f["type"] == "courroie": p = frac
        elif f["type"] == "blocage": p = frac ** 1.5
        else: p = frac
        sev[f["type"]][k] = np.maximum(sev[f["type"]][k], p)
        sev_max[k] = p; fid[k] = f["id"]; ftype_arr[k] = f["type"]
        (prevf if f["preventive"] else prec)[k] = 1

    # contrôle : les événements bénins ne doivent pas chevaucher une fenêtre de défaut (sinon test de fausses alertes confondu)
    ben = {"canicule": CFG["heatwave"][:2], "derive_capteur": CFG["temp_drift"][:2],
           "capteur_fige": (CFG["stuck"][0], str(pd.Timestamp(CFG["stuck"][0]) + pd.Timedelta(hours=CFG["stuck"][1])))}
    for nm, (a_, b_) in ben.items():
        a_, b_ = int((pd.Timestamp(a_) - t0).total_seconds() // 60), int((pd.Timestamp(b_) - t0).total_seconds() // 60)
        if any(not (b_ < f["onset"] or a_ > f["end"]) for f in faults):
            print("WARN: événement bénin", nm, "chevauche un défaut -> changer la fenêtre dans CFG")

    pb, pc, pj, pe = sev["roulement"], sev["courroie"], sev["blocage"], sev["electrique_brutal"]

    # ---------- signaux ----------
    doy = idx.dayofyear.to_numpy(); hod = (idx.hour + idx.minute / 60).to_numpy()
    tamb = 17 + 4 * np.sin(2 * np.pi * (doy - 105) / 365) + 2.5 * np.sin(2 * np.pi * (hod - 9) / 24) \
           + 0.4 * ar1(n, 0.995, rng)
    hw = (idx >= CFG["heatwave"][0]) & (idx < CFG["heatwave"][1])
    tamb = tamb + CFG["heatwave"][2] * hw

    load = speed * fprod
    cur = CFG["i_idle"] + (CFG["i_nom"] - CFG["i_idle"]) * np.clip(load, 0, 1.4)
    cur = cur * (1 + 0.04 * pb + 0.12 * pc * np.clip(load, 0, 1) + 0.25 * pj)
    cur = cur * (1 + 0.15 * transient * running)
    cur = cur + CFG["i_sigma"] * ar1(n, 0.6, rng)
    ramp = np.zeros(n)                                       # défaut électrique brutal : 15 dernières minutes
    for f in faults:
        if f["type"] == "electrique_brutal":
            k = np.arange(f["end"] - 15, f["end"]); ramp[k] = np.linspace(0.1, 1.0, len(k))
    cur = cur * (1 + 0.6 * ramp) + 2.0 * ramp * np.abs(rng.standard_normal(n))
    cur = np.where(running, np.maximum(cur, 0.5), 0.0)

    tgt = tamb + np.where(running, CFG["t_rise_nom"] * (cur / CFG["i_nom"]) ** 2
                                   + 9 * pb + 3 * pc + 8 * pj, 0.0)
    a = np.exp(-1.0 / CFG["tau_min"])
    b_, a_ = [1 - a], [1, -a]
    temp = lfilter(b_, a_, tgt, zi=lfilter_zi(b_, a_) * tgt[0])[0]
    temp = temp + CFG["t_sigma"] * ar1(n, 0.8, rng)

    vsig = CFG["vib_sigma"] * (1 + 2 * pb)
    vib = CFG["vib_base"] * (0.6 + 0.4 * np.clip(speed, 0, 1.3)) * np.sqrt(fprod)
    vib = vib * (1 + 3.2 * pb + 1.2 * pc + 0.3 * pj) * (1 + 0.20 * transient)
    burst = (rng.random(n) < 0.02 * pc) * rng.uniform(0.5, 1.5, n)
    vib = vib * np.exp(vsig * ar1(n, 0.5, rng)) * (1 + burst)
    vib = np.where(running, vib, CFG["vib_floor"] * np.abs(rng.standard_normal(n)) + 0.02)

    # défauts capteurs (bénins) : dérive, figé, pertes de données
    ds, de, dv = CFG["temp_drift"]
    m = (idx >= ds) & (idx < de)
    drift = np.asarray((idx - pd.Timestamp(ds)).total_seconds()) / (pd.Timestamp(de) - pd.Timestamp(ds)).total_seconds()
    temp = temp + dv * np.clip(drift, 0, 1) * m
    st0 = int(((pd.Timestamp(CFG["stuck"][0]) - t0).total_seconds()) // 60); st1 = st0 + CFG["stuck"][1] * 60
    temp[st0:st1] = temp[st0]
    drop_flag = np.zeros(n, np.int8); names = ["temperature", "vibration", "courant"]
    sig = {"temperature": temp, "vibration": vib, "courant": cur}
    drop_log = []
    for i in range(CFG["n_dropouts"]):
        L = int(rng.uniform(*CFG["dropout_hours"]) * 60); s = int(rng.integers(0, n - L)); nm = names[i % 3]
        sig[nm] = sig[nm].copy(); sig[nm][s:s + L] = np.nan; drop_flag[s:s + L] = 1
        drop_log.append((nm, str(idx[s]), L))

    os.makedirs(out, exist_ok=True)
    sensors = pd.DataFrame({
        "timestamp": idx, "running": running.astype(int), "speed": speed.round(3), "product": prod.to_numpy(),
        "temperature_c": sig["temperature"].round(2), "vibration_mm_s": sig["vibration"].round(3),
        "current_a": sig["courant"].round(2)})
    labels = pd.DataFrame({
        "timestamp": idx, "fault_id": fid, "fault_type": ftype_arr, "severity": sev_max.round(4),
        "precursor_failure": prec, "preventive_degradation": prevf,
        "benign_heatwave": hw.astype(int), "benign_temp_drift": m.astype(int),
        "benign_stuck": ((np.arange(n) >= st0) & (np.arange(n) < st1)).astype(int), "benign_dropout": drop_flag})
    sensors.to_csv(os.path.join(out, "synthetic_sensors.csv.gz"), index=False)
    labels.to_csv(os.path.join(out, "synthetic_labels_GROUND_TRUTH.csv.gz"), index=False)
    ft = pd.DataFrame([{"fault_id": f["id"], "type": f["type"],
                        "kind": "degradation corrigée (préventif)" if f["preventive"] else "panne",
                        "onset": idx[f["onset"]], "failure_or_maintenance_time": idx[f["end"]],
                        "precursor_days": round((f["end"] - f["onset"]) / 1440, 2)} for f in faults])
    ft.to_csv(os.path.join(out, "synthetic_fault_events.csv"), index=False)
    json.dump({"CFG": CFG, "n_rows": n, "dropouts": drop_log, "product_load_factor": fprod_tab},
              open(os.path.join(out, "synthetic_config.json"), "w"), indent=2, default=str)
    print("OK", n, "lignes;", len(faults), "défauts")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
