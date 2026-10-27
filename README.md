# F-JEPA: JEPA models for predicting machine failures in a factory

This repository explores whether a **JEPA** (Joint-Embedding Predictive Architecture, the self-supervised approach behind I-JEPA / V-JEPA) can help with **predictive maintenance**: learning what "normal" machine behaviour looks like from unlabeled production data, then predicting failures before they happen.

The work was done during an internship. All code is in Jupyter notebooks (comments and notebook text are in French).

> **Important: most sensor data in this repository is SYNTHETIC.** The factory had no machine sensors available, so realistic sensor streams were simulated with known, injected faults in order to test the method under controlled conditions. Results on synthetic data say nothing definitive about real machines. Every synthetic dataset comes with a `LISEZMOI_*.md` file (README, in French) that describes how it was generated and pre-registers the hypotheses tested on it.

## TL;DR of the results

| Question | Answer so far |
|---|---|
| Can daily production KPIs (real Teeptrak exports) predict a bad day? | Barely. Simple baselines reach ROC-AUC ~0.57-0.59, JEPA ~0.51 (chance). |
| Can timestamped stop logs (real, one machine) predict a stop within 30 min? | Weakly. All models ~0.56-0.58 AUC; JEPA pretraining gives no gain. |
| On synthetic sensors where faults change the *dynamics*, not the levels? | A fine-tuned JEPA encoder is the best model (AUC ~0.75 on 4 machines, ~0.77-0.80 on a 16-machine fleet), clearly ahead of threshold/EWMA detectors and expert-feature boosting. |
| Does the JEPA *pretraining* itself help? | **Not so far.** The same network trained from random initialisation performs as well. More unlabeled machines, more labels and a future-prediction objective did not change that. A masked autoencoder is as good or better on frozen features. |

In short: the architecture (transformer over sensor tokens) works well, the self-supervised JEPA objective has not yet shown added value. This is an honest negative result on synthetic data, and the main open question for real sensor data.

## Repository layout

```
input/
  Données Teeptrak JPA/     Real daily Teeptrak exports (lines BIO 2 and Démoulage, 2024-09 -> 2026-08):
                            daily % of time per state / stop cause. No sensors, no failure labels.
  export-137588/            Real raw Teeptrak logs for one machine ("Tablette mouleuse", 2025-09 -> 2026-08):
                            every cycle and stop timestamped, ~4,200 unplanned stops labeled by zone/component.
  files/                    SYNTHETIC 1-min sensors (temperature, vibration, current) on the real mouleuse timeline,
                            21 injected faults + ground truth.
  capteurs_4ans/            SYNTHETIC 4-year, 1-min, 7-channel sensors for machines M1-M4, with ground truth.
    flotte_non_etiquetee/   SYNTHETIC fleet M5-M16 (variants of M1-M4), used unlabeled then labeled.
prototype/
  *.ipynb                   Experiments (see below)
  results*/                 Metrics (CSV), figures (PNG), trained weights (.pt) and score caches (.pkl)
  cache/                    Not versioned: Excel read cache, rebuilt automatically (see below)
outils/decouper.py          Split / reassemble files larger than GitHub's limit
```

## Notebooks

Run them in roughly this order; each one is self-contained and starts with a description of its goal and protocol.

| Notebook | Data | What it does | Main result (test ROC-AUC) |
|---|---|---|---|
| `F-JEPA_prototype.ipynb` | Daily Teeptrak exports | Predict a "high machine-fault day" tomorrow from 28-day windows | Baselines 0.57-0.59, JEPA probe 0.51 |
| `F-JEPA_mouleuse.ipynb`, `F-JEPA_mouleuse_v2.ipynb` | Raw stop logs (export-137588) | 5-min bins, 4 h windows, predict an unplanned stop within 30 min; alert simulation | All models 0.56-0.58; only the "pré-égouttage" zone is predictable (0.64) |
| `F-JEPA_capteurs.ipynb` | `input/files` (synthetic) | Predict a failure within 7 days from 7-day windows of 2-h tokens | EWMA vibration 0.74 best, JEPA fine-tuned 0.65 (+0.03 over random init) |
| `generation_capteurs_4ans.ipynb` | - | Generates the 4-year synthetic datasets (M1-M16) bit-for-bit from a seed | - |
| `F-JEPA_capteurs_4ans.ipynb` | `capteurs_4ans` M1-M4 | 15-min tokens, 24 h windows, failure or slowdown within 7 days; JEPA vs masked autoencoder vs baselines | JEPA fine-tuned 0.75, random init 0.73, boosting 0.72, thresholds ~0.50 |
| `F-JEPA_flotte.ipynb` | + unlabeled fleet M5-M16 | Pretrain on 4 vs 16 machines, heads trained with 2 to 24 months of labels | More unlabeled data does not help; boosting wins with few labels |
| `F-JEPA_flotte_etiquetee.ipynb` | Fleet M1-M16 labeled | Same encoders, 4x more labeled events | Fine-tuned networks 0.765 > boosting 0.724, but random init = JEPA |

Later experiments (training on 600 declared events with an extended synthetic fleet M17-M40, and predicting the next days instead of masked blocks) confirmed the same picture: best fine-tuned model ~0.80 AUC vs boosting 0.75, with random init still matching JEPA.

## Method in one paragraph

Sensor streams are cut into fixed-length tokens (e.g. 15 minutes per channel: mean, log-std and normalized shape, similar to PatchTST). A transformer **context encoder** sees a window with some blocks of tokens masked; a **predictor** must predict the *representations* of the masked blocks produced by a **target encoder** (an exponential moving average of the context encoder). No reconstruction of raw values and no labels are used during pretraining. The pretrained encoder is then evaluated with a linear probe, by fine-tuning on failure labels, and with unsupervised "surprise" scores, and always compared with the same network from random initialisation, a masked autoencoder, expert-feature gradient boosting and classic detectors (thresholds, EWMA, physical residuals). Splits are chronological (train on earlier years, test on the last year) and results are averaged over several seeds.

## Getting started

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
jupyter lab
```

Everything runs on CPU. Training notebooks take from a few minutes to several hours, but most of them have a `RECALCULER_JEPA = False` flag that reloads the trained weights and cached scores from `prototype/results*/` so the analysis reruns in minutes.

### Caches and large files

- `prototype/cache/*.pkl` (~190 MB) is **not** in the repository. `F-JEPA_mouleuse.ipynb` rebuilds it from the Excel files in `input/export-137588/` on first run (about 4 minutes).
- GitHub rejects files over 100 MB. If a large file ever needs to be versioned, split it into 45 MB parts and reassemble it after cloning:

```bash
python outils/decouper.py decouper path/to/file.pkl      # -> file.pkl.part01, .part02, ... + file.pkl.sha256
python outils/decouper.py reassembler                    # rebuilds every split file in the project and checks SHA-256
```

## Limitations

- The synthetic simulator defines what a fault looks like, so it partly decides which model wins. Conclusions need confirming on real sensor data (PLC signals, vibration, levels), which was not available.
- Confidence intervals are wide (often +/-0.06 to 0.09 AUC) because the test years contain only a few dozen failures per experiment.
- The mapping of Teeptrak stop causes to "machine fault" was not validated with the shop floor.
