# 1_👑_Admin.py

import streamlit as st
import pandas as pd
from collections import defaultdict
import tournament_logic as logic
import json
import time

# --- Page Configuration ---
st.set_page_config(page_title="Admin Panel", page_icon="👑", layout="wide")
st.markdown("<style>.main .block-container {padding-top: 1rem;}</style>", unsafe_allow_html=True)

# --- Session State Initialization ---
if 'data' not in st.session_state: st.session_state.data = logic.load_data()
if 'registration_form_key' not in st.session_state: st.session_state.registration_form_key = 0
if 'newly_created_category' not in st.session_state: st.session_state.newly_created_category = None

# --- Helper Functions ---
def save_and_reload():
    logic.save_data(st.session_state.data)

def get_current_category_data():
    cat_name = st.session_state.get('current_category')
    return st.session_state.data.get(cat_name) if cat_name else None

# --- Sidebar ---
st.sidebar.title("🎾 Menú del Torneo")
categories = list(st.session_state.data.keys())
index = 0
if st.session_state.newly_created_category and st.session_state.newly_created_category in categories:
    index = categories.index(st.session_state.newly_created_category)
    st.session_state.newly_created_category = None
elif 'current_category' in st.session_state and st.session_state.current_category in categories:
    index = categories.index(st.session_state.current_category)

st.sidebar.selectbox("Selecciona una Categoría", options=categories, key='current_category', index=index)

# In 1_👑_Admin.py, replace the "Gestionar Categorías" expander in the sidebar

with st.sidebar.expander("Gestionar Torneo y Categorías", expanded=True):
    # This button allows the user to clear the session and start over.
    if st.button("✨ Iniciar Torneo Nuevo", use_container_width=True):
        st.session_state.data = {}
        st.session_state.current_category = None # Clear selected category
        st.success("Nuevo torneo iniciado.")
        time.sleep(1)
        st.rerun()
        
    st.subheader("Crear Nueva Categoría")
    new_cat_name = st.text_input("Nombre", key="new_cat_name_input", label_visibility="collapsed").strip().upper()
    if st.button("Crear Categoría"):
        if not st.session_state.data:
            st.session_state.data = {} # Ensure data dict exists if starting from empty
        if new_cat_name:
            logic.initialize_category(st.session_state.data, new_cat_name)
            st.session_state.newly_created_category = new_cat_name
            st.rerun()
        else:
            st.warning("El nombre de la categoría no puede estar vacío.")

    st.subheader("Eliminar Categoría")
    if categories:
        cat_to_delete = st.selectbox("Selecciona Categoría", options=[""] + categories, key="delete_cat_select", label_visibility="collapsed")
        if cat_to_delete:
            if st.button(f"Eliminar '{cat_to_delete}'", type="primary"):
                message = logic.delete_category(st.session_state.data, cat_to_delete)
                # Ensure we select a valid category after deletion
                if st.session_state.current_category == cat_to_delete:
                    st.session_state.current_category = categories[0] if len(categories) > 1 else None
                st.success(message)
                st.rerun()
    else:
        st.info("No hay categorías para eliminar.")
    
with st.sidebar.expander("Cargar / Guardar Torneo"):
    st.subheader("Cargar Torneo (subir .json)")
    uploaded_file = st.file_uploader(
        "Selecciona un archivo .json de torneo", type=['json'], label_visibility="collapsed")

    if uploaded_file is not None:
        try:
            string_data = uploaded_file.getvalue().decode("utf-8")
            new_data = json.loads(string_data)
            st.session_state.data = new_data
            save_and_reload()
            st.success("¡Torneo cargado con éxito!")
            time.sleep(1); st.rerun()
        except Exception as e:
            st.error(f"Error al procesar el archivo: {e}")

    st.subheader("Guardar y Descargar Torneo (.json)")
    # Convert current tournament data to a JSON string for the download button
    json_string = json.dumps(st.session_state.data, indent=4)
    st.download_button(
        label="📥 Guardar y Descargar Archivo",
        data=json_string,
        file_name="team_tournament_data.json",
        mime="application/json",
        use_container_width=True
    )


# --- Main Page Content ---
st.title("👑 Panel de Administración")
cat_data = get_current_category_data()
if not cat_data:
    st.info("Selecciona una categoría en el menú lateral o crea una nueva para empezar."); st.stop()


st.header(f"Categoría: {st.session_state.current_category}")
tab_rosters, tab_main, tab_history, tab_knockout = st.tabs(["👥 Plantillas", "📊 Posiciones", "📜 Historial", "🏆 Fase Eliminatoria"])


with tab_rosters:
    col1, col2 = st.columns([1.5, 1])
    
    with col1:
        st.subheader("Equipos Registrados")
        if not cat_data.get('teams'): st.info("No hay equipos registrados en esta categoría.")
        else:
            df = pd.DataFrame(cat_data.get('teams', {}).values()).assign(name=cat_data.get('teams', {}).keys())
            for group, teams in df.groupby('group'):
                st.subheader(f"Grupo {group}")
                for _, team in teams.iterrows():
                    st.markdown(f"**{team['name']}**: {', '.join(p.title() for p in team['players'])}")
                    
    with col2:
        st.subheader("Agregar Equipo")
        with st.form(key=f"new_team_form_{st.session_state.registration_form_key}"):
            team_name = st.text_input("Nombre del Equipo")
            team_group = st.text_input("Grupo (ej: A, B)", "A")
            team_players = st.text_area("Jugadores (separados por comas)")
            if st.form_submit_button("Registrar Equipo"):
                if cat_data is not None and team_name and team_players:
                    st.success(logic.register_team(cat_data, team_name, team_group, team_players))
                    save_and_reload(); st.session_state.registration_form_key += 1; st.rerun()
                else: st.error("Por favor, completa todos los campos.")
        st.subheader("Eliminar Equipo")
        teams_in_cat = list(cat_data.get('teams', {}).keys())
        if not teams_in_cat: st.info("No hay equipos para eliminar.")
        else:
            team_to_delete = st.selectbox("Selecciona un equipo", options=[""] + teams_in_cat, label_visibility="collapsed")
            if team_to_delete:
                st.warning(f"¿Estás seguro de que quieres eliminar a {team_to_delete}?")
                if st.button(f"Sí, eliminar a {team_to_delete}", type="primary"):
                    try:
                        message = logic.delete_team(cat_data, team_to_delete); save_and_reload()
                        st.success(message); st.rerun()
                    except ValueError as e: st.error(e)
                    
with tab_main:
    st.subheader("Registrar Partido de Grupo")
    with st.form("new_group_match_form"):
        result = st.text_input("Resultado", placeholder="ej: Nadal def. Federer 6-4 7-6", label_visibility="collapsed")
        if st.form_submit_button("💾 Guardar Partido"):
            if result:
                try:
                    msg = logic.record_group_match(cat_data, result); save_and_reload()
                    st.success("Partido de grupo registrado.");
                    if msg: st.info(msg)
                    st.rerun()
                except ValueError as e: st.error(f"Error: {e}")
            else: st.warning("El campo de resultado está vacío.")
    st.subheader("Posiciones de Grupo")
    standings_df = logic.get_standings_df(cat_data)
    if not standings_df.empty:
        for group_name, group_df in standings_df.groupby('Grupo'):
            st.markdown(f"**Grupo {group_name}**"); st.dataframe(group_df.drop(columns=['Grupo']).set_index('Equipo'), use_container_width=True)
    else: st.info("No hay equipos registrados.")
    st.markdown("---")
    
            
with tab_history:
    st.subheader("Resultados de Enfrentamientos por Equipos")
    if not cat_data.get('team_results'): st.info("No hay enfrentamientos de grupo completados.")
    else:
        for result in reversed(cat_data.get('team_results', [])):
            team1, team2 = result['teams']
            with st.expander(f"**{team1} vs {team2}** | Ganador: **{result['winner']}** ({result.get('score', 'N/A')})"):
                for m in cat_data['individual_matches']:
                    if {m['team1'], m['team2']} == {team1, team2}:
                        st.write(f"• {m['p1']} def. {m['p2']} ({m['set_scores']})")


with tab_knockout:
    st.header("Fase Eliminatoria")

    is_finished = bool(cat_data.get('champion'))
    knockout_started = bool(cat_data.get('knockout'))

    # Always show the champion message if it exists
    if is_finished:
        #st.balloons()
        st.title(f"🏆 ¡El campeón es {cat_data['champion']}! 🏆")
        
        # Prepare the Excel file data using the new function
        excel_data = logic.export_category_to_excel(cat_data)
        
        # Create the download button with the dynamic file name
        st.download_button(
            label="📥 Descargar Resultados de Categoría (.xlsx)",
            data=excel_data,
            file_name=f"Torneo Cat_{st.session_state.current_category}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    # Logic for displaying the main content of the tab
    if knockout_started:
        # If the knockout has started, ALWAYS show the bracket and the two-column layout
        #st.subheader("Cuadro de Eliminatorias")
        bracket_image = logic.generate_bracket_image(cat_data)
        if bracket_image:
            st.graphviz_chart(bracket_image)
        st.markdown("---")
        
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Registrar Partido de Eliminatoria")
            with st.form("new_ko_match_form"):
                result = st.text_input("Resultado", key="ko_result", label_visibility="collapsed", disabled=is_finished)
                if st.form_submit_button("💾 Guardar Partido", disabled=is_finished):
                    if result:
                        try:
                            msg = logic.record_knockout_match(cat_data, result); save_and_reload()
                            st.success(msg); st.rerun()
                        except ValueError as e: st.error(f"Error: {e}")
                    else: st.warning("El campo de resultado está vacío.")
            
            if st.button("↩️ Resetear Eliminatoria"):
                logic.reset_knockout_phase(cat_data); save_and_reload(); st.rerun()
                
        with c2:
            st.subheader("Resultados Individuales de KO")
            ko_matches = cat_data.get('knockout_individual_matches', [])
            if not ko_matches:
                st.info("No hay partidos de eliminatoria.")
            else:
                for m in reversed(ko_matches[-4:]):
                    st.markdown(f"**{m['p1']}** def. **{m['p2']}** ({m['set_scores']})<br>_({m['team1']} vs {m['team2']})_", unsafe_allow_html=True)

    else: # This block only runs if the knockout has not started yet
        st.info("La fase de grupos ha terminado. Genera el cuadro para continuar.")
        with st.form("generate_knockout_form"):
            c1, c2 = st.columns(2)
            num_advancing = c1.number_input("Equipos que avanzan por grupo", 1, 4, 2, 1)
            bracket_size = c2.selectbox("Tamaño del cuadro", [4, 8, 16, 32, 64])
            if st.form_submit_button("Generar Cuadro"):
                st.success(logic.generate_knockout_bracket(cat_data, num_advancing, bracket_size))
                save_and_reload(); st.rerun()