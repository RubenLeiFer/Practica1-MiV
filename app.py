"""
app.py — Fase 3: dashboard interactiu (Streamlit + Plotly)
Pràctica 1 (Modelització i Visualització de Dades, URV)

Entrada : data/clean/layoffs_clean.csv  (la genera preprocess.py)
Execució: streamlit run app.py

Interaccions implementades (tipologies del curs):
  1. Abstraure/Elaborar -> tooltip en passar el cursor per sobre de cada mes
  2. Filtrar            -> estudis i rang d'anys
  3. Codificar          -> alternar entre columnes cronològiques i línies per any
"""
import calendar
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.colors import sample_colorscale

DATA = Path("data/clean/layoffs_clean.csv")
MONTHS = ["Gener", "Febrer", "Març", "Abril", "Maig", "Juny",
          "Juliol", "Agost", "Setembre", "Octubre", "Novembre", "Desembre"]
MONTHS_SHORT = ["Gen", "Feb", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Oct", "Nov", "Des"]
MONTH_INITIALS = ["G", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"]
BLUE = "#1f6f8b"

st.set_page_config(page_title="Acomiadaments al videojoc", layout="wide")


def fmt(n) -> str:
    """Format català de milers: 14.441"""
    return f"{int(n):,}".replace(",", ".")


# ── Càrrega ─────────────────────────────────────────────────────────────────────────────
# Només es llegeixen les tres columnes que fa servir el dashboard: Studio, Date i Headcount.
@st.cache_data
def load_data() -> pd.DataFrame:
    d = pd.read_csv(DATA, parse_dates=["date"], usecols=["date", "studio", "headcount"])
    d["year"], d["month"] = d["date"].dt.year, d["date"].dt.month
    return d


if not DATA.exists():
    st.error(f"No es troba {DATA}. Executa primer: python preprocess.py")
    st.stop()

df = load_data()
last_date = df["date"].max()   # cobertura de les dades: l'últim esdeveniment registrat


# ── Controls (barra lateral) ──────────────────────────────────────────────────────────────
st.sidebar.header("Controls")

# CODIFICAR: el mateix conjunt de dades amb dues representacions.
view = st.sidebar.radio(
    "Representació",
    ["Cronològica (una columna per mes)", "Anys superposats (línies)"],
    help="La cronològica mostra l'evolució al llarg del temps. La superposada alinea "
         "gener amb gener, febrer amb febrer… per comparar anys i veure si hi ha estacionalitat.",
)

# FILTRAR (1/2): rang d'anys.
years_all = sorted(df["year"].unique())
if len(years_all) > 1:
    y0, y1 = st.sidebar.select_slider("Anys", options=years_all, value=(years_all[0], years_all[-1]))
else:
    y0 = y1 = years_all[0]

# FILTRAR (2/2): estudis, ordenats per impacte (no alfabèticament) per trobar els grans de seguida.
totals = df.groupby("studio")["headcount"].sum()
order = sorted(totals.index, key=lambda s: (-totals[s], s))
studios = st.sidebar.multiselect(
    "Estudis",
    options=order,
    format_func=lambda s: f"{s} ({fmt(totals[s])})" if totals[s] > 0 else f"{s} (sense xifra)",
    placeholder="Tots els estudis",
    help="Ordenats pel total d'acomiadats conegut. Si no en selecciones cap, es mostren tots.",
)

dff = df[df["year"].between(y0, y1)]
if studios:
    dff = dff[dff["studio"].isin(studios)]


# ── Agregació mensual ──────────────────────────────────────────────────────────────────────
def monthly_table(d: pd.DataFrame, years: list, last: pd.Timestamp) -> pd.DataFrame:
    """Una fila per cada mes de cada any, amb o sense esdeveniments."""
    grid = pd.DataFrame([(y, m) for y in years for m in range(1, 13)], columns=["year", "month"])
    agg = (d.groupby(["year", "month"])
             .agg(known=("headcount", "sum"), events=("studio", "size"),
                  no_figure=("headcount", lambda s: int(s.isna().sum())))
             .reset_index())
    # estudi amb més acomiadats cada mes (sumant els seus esdeveniments del mes)
    per_studio = (d.groupby(["year", "month", "studio"], as_index=False)["headcount"]
                    .sum(min_count=1).dropna())
    top = (per_studio.sort_values("headcount", ascending=False)
                     .drop_duplicates(["year", "month"])
                     .rename(columns={"studio": "top_studio", "headcount": "top_n"}))
    t = grid.merge(agg, how="left", on=["year", "month"]).merge(top, how="left", on=["year", "month"])
    t[["known", "events", "no_figure"]] = t[["known", "events", "no_figure"]].fillna(0).astype(int)

    # Cobertura: un mes posterior a l'últim esdeveniment és "sense dades" (NO és un 0).
    key, last_key = t["year"] * 100 + t["month"], last.year * 100 + last.month
    last_month_incomplete = last.day < calendar.monthrange(last.year, last.month)[1]
    t["status"] = np.where(key > last_key, "sense_dades",
                           np.where((key == last_key) & last_month_incomplete, "parcial", "ok"))
    t["label"] = t["month"].map(lambda m: MONTHS[m - 1]) + " " + t["year"].astype(str)
    t["hover"] = t.apply(hover_text, axis=1)
    return t


# ABSTRAURE/ELABORAR: contingut del tooltip (més detall a petició del cursor).
def hover_text(r) -> str:
    if r["status"] == "sense_dades":
        return f"<b>{r['label']}</b><br>Sense dades: la font encara no cobreix aquest mes"
    txt = f"<b>{r['label']}</b><br>Persones acomiadades (xifres conegudes): <b>{fmt(r['known'])}</b>"
    txt += f"<br>Esdeveniments: {r['events']}"
    if r["no_figure"]:
        txt += f" (sense xifra: {r['no_figure']})"
    if pd.notna(r["top_studio"]):
        txt += f"<br>Estudi amb més acomiadats: {r['top_studio']} ({fmt(r['top_n'])})"
    if r["no_figure"]:
        txt += "<br><i>El total real és igual o superior</i>"
    if r["status"] == "parcial":
        txt += "<br><i>Mes possiblement incomplet</i>"
    return txt


# ── Figura 1: columnes cronològiques ────────────────────────────────────────────────────────
def fig_chrono(t: pd.DataFrame) -> go.Figure:
    n, x = len(t), np.arange(len(t))
    ymax = max(int(t["known"].max()), 1)
    ok = (t["status"] != "sense_dades").values
    hatched = ok & (t["no_figure"] > 0).values
    solid = ok & ~hatched

    fig = go.Figure()
    fig.add_bar(x=x[solid], y=t.loc[solid, "known"], name="Xifres conegudes",
                marker_color=BLUE, hoverinfo="skip")
    # Barres ratllades: el mes té esdeveniments sense xifra, així que el total real és superior.
    fig.add_bar(x=x[hatched], y=t.loc[hatched, "known"],
                name="Mínim conegut (el mes té esdeveniments sense xifra)",
                marker=dict(color=BLUE, pattern=dict(shape="/", fgcolor=BLUE, bgcolor="white"),
                            line=dict(color=BLUE, width=1)),
                hoverinfo="skip")
    # Capa transparent d'alçada completa: permet el tooltip fins i tot en mesos a 0.
    fig.add_bar(x=x, y=[ymax * 1.05] * n, marker_color="rgba(0,0,0,0)", showlegend=False,
                hovertext=t["hover"], hoverinfo="text")

    # Agrupació per any (Gestalt: proximitat/fons alternat) amb l'any sota l'eix.
    first_year = t["year"].min()
    for y, g in t.groupby("year"):
        i0, i1 = g.index.min() - 0.5, g.index.max() + 0.5
        if (y - first_year) % 2 == 1:
            fig.add_vrect(x0=i0, x1=i1, fillcolor="rgba(0,0,0,0.05)", line_width=0, layer="below")
        fig.add_annotation(x=(i0 + i1) / 2, y=-0.13, yref="paper", text=f"<b>{y}</b>", showarrow=False)

    # Mesos sense dades: zona grisa explícita, no barres a 0.
    nd = t.index[t["status"] == "sense_dades"]
    if len(nd):
        fig.add_vrect(x0=nd.min() - 0.5, x1=nd.max() + 0.5, fillcolor="rgba(150,150,150,0.28)",
                      line_width=0, layer="below")
        fig.add_annotation(x=(nd.min() + nd.max()) / 2, y=0.5, yref="paper", text="Sense dades",
                           textangle=-90 if len(nd) < 3 else 0, showarrow=False, font=dict(color="#555"))

    fig.update_xaxes(tickmode="array", tickvals=list(x), ticktext=[MONTH_INITIALS[m - 1] for m in t["month"]],
                     range=[-0.6, n - 0.4], showgrid=False, title_text="Mes i any", title_standoff=30)
    fig.update_yaxes(title_text="Persones acomiadades (xifres conegudes)", rangemode="tozero")
    fig.update_layout(barmode="overlay", bargap=0.2)
    return fig


# ── Figura 2: anys superposats ─────────────────────────────────────────────────────────────
def fig_overlay(t: pd.DataFrame) -> go.Figure:
    years = sorted(t["year"].unique())
    pos = [0.0 if len(years) == 1 else 0.8 * i / (len(years) - 1) for i in range(len(years))]
    colors = sample_colorscale("Viridis", pos)   # escala seqüencial: ordre dels anys i apta per a daltònics
    fig = go.Figure()
    for y, c in zip(years, colors):
        g = t[t["year"] == y]
        yv = g["known"].where(g["status"] != "sense_dades")   # NaN: la línia s'atura on no hi ha dades
        fig.add_scatter(x=g["month"], y=yv, mode="lines+markers", name=str(y),
                        line=dict(color=c, width=2.5), marker=dict(size=7),
                        hovertext=g["hover"], hoverinfo="text")
    fig.update_xaxes(tickmode="array", tickvals=list(range(1, 13)), ticktext=MONTHS_SHORT,
                     title_text="Mes", showgrid=False)
    fig.update_yaxes(title_text="Persones acomiadades (xifres conegudes)", rangemode="tozero")
    fig.update_layout(legend_title_text="Any")
    return fig


# ── Pàgina ───────────────────────────────────────────────────────────────────────────────
st.title("Acomiadaments a la indústria del videojoc, mes a mes")
st.caption("Cada columna cobreix exactament un mes, així que totes són comparables entre si. "
           "Només es compten les xifres conegudes: els mesos amb ratlles tenen esdeveniments "
           "sense xifra i el seu total real és superior.")

if dff.empty:
    st.info("Cap esdeveniment amb aquests filtres. Prova d'ampliar el rang d'anys o de treure algun estudi.")
    st.stop()

c1, c2, c3 = st.columns(3)
c1.metric("Persones acomiadades (xifres conegudes)", fmt(dff["headcount"].sum()))
c2.metric("Esdeveniments", fmt(len(dff)))
c3.metric("Esdeveniments sense xifra", fmt(dff["headcount"].isna().sum()))

table = monthly_table(dff, list(range(y0, y1 + 1)), last_date)
fig = fig_chrono(table) if view.startswith("Cronològica") else fig_overlay(table)
fig.update_layout(template="plotly_white", height=520, hovermode="closest", separators=",.",
                  margin=dict(l=70, r=20, t=50, b=90),
                  legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
st.plotly_chart(fig, width="stretch", config={"displaylogo": False})

st.caption(f"Font: tracker de Farhan Noor (exportació d'Airtable). Dades fins a l'últim esdeveniment "
           f"registrat ({last_date:%d/%m/%Y}). Les cel·les sense xifra no es compten com a 0: "
           f"es mostren com a desconegudes.")
