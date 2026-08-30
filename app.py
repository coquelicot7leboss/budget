import streamlit as st
import sqlite3
import html
import base64
from pathlib import Path
from datetime import date
import pandas as pd
import altair as alt

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
DB_PATH = "budget.db"

CATEGORIES_REVENU = ["Salaire", "Autre revenu"]
CATEGORIES_DEPENSE = [
    "Logement", "Assurances", "Abonnements", "Sport",
    "Courses", "Restaurants", "Loisirs", "Transport", "Autre",
]

MOIS_FR = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]

COULEUR_POSITIF = "#2F6F4F"
COULEUR_NEGATIF = "#B23A48"

st.set_page_config(page_title="Budget List", layout="wide")

# ----------------------------------------------------------------------
# Habillage visuel (CSS)
# ----------------------------------------------------------------------
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@500&display=swap');

html, body, [class*="css"]  {
    font-family: 'Inter', sans-serif;
}

.block-container {
    max-width: 980px;
    padding-top: 2.2rem;
    margin: 0 auto;
}

h1, h2, h3 {
    font-family: 'Fraunces', serif;
    letter-spacing: -0.01em;
}

.eyebrow {
    font-family: 'Inter', sans-serif;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    font-size: 0.72rem;
    color: #6B7566;
    font-weight: 600;
    margin-bottom: 0.15rem;
}

.ledger-rule-gold {
    border: none;
    border-top: 2px solid #C9A227;
    margin: 0.35rem 0 1.3rem 0;
    width: 56px;
}

[data-testid="stMetric"] {
    background-color: #ECEBE3;
    border: 1px solid #DEDCCE;
    border-radius: 10px;
    padding: 0.9rem 1rem 0.7rem 1rem;
    overflow: visible;
}

[data-testid="stMetricValue"] {
    font-family: 'Fraunces', serif;
    font-weight: 600;
    color: #1C2321;
    font-size: clamp(1.15rem, 2.1vw, 1.8rem) !important;
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: clip !important;
    word-break: break-word;
    line-height: 1.2;
}

[data-testid="stMetricLabel"] {
    font-family: 'Inter', sans-serif;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-size: 0.7rem;
    color: #6B7566;
}

.ledger-row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    padding: 0.4rem 0.1rem;
    border-bottom: 1px dashed #DEDCCE;
    font-size: 0.95rem;
}

.ledger-nom {
    color: #1C2321;
}

.ledger-tag {
    font-size: 0.66rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #8B9186;
    margin-left: 0.45rem;
}

.ledger-montant {
    font-family: 'IBM Plex Mono', monospace;
    font-weight: 500;
    white-space: nowrap;
}

.montant-positif { color: #2F6F4F; }
.montant-negatif { color: #B23A48; }

section[data-testid="stSidebar"] {
    background-color: #ECEBE3;
    border-right: 1px solid #DEDCCE;
}

.st-key-bouton_accueil {
    width: 100% !important;
}
.st-key-bouton_accueil > div {
    width: 100% !important;
}
.st-key-bouton_accueil div[data-testid="stButton"] {
    width: 100% !important;
}
.st-key-bouton_accueil button {
    width: 100% !important;
    aspect-ratio: 1195 / 1303;
    height: auto !important;
    min-width: 0 !important;
    margin: 0 auto 0.6rem auto;
    padding: 0;
    display: block;
    background-image: var(--image-bouton-accueil);
    background-size: contain;
    background-repeat: no-repeat;
    background-position: center;
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
}
.st-key-bouton_accueil button:hover {
    background-color: transparent !important;
    border: none !important;
    filter: brightness(1.08);
}
.st-key-bouton_accueil button p {
    display: none;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def appliquer_fond(chemin_image):
    """Affiche l'image comme fond d'écran, avec un voile clair par-dessus
    pour que le texte reste toujours lisible."""
    fichier = Path(chemin_image)
    if not fichier.exists():
        return
    extension = fichier.suffix.lstrip(".").lower()
    data_b64 = base64.b64encode(fichier.read_bytes()).decode()
    css_fond = f"""
    <style>
    [data-testid="stAppViewContainer"] {{
        background-image:
            linear-gradient(rgba(247, 247, 242, 0.90), rgba(247, 247, 242, 0.90)),
            url("data:image/{extension};base64,{data_b64}");
        background-size: cover;
        background-position: center top;
        background-attachment: fixed;
    }}
    [data-testid="stHeader"] {{
        background-color: rgba(0, 0, 0, 0);
    }}
    </style>
    """
    st.markdown(css_fond, unsafe_allow_html=True)


appliquer_fond("fond.png")


def fmt_euro(valeur):
    texte = f"{valeur:,.2f}"
    texte = texte.replace(",", " ").replace(".", ",")
    return f"{texte} €"


def entete(eyebrow_texte, titre):
    st.markdown(f'<div class="eyebrow">{eyebrow_texte}</div>', unsafe_allow_html=True)
    st.title(titre)
    st.markdown('<hr class="ledger-rule-gold">', unsafe_allow_html=True)


def ligne_ledger(nom, montant, positif, tag=""):
    classe = "montant-positif" if positif else "montant-negatif"
    signe = "+" if positif else "−"
    nom_echap = html.escape(nom)
    tag_html = f'<span class="ledger-tag">{html.escape(tag)}</span>' if tag else ""
    st.markdown(
        f'<div class="ledger-row"><span class="ledger-nom">{nom_echap}{tag_html}</span>'
        f'<span class="ledger-montant {classe}">{signe}{fmt_euro(montant)}</span></div>',
        unsafe_allow_html=True,
    )


# ----------------------------------------------------------------------
# Base de données
# ----------------------------------------------------------------------
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            solde_initial REAL NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS recurrents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            montant REAL NOT NULL,
            type TEXT NOT NULL,
            categorie TEXT NOT NULL,
            frequence TEXT NOT NULL,
            mois_debut TEXT NOT NULL,
            mois_fin TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ponctuels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            montant REAL NOT NULL,
            type TEXT NOT NULL,
            categorie TEXT NOT NULL,
            mois TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def get_solde_initial():
    conn = get_connection()
    row = conn.execute("SELECT solde_initial FROM settings WHERE id = 1").fetchone()
    conn.close()
    return row["solde_initial"] if row else None


def set_solde_initial(montant):
    conn = get_connection()
    conn.execute("""
        INSERT INTO settings (id, solde_initial) VALUES (1, ?)
        ON CONFLICT(id) DO UPDATE SET solde_initial = excluded.solde_initial
    """, (montant,))
    conn.commit()
    conn.close()


def get_recurrents():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM recurrents ORDER BY type, categorie, nom").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_recurrent(nom, montant, type_, categorie, frequence, mois_debut, mois_fin=None):
    conn = get_connection()
    conn.execute("""
        INSERT INTO recurrents (nom, montant, type, categorie, frequence, mois_debut, mois_fin)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (nom, montant, type_, categorie, frequence, mois_debut, mois_fin))
    conn.commit()
    conn.close()


def update_recurrent_mois_fin(rec_id, mois_fin):
    conn = get_connection()
    conn.execute("UPDATE recurrents SET mois_fin = ? WHERE id = ?", (mois_fin, rec_id))
    conn.commit()
    conn.close()


def delete_recurrent(rec_id):
    conn = get_connection()
    conn.execute("DELETE FROM recurrents WHERE id = ?", (rec_id,))
    conn.commit()
    conn.close()


def get_ponctuels(mois=None):
    conn = get_connection()
    if mois:
        rows = conn.execute("SELECT * FROM ponctuels WHERE mois = ? ORDER BY nom", (mois,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM ponctuels ORDER BY mois").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_ponctuel(nom, montant, type_, categorie, mois):
    conn = get_connection()
    conn.execute("""
        INSERT INTO ponctuels (nom, montant, type, categorie, mois)
        VALUES (?, ?, ?, ?, ?)
    """, (nom, montant, type_, categorie, mois))
    conn.commit()
    conn.close()


def delete_ponctuel(pid):
    conn = get_connection()
    conn.execute("DELETE FROM ponctuels WHERE id = ?", (pid,))
    conn.commit()
    conn.close()


# ----------------------------------------------------------------------
# Utilitaires de dates / mois
# ----------------------------------------------------------------------
def mois_du_jour():
    today = date.today()
    return f"{today.year:04d}-{today.month:02d}"


def ajouter_mois(mois_str, n):
    annee, mois = map(int, mois_str.split("-"))
    total = (mois - 1) + n
    nouvelle_annee = annee + total // 12
    nouveau_mois = total % 12 + 1
    return f"{nouvelle_annee:04d}-{nouveau_mois:02d}"


def diff_mois(mois_a, mois_b):
    """Nombre de mois entre mois_a et mois_b (mois_b - mois_a)."""
    aa, am = map(int, mois_a.split("-"))
    ba, bm = map(int, mois_b.split("-"))
    return (ba - aa) * 12 + (bm - am)


def libelle_mois(mois_str):
    annee, mois = map(int, mois_str.split("-"))
    return f"{MOIS_FR[mois - 1].capitalize()} {annee}"


def libelle_mois_court(mois_str):
    annee, mois = map(int, mois_str.split("-"))
    return f"{MOIS_FR[mois - 1][:3].capitalize()} {str(annee)[2:]}"


def options_mois(n=60, depart=None):
    depart = depart or mois_du_jour()
    return [ajouter_mois(depart, i) for i in range(n)]


# ----------------------------------------------------------------------
# Moteur de calcul
# ----------------------------------------------------------------------
def recurrent_actif(rec, mois):
    if mois < rec["mois_debut"]:
        return False
    if rec["mois_fin"] and mois > rec["mois_fin"]:
        return False
    ecart = diff_mois(rec["mois_debut"], mois)
    if rec["frequence"] == "mensuel":
        return True
    if rec["frequence"] == "trimestriel":
        return ecart % 3 == 0
    if rec["frequence"] == "annuel":
        return ecart % 12 == 0
    return False


def calculer_projection(nb_mois):
    solde_initial = get_solde_initial() or 0.0
    recurrents = get_recurrents()
    depart = mois_du_jour()
    mois_liste = options_mois(nb_mois, depart)

    solde = solde_initial
    resultats = []

    for mois in mois_liste:
        rec_actifs = [r for r in recurrents if recurrent_actif(r, mois)]
        rev_recurrents = [r for r in rec_actifs if r["type"] == "revenu"]
        dep_recurrentes = [r for r in rec_actifs if r["type"] == "depense"]

        ponctuels_mois = get_ponctuels(mois)
        rev_ponctuels = [p for p in ponctuels_mois if p["type"] == "revenu"]
        dep_ponctuelles = [p for p in ponctuels_mois if p["type"] == "depense"]

        total_revenus = sum(r["montant"] for r in rev_recurrents) + sum(p["montant"] for p in rev_ponctuels)
        total_depenses = sum(r["montant"] for r in dep_recurrentes) + sum(p["montant"] for p in dep_ponctuelles)

        solde_debut = solde
        solde_fin = solde_debut + total_revenus - total_depenses

        resultats.append({
            "mois": mois,
            "solde_debut": solde_debut,
            "revenus_recurrents": rev_recurrents,
            "depenses_recurrentes": dep_recurrentes,
            "revenus_ponctuels": rev_ponctuels,
            "depenses_ponctuelles": dep_ponctuelles,
            "total_revenus": total_revenus,
            "total_depenses": total_depenses,
            "solde_fin": solde_fin,
        })

        solde = solde_fin

    return resultats


# ----------------------------------------------------------------------
# Initialisation
# ----------------------------------------------------------------------
init_db()

if get_solde_initial() is None:
    st.markdown('<div class="eyebrow">Budget List</div>', unsafe_allow_html=True)
    st.title("Bienvenue dans ton registre")
    st.markdown('<hr class="ledger-rule-gold">', unsafe_allow_html=True)
    st.write("Avant de commencer, indique le montant d'argent que tu as actuellement.")
    with st.form("form_solde_initial"):
        montant = st.number_input("Montant actuel (€)", min_value=0.0, step=50.0, format="%.2f")
        valide = st.form_submit_button("Valider")
        if valide:
            set_solde_initial(montant)
            st.rerun()
    st.stop()


# ----------------------------------------------------------------------
# Navigation
# ----------------------------------------------------------------------
icone_accueil = Path("home_icon.png")
if icone_accueil.exists():
    icone_b64 = base64.b64encode(icone_accueil.read_bytes()).decode()
    st.markdown(
        f'<style>:root {{ --image-bouton-accueil: url("data:image/png;base64,{icone_b64}"); }}</style>',
        unsafe_allow_html=True,
    )

with st.sidebar.container(key="bouton_accueil"):
    if st.button(" ", key="btn_accueil_icone"):
        st.session_state["nav_radio"] = "🏠 Accueil"
        st.rerun()

st.sidebar.markdown('<div class="eyebrow">100.000 euros c\'est bien, mais 120.000 c\'est mieux !</div>', unsafe_allow_html=True)
st.sidebar.markdown('<hr class="ledger-rule-gold">', unsafe_allow_html=True)
page = st.sidebar.radio("Navigation", ["🏠 Accueil", "📅 Mois", "🔁 Récurrents"], label_visibility="collapsed", key="nav_radio")

st.sidebar.divider()
with st.sidebar.expander("⚙️ Modifier mon solde actuel"):
    nouveau_solde = st.number_input(
        "Nouveau solde", value=float(get_solde_initial()), step=50.0, format="%.2f", key="maj_solde"
    )
    if st.button("Mettre à jour le solde"):
        set_solde_initial(nouveau_solde)
        st.rerun()


# ----------------------------------------------------------------------
# Formulaire d'ajout d'un élément (revenu / dépense, récurrent / ponctuel)
# ----------------------------------------------------------------------
def formulaire_ajout(mois_par_defaut=None, key_suffix=""):
    st.subheader("Ajouter un élément")

    col1, col2 = st.columns(2)
    with col1:
        type_ = st.radio(
            "Type", ["revenu", "depense"],
            format_func=lambda x: "Revenu" if x == "revenu" else "Dépense",
            key=f"type_{key_suffix}",
        )
    with col2:
        nature = st.radio(
            "Nature", ["recurrent", "ponctuel"],
            format_func=lambda x: "Récurrent" if x == "recurrent" else "Ponctuel",
            key=f"nature_{key_suffix}",
        )

    categories = CATEGORIES_REVENU if type_ == "revenu" else CATEGORIES_DEPENSE

    with st.form(f"form_ajout_{key_suffix}"):
        nom = st.text_input("Nom")
        categorie = st.selectbox("Catégorie", categories)
        montant = st.number_input("Montant (€, toujours positif)", min_value=0.0, step=10.0, format="%.2f")

        mois_dispo = options_mois(60)
        labels_mois = [libelle_mois(m) for m in mois_dispo]
        idx_defaut = mois_dispo.index(mois_par_defaut) if mois_par_defaut in mois_dispo else 0

        if nature == "recurrent":
            frequence = st.selectbox("Fréquence", ["mensuel", "trimestriel", "annuel"])
            mois_debut_label = st.selectbox("À partir de quel mois", labels_mois, index=idx_defaut)
            mois_debut = mois_dispo[labels_mois.index(mois_debut_label)]
        else:
            mois_label = st.selectbox("Mois concerné", labels_mois, index=idx_defaut)
            mois_ponctuel = mois_dispo[labels_mois.index(mois_label)]

        valide = st.form_submit_button("Ajouter")

        if valide:
            if not nom.strip():
                st.error("Merci de renseigner un nom.")
            elif montant <= 0:
                st.error("Le montant doit être supérieur à 0.")
            else:
                if nature == "recurrent":
                    add_recurrent(nom.strip(), montant, type_, categorie, frequence, mois_debut)
                else:
                    add_ponctuel(nom.strip(), montant, type_, categorie, mois_ponctuel)
                st.success("Élément ajouté !")
                st.rerun()


# ----------------------------------------------------------------------
# Page Accueil
# ----------------------------------------------------------------------
if page == "🏠 Accueil":
    entete("Budget List · Vue d'ensemble", "Ton registre")

    solde_actuel = get_solde_initial()
    projection = calculer_projection(48)

    st.metric("Solde actuel", fmt_euro(solde_actuel))

    col1, col2, col3 = st.columns(3)
    col1.metric("Dans 1 mois", fmt_euro(projection[0]["solde_fin"]))
    col2.metric("Dans 12 mois", fmt_euro(projection[11]["solde_fin"]))
    col3.metric("Dans 24 mois", fmt_euro(projection[23]["solde_fin"]))
    st.metric("Dans 48 mois", fmt_euro(projection[47]["solde_fin"]))

    st.write("")
    st.markdown('<div class="eyebrow">Évolution du solde</div>', unsafe_allow_html=True)

    df = pd.DataFrame({
        "mois": [libelle_mois_court(p["mois"]) for p in projection],
        "ordre": range(len(projection)),
        "solde": [p["solde_fin"] for p in projection],
    })
    labels_pour_axe = df["mois"].tolist()

    chart = alt.Chart(df).mark_area(
        line={"color": COULEUR_POSITIF, "strokeWidth": 2},
        color=alt.Gradient(
            gradient="linear",
            stops=[
                alt.GradientStop(color=COULEUR_POSITIF, offset=0),
                alt.GradientStop(color="#F7F7F2", offset=1),
            ],
            x1=1, x2=1, y1=1, y2=0,
        ),
        opacity=0.55,
    ).encode(
        x=alt.X(
            "ordre:Q",
            axis=alt.Axis(
                values=list(range(0, len(df), 4)),
                labelExpr=f"{labels_pour_axe}[datum.value]",
                title=None, labelFontSize=10, labelAngle=0,
            ),
        ),
        y=alt.Y("solde:Q", title=None, axis=alt.Axis(format="~s")),
        tooltip=[alt.Tooltip("mois:N", title="Mois"), alt.Tooltip("solde:Q", title="Solde", format=",.0f")],
    ).properties(height=300)

    st.altair_chart(chart, use_container_width=True)


# ----------------------------------------------------------------------
# Page Mois
# ----------------------------------------------------------------------
elif page == "📅 Mois":
    entete("Budget List · Détail", "Projection mensuelle")

    horizon = st.selectbox("Horizon de projection", [12, 24, 48], index=0)
    projection = calculer_projection(horizon)

    tableau = pd.DataFrame([
        {
            "Mois": libelle_mois(p["mois"]),
            "Solde début": p["solde_debut"],
            "Revenus": p["total_revenus"],
            "Dépenses": p["total_depenses"],
            "Solde fin": p["solde_fin"],
        }
        for p in projection
    ])
    st.dataframe(tableau, use_container_width=True, hide_index=True)

    st.write("")
    st.markdown('<div class="eyebrow">Détail d\'un mois</div>', unsafe_allow_html=True)

    labels_mois = [libelle_mois(p["mois"]) for p in projection]
    choix_label = st.selectbox("Choisir un mois", labels_mois)
    mois_choisi = projection[labels_mois.index(choix_label)]

    st.metric("Solde de début", fmt_euro(mois_choisi["solde_debut"]))

    st.markdown("**Revenus**")
    for r in mois_choisi["revenus_recurrents"]:
        ligne_ledger(r["nom"], r["montant"], True, "récurrent")
    for p in mois_choisi["revenus_ponctuels"]:
        ligne_ledger(p["nom"], p["montant"], True, "ponctuel")
    if not mois_choisi["revenus_recurrents"] and not mois_choisi["revenus_ponctuels"]:
        st.caption("Aucun revenu ce mois-ci.")

    st.markdown("**Dépenses récurrentes**")
    for r in mois_choisi["depenses_recurrentes"]:
        ligne_ledger(r["nom"], r["montant"], False, r["frequence"])
    if not mois_choisi["depenses_recurrentes"]:
        st.caption("Aucune dépense récurrente ce mois-ci.")

    st.markdown("**Dépenses ponctuelles**")
    if mois_choisi["depenses_ponctuelles"]:
        for p in mois_choisi["depenses_ponctuelles"]:
            colA, colB = st.columns([5, 1])
            with colA:
                ligne_ledger(p["nom"], p["montant"], False)
            if colB.button("Suppr.", key=f"del_ponct_{p['id']}"):
                delete_ponctuel(p["id"])
                st.rerun()
    else:
        st.caption("Aucune dépense ponctuelle ce mois-ci.")

    st.metric("Solde de fin", fmt_euro(mois_choisi["solde_fin"]))

    st.write("")
    formulaire_ajout(mois_par_defaut=mois_choisi["mois"], key_suffix="mois")


# ----------------------------------------------------------------------
# Page Récurrents
# ----------------------------------------------------------------------
elif page == "🔁 Récurrents":
    entete("Budget List · Automatique", "Éléments récurrents")

    recurrents = get_recurrents()
    aujourd_hui = mois_du_jour()
    actifs = [r for r in recurrents if r["mois_fin"] is None or r["mois_fin"] >= aujourd_hui]

    if not actifs:
        st.caption("Aucun élément récurrent pour le moment.")

    for r in actifs:
        pastille = "🟢" if r["type"] == "revenu" else "🔴"
        signe = "+" if r["type"] == "revenu" else "−"
        with st.expander(f"{pastille}  {r['nom']} — {signe}{fmt_euro(r['montant'])} · {r['frequence']}"):
            st.write(f"Catégorie : {r['categorie']}")
            st.write(f"Depuis : {libelle_mois(r['mois_debut'])}")
            if r["mois_fin"]:
                st.write(f"Jusqu'à : {libelle_mois(r['mois_fin'])}")

            mois_dispo = options_mois(60)
            labels = [libelle_mois(m) for m in mois_dispo]

            st.markdown("**Modifier le montant à partir d'une date**")
            colA, colB, colC = st.columns([2, 2, 1])
            nouveau_montant = colA.number_input(
                "Nouveau montant", min_value=0.0, step=10.0, format="%.2f", key=f"maj_montant_{r['id']}"
            )
            mois_effet_label = colB.selectbox("À partir de", labels, key=f"maj_mois_{r['id']}")
            mois_effet = mois_dispo[labels.index(mois_effet_label)]

            if colC.button("Appliquer", key=f"maj_valider_{r['id']}"):
                mois_fin_ancien = ajouter_mois(mois_effet, -1)
                update_recurrent_mois_fin(r["id"], mois_fin_ancien)
                add_recurrent(r["nom"], nouveau_montant, r["type"], r["categorie"], r["frequence"], mois_effet)
                st.success("Modification enregistrée.")
                st.rerun()

            st.markdown("**Arrêter cet élément**")
            colD, colE = st.columns([3, 1])
            mois_arret_label = colD.selectbox("À partir de", labels, key=f"arret_mois_{r['id']}")
            mois_arret = mois_dispo[labels.index(mois_arret_label)]
            if colE.button("Arrêter", key=f"arret_valider_{r['id']}"):
                mois_fin = ajouter_mois(mois_arret, -1)
                update_recurrent_mois_fin(r["id"], mois_fin)
                st.success("Élément arrêté à partir de la date choisie.")
                st.rerun()

            if st.button("Supprimer complètement", key=f"suppr_{r['id']}"):
                delete_recurrent(r["id"])
                st.success("Élément supprimé.")
                st.rerun()

    st.write("")
    formulaire_ajout(key_suffix="recurrents")
