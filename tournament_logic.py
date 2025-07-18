# tournament_logic.py

import json
import re
from collections import defaultdict
import random
import pandas as pd
import graphviz
import io


DATA_FILE = "team_tournament_data.json"

# --- Data Handling and Core Logic (No changes in this section) ---
def load_data():
    try:
        with open(DATA_FILE, 'r') as f: return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError): return {}
    
    
def save_data(data):
    with open(DATA_FILE, 'w') as f: json.dump(data, f, indent=4)
    
    
def initialize_category(data, cat_name):
    if cat_name not in data:
        data[cat_name] = {"teams": {}, "team_results": [], "individual_matches": [], "knockout": [], "knockout_individual_matches": []}
    return data[cat_name]


def delete_category(data, cat_name):
    if cat_name in data:
        data.pop(cat_name)
        return f"Categoría '{cat_name}' eliminada permanentemente."
    return "Categoría no encontrada."


def delete_team(cat_data, team_name_to_delete):
    if cat_data.get('knockout'):
        raise ValueError("No se pueden eliminar equipos una vez que ha comenzado la fase eliminatoria.")
    if team_name_to_delete in cat_data.get('teams', {}):
        cat_data['teams'].pop(team_name_to_delete)
        cat_data['individual_matches'] = [m for m in cat_data.get('individual_matches', []) if team_name_to_delete not in (m['team1'], m['team2'])]
        cat_data['team_results'] = [r for r in cat_data.get('team_results', []) if team_name_to_delete not in r['teams']]
        return f"Equipo '{team_name_to_delete}' y todos sus partidos han sido eliminados."
    return f"Equipo '{team_name_to_delete}' no encontrado."


def register_team(cat_data, name, group, players_str):
    players = [p.strip().lower() for p in players_str.split(',')]
    cat_data['teams'][name] = {"group": group.upper(), "players": players, "team_matches_played": 0, "team_matches_won": 0, "individual_matches_won": 0, "sets_won": 0, "sets_lost": 0, "games_won": 0, "games_lost": 0}
    return f"Equipo '{name}' registrado en el grupo {group}."


def parse_match_result(result_line):
    match = re.match(r"(.+?) def\. (.+?) (.+)", result_line)
    if not match: raise ValueError("Formato invalido (ej: Alice def. Bob 6-4 6-3)")
    p1, p2, score = match.groups()
    p1_sets, p2_sets, p1_games, p2_games, set_scores = 0, 0, 0, 0, []
    for s in score.split():
        g1, g2 = map(int, s.split("-")); set_scores.append(f"{g1}-{g2}")
        if g1 > g2: p1_sets += 1
        else: p2_sets += 1
        p1_games += g1; p2_games += g2
    return p1.strip(), p2.strip(), p1_sets, p2_sets, p1_games, p2_games, " ".join(set_scores)


def identify_team(player, teams):
    names = [n.strip().lower() for n in player.split("/")]
    for team_name, info in teams.items():
        if all(n in info['players'] for n in names): return team_name
    return None


def record_group_match(cat_data, result_line):
    p1, p2, s1, s2, g1, g2, set_scores = parse_match_result(result_line)
    t1 = identify_team(p1, cat_data['teams']); t2 = identify_team(p2, cat_data['teams'])
    if not t1 or not t2: raise ValueError(f"No se pudo identificar equipos para: {p1}, {p2}")
    if t1 == t2: raise ValueError("Jugadores pertenecen al mismo equipo.")
    winner_team = t1 if s1 > s2 else t2
    cat_data['individual_matches'].append({"p1": p1, "p2": p2, "team1": t1, "team2": t2, "winner": winner_team, "set_scores": set_scores})
    cat_data['teams'][winner_team]['individual_matches_won'] += 1
    for team, sets_won, sets_lost, games_won, games_lost in [(t1, s1, s2, g1, g2), (t2, s2, s1, g2, g1)]:
        cat_data['teams'][team]['sets_won'] += sets_won; cat_data['teams'][team]['sets_lost'] += sets_lost
        cat_data['teams'][team]['games_won'] += games_won; cat_data['teams'][team]['games_lost'] += games_lost
    matches_between = [m for m in cat_data['individual_matches'] if {m['team1'], m['team2']} == {t1, t2}]
    confrontation_recorded = any(res for res in cat_data.get('team_results', []) if frozenset(res['teams']) == frozenset([t1, t2]))
    if len(matches_between) >= 3 and not confrontation_recorded:
        tally = defaultdict(int); [tally.__setitem__(m['winner'], tally[m['winner']] + 1) for m in matches_between[:3]]
        winner = max(tally, key=tally.get)
        cat_data['teams'][t1]['team_matches_played'] += 1; cat_data['teams'][t2]['team_matches_played'] += 1
        cat_data['teams'][winner]['team_matches_won'] += 1
        cat_data['team_results'].append({"teams": [t1, t2], "winner": winner, "score": f"{tally[winner]}-{3 - tally[winner]}"})
        return f"Enfrentamiento de grupo completado: {t1} vs {t2}. Ganador: {winner}"
    return None


def get_standings_df(cat_data):
    if not cat_data.get('teams'): return pd.DataFrame()
    df = pd.DataFrame(cat_data['teams'].values()).assign(Equipo=cat_data['teams'].keys())
    df['Dif Sets'] = df['sets_won'] - df['sets_lost']; df['Dif Games'] = df['games_won'] - df['games_lost']
    df = df.rename(columns={'group': 'Grupo', 'team_matches_played': 'PJ (E)', 'team_matches_won': 'PG (E)', 'individual_matches_won': 'PG (I)', 'sets_won': 'SG', 'sets_lost': 'SP', 'games_won': 'GG', 'games_lost': 'GP'})
    return df[['Grupo', 'Equipo', 'PJ (E)', 'PG (E)', 'PG (I)', 'SG', 'SP', 'Dif Sets', 'GG', 'GP', 'Dif Games']].sort_values(by=['Grupo', 'PG (E)', 'PG (I)', 'Dif Sets', 'Dif Games'], ascending=[True, False, False, False, False]).reset_index(drop=True)


def _get_ko_provisional_winner(cat_data, team_a, team_b):
    if team_b == "BYE": return team_a
    if team_a == "BYE": return team_b
    tally = defaultdict(int)
    for match in cat_data.get('knockout_individual_matches', []):
        if {match['team1'], match['team2']} == {team_a, team_b}: tally[match['winner']] += 1
    if tally[team_a] >= 2: return team_a
    if tally[team_b] >= 2: return team_b
    return None


def _get_ko_final_winner(cat_data, team_a, team_b):
    if team_b == "BYE": return team_a
    if team_a == "BYE": return team_b
    matches_between = [m for m in cat_data.get('knockout_individual_matches', []) if {m['team1'], m['team2']} == {team_a, team_b}]
    if len(matches_between) < 3: return None
    tally = defaultdict(int)
    for match in matches_between: tally[match['winner']] += 1
    return max(tally, key=tally.get) if tally else None


def _check_and_generate_next_round(cat_data):
    if not cat_data.get('knockout'): return
    current_round_matchups = cat_data['knockout'][-1]
    winners_this_round, all_decided = [], True
    for team_a, team_b in current_round_matchups:
        winner = _get_ko_final_winner(cat_data, team_a, team_b)
        if winner: winners_this_round.append(winner)
        else: all_decided = False; break
    if all_decided:
        if len(winners_this_round) == 1: cat_data['champion'] = winners_this_round[0]
        else:
            next_round = [(winners_this_round[i], winners_this_round[i+1] if i+1 < len(winners_this_round) else "BYE") for i in range(0, len(winners_this_round), 2)]
            cat_data['knockout'].append(next_round)
            
            
def record_knockout_match(cat_data, result_line):
    p1, p2, s1, s2, g1, g2, set_scores = parse_match_result(result_line)
    t1 = identify_team(p1, cat_data['teams']); t2 = identify_team(p2, cat_data['teams'])
    if not t1 or not t2: raise ValueError(f"No se pudo identificar equipos para: {p1}, {p2}")
    current_round_matchups = cat_data['knockout'][-1]; match_found = False
    for team_a, team_b in current_round_matchups:
        if {t1, t2} == {team_a, team_b}:
            matches_between = [m for m in cat_data.get('knockout_individual_matches', []) if {m['team1'], m['team2']} == {t1, t2}]
            if len(matches_between) >= 3: raise ValueError(f"Ya se han jugado 3 partidos entre {t1} y {t2}.")
            match_found = True; break
    if not match_found: raise ValueError(f"No se encontró un enfrentamiento activo entre {t1} y {t2}.")
    winner_team = t1 if s1 > s2 else t2
    cat_data.setdefault('knockout_individual_matches', []).append({"p1": p1, "p2": p2, "team1": t1, "team2": t2, "winner": winner_team, "set_scores": set_scores})
    _check_and_generate_next_round(cat_data)
    return f"Partido de eliminatoria registrado: {winner_team} gana."


def generate_knockout_bracket(cat_data, num_advancing, bracket_size):
    if num_advancing != 2:
        groups = defaultdict(list); [groups[d['group']].append((team, d)) for team, d in cat_data['teams'].items()]
        qualifiers = []
        for group, group_teams in sorted(groups.items()):
            sorted_teams = sorted(group_teams, key=lambda kv: (kv[1]['team_matches_won'], kv[1]['individual_matches_won'], kv[1]['sets_won'] - kv[1]['sets_lost'], kv[1]['games_won'] - kv[1]['games_lost']), reverse=True)
            qualifiers.extend([t[0] for t in sorted_teams[:num_advancing]])
        while len(qualifiers) < bracket_size: qualifiers.append("BYE")
        random.shuffle(qualifiers); matchups = [(qualifiers[i], qualifiers[i+1]) for i in range(0, bracket_size, 2)]
    else:
        first_place_pot, second_place_pot = [], []
        groups = defaultdict(list); [groups[d['group']].append((team, d)) for team, d in cat_data['teams'].items()]
        for group, group_teams in sorted(groups.items()):
            sorted_teams = sorted(group_teams, key=lambda kv: (kv[1]['team_matches_won'], kv[1]['individual_matches_won'], kv[1]['sets_won'] - kv[1]['sets_lost'], kv[1]['games_won'] - kv[1]['games_lost']), reverse=True)
            if len(sorted_teams) > 0: first_place_pot.append({'name': sorted_teams[0][0], 'group': group})
            if len(sorted_teams) > 1: second_place_pot.append({'name': sorted_teams[1][0], 'group': group})
        while len(first_place_pot) + len(second_place_pot) < bracket_size:
            second_place_pot.append({'name': "BYE", 'group': "BYE_GROUP"})
        random.shuffle(first_place_pot); random.shuffle(second_place_pot)
        matchups, available_seconds = [], list(second_place_pot)
        for first_team in first_place_pot:
            best_partner = next((p for p in available_seconds if first_team['group'] != p['group']), None)
            if best_partner is None and available_seconds: best_partner = available_seconds[0]
            if best_partner:
                matchups.append((first_team['name'], best_partner['name'])); available_seconds.remove(best_partner)
    cat_data['knockout'] = [matchups]; cat_data['knockout_individual_matches'] = []
    cat_data.pop('champion', None)
    return f"Eliminatoria de {bracket_size} generada."


def generate_bracket_image(cat_data):
    import graphviz
    if not cat_data.get('knockout'):
        return None

    dot = graphviz.Digraph(graph_attr={
        'splines': 'polyline',
        'rankdir': 'LR',
        'bgcolor': "#535050"
    })

    dot.attr('node', shape='box', style='rounded,filled', fillcolor="#989494", fontname='sans-serif')
    dot.attr('edge', style='invis')

    team_to_source_node = {}
    round_nodes = {}  # Guardamos los nodos de cada ronda

    for r_idx, round_matchups in enumerate(cat_data['knockout']):
        round_len = len(round_matchups)
        round_name = f"Ronda {r_idx + 1}"
        if round_len == 1 and r_idx > 0: round_name = "Final"
        elif round_len == 2: round_name = "Semifinales"
        elif round_len == 4: round_name = "Cuartos de Final"
        elif round_len == 8: round_name = "Octavos de Final"
        elif round_len == 16: round_name = "Dieciseisavos de Final"

        round_nodes[r_idx] = []

        with dot.subgraph(name=f'cluster_{r_idx}') as c:
            c.attr(label=round_name, style='rounded', color='lightgrey', fontcolor='black')

            for m_idx, (team_a, team_b) in enumerate(round_matchups):
                node_id = f'R{r_idx}M{m_idx}'
                round_nodes[r_idx].append(node_id)  # Guardar para alineación
                fillcolor = "#e3fdeb"

                if team_b == "BYE":
                    label = f"{team_a}\n(BYE)"
                else:
                    label = f"{team_a} vs {team_b}"

                # Marcar ganador provisional
                provisional_winner = _get_ko_provisional_winner(cat_data, team_a, team_b)
                if provisional_winner:
                    label = f"<{ '<b>' + team_a + '</b>' if provisional_winner == team_a else team_a } vs {'<b>' + team_b + '</b>' if provisional_winner == team_b else team_b}>"
                    fillcolor = "#e8f5e9"

                # Marcar ganador final
                final_winner = _get_ko_final_winner(cat_data, team_a, team_b)
                if final_winner:
                    team_to_source_node[final_winner] = node_id

                c.node(node_id, label=label, fillcolor=fillcolor)

                if r_idx > 0:
                    if team_a != "BYE" and team_a in team_to_source_node:
                        dot.edge(team_to_source_node[team_a], node_id)
                    if team_b != "BYE" and team_b in team_to_source_node:
                        dot.edge(team_to_source_node[team_b], node_id)

            c.attr(rank='same')  # Fuerza alineación horizontal entre partidos de la ronda

    # Agregar bordes invisibles entre rondas para centrar visualmente
    for r in range(len(round_nodes) - 1):
        current = round_nodes[r]
        nxt = round_nodes[r + 1]
        if current and nxt:
            mid_from = current[len(current) // 2]
            mid_to = nxt[len(nxt) // 2]
            dot.edge(mid_from, mid_to, style='invis')

    # Campeón
    if cat_data.get('champion'):
        champ = cat_data.get('champion')
        dot.node('champion_node', f'🏆 CAMPEÓN 🏆\n\n{champ}',
                 shape='box', style='rounded,filled', fillcolor='#fff59d', fontname='sans-serif')
        if champ in team_to_source_node:
            dot.edge(team_to_source_node[champ], 'champion_node')

    return dot



def reset_knockout_phase(cat_data):
    cat_data['knockout'] = []; cat_data['knockout_individual_matches'] = []; cat_data.pop('champion', None)
    return "La fase eliminatoria ha sido reiniciada."



def _write_formatted_standings(writer, sheet_name, cat_data):
    """Writes the group standings with custom formatting to a specific sheet."""
    workbook = writer.book
    worksheet = writer.book.get_worksheet_by_name(sheet_name)
    group_header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'font_size': 12, 'border': 1, 'bg_color': '#D3D3D3'})
    table_header_format = workbook.add_format({'bold': True, 'border': 1, 'align': 'center', 'bg_color': '#F2F2F2'})
    cell_format = workbook.add_format({'border': 1, 'align': 'center'})
    standings_df = get_standings_df(cat_data)
    if standings_df.empty: return 0
    num_cols = len(standings_df.columns)
    start_row = 0
    for group_name, group_df in standings_df.groupby('Grupo'):
        if start_row > 0: start_row += 1
        worksheet.merge_range(start_row, 0, start_row, num_cols - 2, f"GRUPO {group_name}", group_header_format)
        start_row += 1
        for col_num, value in enumerate(group_df.columns[1:]):
            worksheet.write(start_row, col_num, value, table_header_format)
        start_row += 1
        for _, row_data in group_df.iterrows():
            for col_num, value in enumerate(row_data.values[1:]):
                worksheet.write(start_row, col_num, value, cell_format)
            start_row += 1
    worksheet.set_column('A:A', 18)
    worksheet.set_column('B:K', 10)
    return start_row

def export_category_to_excel(cat_data):
    """Generates an in-memory Excel file for a single category with an embedded bracket image."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        sheet_name = "Resultados del Torneo"
        writer.book.add_worksheet(sheet_name)
        
        # Write the formatted standings and get the next available row
        next_row = _write_formatted_standings(writer, sheet_name, cat_data)
        
        # Generate the bracket image in memory
        bracket_dot = generate_bracket_image(cat_data)
        if bracket_dot:
            # Render the Graphviz object to a PNG image in a bytes buffer
            png_image_data = bracket_dot.pipe(format='png')
            image_buffer = io.BytesIO(png_image_data)
            
            # Get the worksheet object and insert the image
            worksheet = writer.book.get_worksheet_by_name(sheet_name)
            worksheet.insert_image(
                next_row + 1, 0,  # The cell (row, col) to insert the top-left of the image
                'bracket.png',    # A placeholder name for the image
                {'image_data': image_buffer}
            )
            
    return output.getvalue()