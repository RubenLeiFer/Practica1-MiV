# Desmuntant la mentida visual: acomiadaments a la indústria del videojoc

Pràctica 1 de *Modelització i Visualització de Dades* (Universitat Rovira i Virgili, Grau en Enginyeria Informàtica).
Autor: Ruben Leiva Fernandez

## De què va

El febrer de 2026, Luminate Intelligence va publicar un gràfic amb els acomiadaments de la indústria del videojoc per any (2022-2026). Semblava que el 2026 baixaven de cop, però aquell any només tenia 29 dies de dades i es comparava amb anys complets.

Aquest projecte fa dues coses:

1. **Neteja les dades** de la font original.
2. **Les mostra en un panell interactiu (dashboard)** amb una columna per cada mes, de manera que totes les columnes cobreixen el mateix temps i es poden comparar de debò.

## D'on surten les dades

Del tracker col·laboratiu de Farhan Noor (@dekaf): https://publish.obsidian.md/vg-layoffs/

He fet servir els CSV (taules de dades) que ofereix per cada any, de 2022 a 2025. Cada fila és **un esdeveniment d'acomiadament** (un estudi, una data i el nombre de persones afectades), no una persona.

**Limitacions que cal tenir presents:**

- Prop del 30 % dels esdeveniments no tenen xifra. No els tracto com a 0, perquè això voldria dir que no hi va haver acomiadaments, i el que passa és que no ho sabem.
- A la web del tracker es distingeix entre xifres exactes i aproximades, però el CSV no ho conserva.
- És un recompte col·laboratiu de casos públics, així que la xifra real és probablement més alta.
- Les dades arriben fins a l'últim esdeveniment registrat, i l'últim mes pot estar incomplet.

## Què hi ha al repositori

```
├── data/
│   ├── raw/              Els CSV descarregats, sense modificar
│   └── clean/            Les dades ja netes (les crea preprocess.py)
├── preprocess.py         Neteja i prepara les dades
├── app.py                El dashboard interactiu
├── requirements.txt      Llista de llibreries necessàries
└── README.md             Aquest fitxer
```

## Com executar-ho

Necessites **Python 3.12** i l'eina **uv** (o, si prefereixes, `pip`). Totes les ordres s'executen des de la carpeta principal del projecte.

**1. Prepara l'entorn** (només la primera vegada). Crea un espai aïllat per al projecte i hi instal·la les llibreries:

```
uv venv --python 3.12
uv pip install -r requirements.txt
```

**2. Neteja les dades.** Llegeix els CSV de `data/raw/` i crea els fitxers nets a `data/clean/`:

```
.venv\Scripts\python.exe preprocess.py
```

**3. Obre el dashboard:**

```
.venv\Scripts\streamlit.exe run app.py
```

S'obrirà sol al navegador (normalment a http://localhost:8501). Per aturar-lo, tanca el terminal o prem `Ctrl+C`.

*A Mac o Linux, substitueix `.venv\Scripts\python.exe` per `.venv/bin/python` i `.venv\Scripts\streamlit.exe` per `.venv/bin/streamlit`.*

## Què fa la neteja de dades (`preprocess.py`)

Les dades originals no estan pensades per dibuixar-les directament. El programa fa això:

1. **Posa ordre al format.** Treu espais sobrants, descarta columnes buides i converteix dates i xifres en un format que l'ordinador pugui calcular. Les xifres que falten es queden com a *desconegudes*, mai com a 0.
2. **Unifica els noms.** La mateixa empresa apareixia escrita de maneres diferents (per exemple, «PlayTika» i «Playtika») i hi havia alguna errada d'escriptura. Si no s'ajusten, el filtre per estudi les tractaria com a entitats diferents.
3. **Marca els casos extrems.** Alguns esdeveniments són molt més grans que la resta. No s'eliminen, perquè són reals, només es marquen.

El programa també crea altres columnes de suport (pes de cada esdeveniment sobre el total de l'any, possibles dobles recomptes...) que el dashboard actual no fa servir.

**Correcció manual:** una data tenia l'any escrit malament a l'origen (0125). L'he corregit a mà al CSV original a 2024.

## Com es fa servir el dashboard

**Al menú de l'esquerra:**

- **Representació:** canvia entre una columna per cada mes (evolució en el temps) i una línia per cada any, alineades gener amb gener, febrer amb febrer… (per comparar anys).
- **Anys:** tria el rang d'anys que vols veure.
- **Estudis:** tria un o diversos estudis, ordenats pels que han acomiadat més gent. Si no en tries cap, es mostren tots.

**Al gràfic:** passa el cursor per sobre d'un mes per veure el total conegut, el nombre d'esdeveniments, quants no tenen xifra i l'estudi amb més acomiadats d'aquell mes.

**Com llegir-lo:**

- Cada columna és **un mes**. Els anys s'agrupen amb un fons alternat i l'any s'indica sota l'eix.
- Una **columna ratllada** vol dir que aquell mes té esdeveniments sense xifra, de manera que el total real és igual o superior al que es veu.
- La **zona grisa «Sense dades»** són mesos que la font encara no cobreix. No són un 0.

## Glossari ràpid

- **CSV:** fitxer de text que guarda una taula, una fila per línia. S'obre amb Excel.
- **Entorn virtual (`.venv`):** carpeta amb una còpia de Python i les llibreries del projecte, perquè no interfereixin amb la resta de l'ordinador.
- **pandas:** llibreria de Python per treballar amb taules de dades.
- **Plotly:** llibreria que dibuixa els gràfics interactius.
- **Streamlit:** eina que converteix un programa de Python en una pàgina web.
- **Tooltip:** quadre d'informació que apareix en passar el cursor per sobre d'un element.

## Crèdits

- Dades: tracker de Farhan Noor (@dekaf).
- Gràfic analitzat: «Global Video Game Layoffs», Luminate Intelligence, article «Gaming Industry Off to a Shaky 2026» (11/02/2026).
- Llibreries: pandas, NumPy, Plotly i Streamlit.