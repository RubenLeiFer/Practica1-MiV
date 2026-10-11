"""
preprocess.py — Fase 2: adquisició i preprocessament de dades
Pràctica 1 (Modelització i Visualització de Dades, URV)

Entrada : data/raw/*.csv         (un CSV per any, exportat de l'Airtable del tracker de Farhan Noor)
Sortida : data/clean/layoffs_clean.csv    (un registre = un esdeveniment d'acomiadament)
          data/clean/yearly_summary.csv   (resum per any, per documentar la qualitat de les dades)

Execució: python preprocess.py
"""
import difflib
from pathlib import Path

import numpy as np
import pandas as pd

RAW_DIR = Path("data/raw")
CLEAN_DIR = Path("data/clean")
CLEAN_DIR.mkdir(parents=True, exist_ok=True)

TOP_N = 10               # empreses que es mostren individualment al dashboard; la resta -> "Altres empreses"
MAX_EMPTY_SHARE = 0.90   # una columna buida en >= 90 % dels registres no aporta informació
REQUIRED = ["studio", "date", "headcount"]

# Correccions manuals: NOMÉS erratades o variants evidents de la mateixa entitat.
# El bloc P2 imprimeix noms gairebé idèntics perquè hi puguis afegir els que et faltin.
STUDIO_FIXES = {
    "Heartmachine": "Heart Machine", "Pirahna Games": "Piranha Games", "Might Yell": "Mighty Yell",
    "RecRoom": "Rec Room", "Bioware Games": "BioWare", "HiRez Studios": "Hi-Rez Studios",
    "Zenimax Online": "ZeniMax Online", "Rare LTD.": "Rare Ltd.", "jar of Sparks": "Jar of Sparks",
    "Netease": "NetEase",
}
PARENT_FIXES = {
    "App Lovin": "AppLovin", "SuperCell": "Supercell", "TakeTwo Interactive": "Take-Two Interactive",
    "Warner Brothers": "Warner Bros.", "Netease": "NetEase", "PlayTika": "Playtika",
}

# ══════════════════════════════════════════════════════════════════════════════════════════
# CARREGA
# Els CSV d'Airtable porten BOM (per això 'utf-8-sig'). Es llegeix tot com a text (dtype=str)
# i sense convertir buits a NaN encara: ho decidim nosaltres columna a columna.
# ══════════════════════════════════════════════════════════════════════════════════════════
files = sorted(RAW_DIR.glob("*.csv"))
if not files:
    raise SystemExit(f"No hi ha cap CSV a {RAW_DIR}/")
df = pd.concat(
    [pd.read_csv(f, dtype=str, keep_default_na=False, encoding="utf-8-sig").assign(source_file=f.name)
     for f in files],
    ignore_index=True,
)
n_loaded = len(df)

# Noms de columna uniformes (la web diu "Number Affected" i el CSV "Headcount")
df = df.rename(columns={"Number Affected": "Headcount"})
df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
missing = [c for c in REQUIRED if c not in df.columns]
if missing:
    raise SystemExit(f"Falten columnes obligatòries: {missing}. Columnes trobades: {list(df.columns)}")

# ══════════════════════════════════════════════════════════════════════════════════════════
# P1. NETEJA I TIPATGE
# Problemes: espais sobrants ("Electronic Arts        "), columnes pràcticament buides,
# dates i xifres en format text, i xifres que falten.
# ══════════════════════════════════════════════════════════════════════════════════════════
# 1.1 Espais: sense això "Console" i " Console   " serien categories diferents als filtres.
for c in df.columns:
    df[c] = df[c].str.replace(r"\s+", " ", regex=True).str.strip()

# 1.2 Columnes inútils: 'field_1' està 100 % buida i les ubicacions >90 % buides. Es calcula, no es fixa a mà.
empty_share = (df.drop(columns="source_file") == "").mean()
dropped_cols = [c for c in empty_share[empty_share >= MAX_EMPTY_SHARE].index if c not in REQUIRED]
df = df.drop(columns=dropped_cols)

# 1.3 Files sense estudi ni data no són esdeveniments.
df = df[(df["studio"] != "") & (df["date"] != "")].copy()

# 1.4 Data a datetime. Format ISO a l'Airtable; les inconsistents es descarten i s'informa.
df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d", errors="coerce")
n_bad_date = int(df["date"].isna().sum())
df = df.dropna(subset=["date"]).copy()

# 1.5 Xifra d'acomiadats. DECISIÓ CLAU: un buit NO es converteix en 0 (seria afirmar que no hi
# va haver acomiadaments). Es deixa NaN i es guarda l'estat a 'headcount_status'.
#   número sol -> exacte | buit -> no_disponible | amb "~" -> aproximat | "?" -> desconegut
# (els dos últims no apareixen al CSV d'Airtable de 2025, però es contemplen per si algun any en porta)
def parse_headcount(s: str):
    if s == "":
        return np.nan, "no_disponible"
    if s == "?":
        return np.nan, "desconegut"
    t = s.replace(",", "")
    approx = t.endswith("~")
    t = t.rstrip("~").strip()
    if t.isdigit():
        return float(t), ("aproximat" if approx else "exacte")
    return np.nan, "revisar"

parsed = df["headcount"].map(parse_headcount)
df["headcount"] = parsed.map(lambda t: t[0])
df["headcount_status"] = parsed.map(lambda t: t[1])

# ══════════════════════════════════════════════════════════════════════════════════════════
# P2. NORMALITZACIÓ D'ENTITATS (necessària per filtrar per empresa)
# Problemes: la mateixa entitat amb noms diferents ("Heart Machine"/"Heartmachine",
# "App Lovin"/"AppLovin"), erratades ("Pirahna") i matriu buida en molts estudis independents.
# Sense això, un filtre per empresa partiria una empresa en diverses.
# ══════════════════════════════════════════════════════════════════════════════════════════
df["studio"] = df["studio"].replace(STUDIO_FIXES)
df["parent"] = df["parent"].replace(PARENT_FIXES) if "parent" in df else ""
df["type"] = df["type"].replace("", "Sense classificar") if "type" in df else "Sense classificar"
# 'company' = empresa matriu si n'hi ha; si no, l'estudi (és la unitat pel filtre).
df["company"] = df["parent"].where(df["parent"] != "", df["studio"])

names = sorted(set(df["studio"]) | set(df["company"]))
pairs = {tuple(sorted((a, b))) for a in names for b in difflib.get_close_matches(a, names, n=3, cutoff=0.85) if a != b}
for a, b in sorted(pairs):
    print(f"[revisar P2] Mateixa entitat?  '{a}'  ~  '{b}'")

# ══════════════════════════════════════════════════════════════════════════════════════════
# P3. REORDENACIÓ LÒGICA I VARIABLES TEMPORALS
# Problema: l'ordre del fitxer és arbitrari i l'alfabètic de les categories (biaix d'ordenació) no
# diu res. Es fa servir l'ordre cronològic, i les empreses es rànquegen per impacte.
# ══════════════════════════════════════════════════════════════════════════════════════════
df = df.sort_values(["date", "company", "studio"]).reset_index(drop=True)
df["year"], df["month"] = df["date"].dt.year, df["date"].dt.month
df["quarter"], df["day_of_year"] = df["date"].dt.quarter, df["date"].dt.dayofyear

# Acumulat per any (els buits sumen 0 NOMÉS aquí, perquè la corba és un mínim conegut).
df["cum_headcount_min"] = df.groupby("year")["headcount"].transform(lambda s: s.fillna(0).cumsum())

# Rànquing d'empreses per total conegut (1 = la que més): ordena el desplegable del dashboard.
company_total = df.groupby("company")["headcount"].sum()
df["company_rank"] = df["company"].map(company_total.rank(ascending=False, method="min")).astype(int)

# ══════════════════════════════════════════════════════════════════════════════════════════
# P4. NORMALITZACIÓ A DADES RELATIVES
# Problema: una xifra absoluta no diu si un esdeveniment és gran o petit dins del seu any.
# Es calcula el pes (%) de cada esdeveniment sobre el total CONEGUT de l'any.
# (No hi ha denominador de plantilla total del sector, per això es relativitza al total conegut.)
# ══════════════════════════════════════════════════════════════════════════════════════════
year_total = df.groupby("year")["headcount"].transform("sum")
df["pct_of_year_known"] = (df["headcount"] / year_total * 100).round(2)

# ══════════════════════════════════════════════════════════════════════════════════════════
# P5. AGRUPACIÓ I VALORS ATÍPICS
# Problemes: ~100 empreses amb 1-2 esdeveniments fan il·legible un gràfic; pocs esdeveniments grans
# aixafen l'escala. Agrupem en top-N + "Altres empreses" i marquem atípics amb la regla IQR (Tukey).
# ATÈS que no s'eliminen (són reals), només es marquen per poder-los ressaltar/filtrar.
# ══════════════════════════════════════════════════════════════════════════════════════════
top = set(company_total.nlargest(TOP_N).index)
df["company_group"] = df["company"].where(df["company"].isin(top), "Altres empreses")

q1, q3 = df["headcount"].quantile([0.25, 0.75])
iqr_limit = q3 + 1.5 * (q3 - q1)
df["is_outlier"] = df["headcount"] > iqr_limit

# ══════════════════════════════════════════════════════════════════════════════════════════
# P6. AUDITORIA: POSSIBLES DOBLES RECOMPTES
# Problema: la fila de la matriu pot incloure les dels seus estudis el mateix dia (p. ex. EA i Respawn).
# Es MARCA, no s'esborra: no es pot saber amb certesa i la decisió es deixa a l'usuari del dashboard.
# ══════════════════════════════════════════════════════════════════════════════════════════
several = df.groupby(["company", "date"])["studio"].transform("nunique") > 1
df["possible_double_count"] = several & (df["studio"] == df["company"])

# ══════════════════════════════════════════════════════════════════════════════════════════
# SORTIDES
# ══════════════════════════════════════════════════════════════════════════════════════════
cols = ["date", "year", "month", "quarter", "day_of_year", "studio", "company", "company_group",
        "company_rank", "parent", "type", "headcount", "headcount_status", "pct_of_year_known",
        "cum_headcount_min", "is_outlier", "possible_double_count", "source_file"]
df[cols].to_csv(CLEAN_DIR / "layoffs_clean.csv", index=False, date_format="%Y-%m-%d")

yearly = (df.groupby("year")
            .agg(events=("studio", "size"), known_total=("headcount", "sum"),
                 events_without_figure=("headcount", lambda s: int(s.isna().sum())),
                 first_event=("date", "min"), last_event=("date", "max"))
            .reset_index())
yearly["share_without_figure"] = (yearly["events_without_figure"] / yearly["events"]).round(3)
# Aproximació: es compta fins a l'últim esdeveniment, no fins a la data real de tall de la font.
yearly["days_until_last_event"] = (yearly["last_event"] - pd.to_datetime(yearly["year"].astype(str) + "-01-01")).dt.days + 1
yearly.to_csv(CLEAN_DIR / "yearly_summary.csv", index=False, date_format="%Y-%m-%d")

# ── Informe de qualitat (surt per pantalla; útil per al PDF) ──
print(f"\nFitxers llegits: {[f.name for f in files]}")
print(f"Registres: {n_loaded} carregats -> {len(df)} nets | dates invàlides descartades: {n_bad_date}")
print(f"Columnes eliminades per buides: {dropped_cols}")
print("\nEstat de la xifra:\n" + df["headcount_status"].value_counts().to_string())
print(f"\nLímit d'atípics (IQR): {iqr_limit:.0f} | atípics marcats: {int(df['is_outlier'].sum())}")
print(f"Possibles dobles recomptes marcats: {int(df['possible_double_count'].sum())}")
print("\n" + yearly.to_string(index=False))