# pages/2_📺_Pantalla_publica.py

import streamlit as st
import time
import pandas as pd
import tournament_logic as logic
import xlsxwriter

# --- Configuration ---
ROTATION_INTERVAL_SECONDS = 60

# --- Page Configuration ---
st.set_page_config(
    page_title="Resultados en Vivo",
    page_icon="📺",
    layout="wide",
)

# --- CSS Styling (Safe Version) ---
st.markdown("""
<style>
    /* Hide Streamlit's default UI elements we don't need */
    [data-testid="stSidebar"] {
        display: none;
    }
    [data-testid="stHeader"] {
        display: none;
    }

    /* Style the main page content */
    .main .block-container {
        padding-top: 1rem;
    }
    h1, h2, h3 {
        color: #ffad42;
        font-weight: bold;
    }
    .stDataFrame {
        font-size: 1.1rem;
    }
</style>
""", unsafe_allow_html=True)


# --- Data Loading and State Initialization ---
data = logic.load_data()
categories = list(data.keys())

# Initialize session state keys only if they are missing
if 'public_view_cat_index' not in st.session_state:
    st.session_state.public_view_cat_index = 0
if 'last_rotation_time' not in st.session_state:
    st.session_state.last_rotation_time = time.time()


# --- Core Rotation Logic ---
elapsed_time = time.time() - st.session_state.last_rotation_time

if elapsed_time > ROTATION_INTERVAL_SECONDS and len(categories) > 1:
    st.session_state.public_view_cat_index = (st.session_state.public_view_cat_index + 1) % len(categories)
    st.session_state.last_rotation_time = time.time()
    elapsed_time = 0


# --- Native Streamlit Header (RELIABLE) ---
col1, col2 = st.columns([4, 1])

with col1:
    time_left = int(ROTATION_INTERVAL_SECONDS - elapsed_time)
    st.write(f"#### Cambiando categoría en: **{max(0, time_left)}s**")

with col2:
    if st.button("👑 Volver al Panel de Admin"):
        st.switch_page("1_👑_Admin.py")

st.markdown("---") # Visual separator


# --- Main Page Display ---
if not categories:
    st.title("Esperando datos del torneo...");
    st.stop()

# Get the current category name and data for display
current_category_name = categories[st.session_state.public_view_cat_index]
cat_data = data.get(current_category_name, {})

# --- Page Layout ---
col1, col2 = st.columns([3,3])

with col1:
    st.header(f"📊 Posiciones de Grupo - CAT: {current_category_name}")
    standings_df = logic.get_standings_df(cat_data)
    if not standings_df.empty:
        for group_name, group_df in standings_df.groupby('Grupo'):
            st.subheader(f"Grupo {group_name}")
            st.dataframe(group_df.drop(columns=['Grupo']).set_index('Equipo'), use_container_width=True)
    else:
        st.info("No hay equipos en esta categoría.")

# In pages/2_📺_Pantalla_Publica.py, replace the "with col2:" block

with col2:
    # Check if the knockout phase has been generated at all
    knockout_data_exists = cat_data.get('knockout')

    st.header("🏆 Fase Eliminatoria" if knockout_data_exists else "🎾 Partidos Recientes")

    if knockout_data_exists:
        # If knockout data exists, always show the bracket.
        # The logic file will correctly draw it whether it's in progress or finished.
        bracket_image = logic.generate_bracket_image(cat_data)
        if bracket_image:
            st.graphviz_chart(bracket_image)

        st.subheader("Resultados de Eliminatoria")
        ko_matches = cat_data.get('knockout_individual_matches', [])
        if not ko_matches:
            st.info("Aún no se han registrado partidos de eliminatoria.")
        else:
            for match in reversed(ko_matches[-4:]):
                st.markdown(
                    f"**{match['p1']}** def. **{match['p2']}** ({match['set_scores']})<br>"
                    f"_({match['team1']} vs {match['team2']})_",
                    unsafe_allow_html=True
                )
    else:
        # If no knockout data exists, show recent GROUP matches.
        group_matches = cat_data.get('individual_matches', [])
        if not group_matches:
            st.info("Aún no se han registrado partidos de grupo.")
        else:
            for match in reversed(group_matches[-10:]):
                st.markdown(
                    f"**{match['p1']}** def. **{match['p2']}** ({match['set_scores']})<br>"
                    f"_({match['team1']} vs {match['team2']})_",
                    unsafe_allow_html=True
                )


# --- Stable Auto-Refresh ---
time.sleep(1)
st.rerun()