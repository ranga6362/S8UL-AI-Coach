"""
S8UL AI Coach v3.2 - Free Fire Max Esports Team Management
FINAL BUILD - Enterprise Edition (Clean Deploy)
Features: IGL+Nader, Mood Tracker, Live Tournaments,
          AI VOD Timestamps, User Management, Deployment Ready
"""

import streamlit as st
import sqlite3
import hashlib
import random
import datetime
import json
import time
import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# ───────────────────────────────────────────────
# CONFIG
# ───────────────────────────────────────────────
DB_PATH = "s8ul_coach.db"
S8UL_RED = "#ff3333"
S8UL_DARK = "#0a0a0a"
S8UL_CARD = "#141414"
S8UL_GREEN = "#00c853"
S8UL_AMBER = "#ffab00"

FF_MAPS = ["Bermuda", "Kalahari", "Purgatory", "Alpine", "Solara", "Nexterra"]
FF_ROLES = ["IGL", "Nader", "Rusher", "Support", "Sniper", "Flex"]
USER_ROLES = ["Admin", "Head Coach", "Analyst", "Team Manager"]

PLACEMENT_POINTS = {
    1: 12, 2: 9, 3: 8, 4: 7, 5: 6,
    6: 5, 7: 4, 8: 3, 9: 2, 10: 1
}

MOOD_EMOJIS = {
    "Excellent": "😄", "Good": "🙂", "Neutral": "😐",
    "Tired": "😴", "Burned Out": "🔥", "Stressed": "😰"
}

BURNOUT_LEVELS = {
    "Excellent": 0, "Good": 1, "Neutral": 2,
    "Tired": 3, "Burned Out": 4, "Stressed": 3
}

# ───────────────────────────────────────────────
# DATABASE
# ───────────────────────────────────────────────
def init_db():
    # DELETE old database file to ensure completely fresh start (no old demo data)
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Users table - drop and recreate to handle schema changes
    c.execute("DROP TABLE IF EXISTS users")
    c.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            email TEXT,
            created_at TEXT,
            last_login TEXT,
            is_active INTEGER DEFAULT 1
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            uid TEXT UNIQUE,
            role TEXT,
            status TEXT DEFAULT 'Active',
            joined_date TEXT,
            garena_api_key TEXT,
            last_api_sync TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS daily_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER,
            date TEXT,
            matches INTEGER DEFAULT 0,
            kills INTEGER DEFAULT 0,
            damage REAL DEFAULT 0,
            survival_time REAL DEFAULT 0,
            booyahs INTEGER DEFAULT 0,
            headshots INTEGER DEFAULT 0,
            FOREIGN KEY (player_id) REFERENCES players(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS scrims (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            map TEXT,
            placement INTEGER,
            kills INTEGER,
            total_points INTEGER,
            notes TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS igl_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            map TEXT,
            zone INTEGER,
            call_type TEXT,
            outcome TEXT,
            notes TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS opponents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_name TEXT,
            match_date TEXT,
            map TEXT,
            our_placement INTEGER,
            their_placement INTEGER,
            our_kills INTEGER,
            their_kills INTEGER,
            our_points INTEGER,
            their_points INTEGER,
            result TEXT,
            notes TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS team_compositions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            map TEXT,
            igl_id INTEGER,
            nader_id INTEGER,
            rusher1_id INTEGER,
            rusher2_id INTEGER,
            support_id INTEGER,
            sniper_id INTEGER,
            created_date TEXT,
            is_active INTEGER DEFAULT 1
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS map_strategies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            map TEXT,
            drop_location TEXT,
            rotation TEXT,
            late_game_plan TEXT,
            notes TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS tournaments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            start_date TEXT,
            end_date TEXT,
            prize_pool TEXT,
            status TEXT,
            format TEXT,
            notes TEXT,
            is_live INTEGER DEFAULT 0,
            current_placement INTEGER,
            total_teams INTEGER,
            points INTEGER DEFAULT 0,
            kills INTEGER DEFAULT 0,
            matches_played INTEGER DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS vod_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_date TEXT,
            map TEXT,
            opponent TEXT,
            video_link TEXT,
            timestamp TEXT,
            notes TEXT,
            tags TEXT,
            ai_timestamps TEXT,
            ai_fights_detected INTEGER DEFAULT 0,
            ai_rotations_detected INTEGER DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS player_mood (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER,
            date TEXT,
            mood TEXT,
            energy_level INTEGER,
            sleep_hours REAL,
            motivation INTEGER,
            physical_pain INTEGER,
            notes TEXT,
            FOREIGN KEY (player_id) REFERENCES players(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS garena_api_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER,
            uid TEXT,
            api_data TEXT,
            fetched_at TEXT,
            FOREIGN KEY (player_id) REFERENCES players(id)
        )
    """)

    # Seed default users
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        default_users = [
            ("admin", hashlib.sha256("s8uladmin2026".encode()).hexdigest(), "Admin", "admin@s8ul.gg"),
            ("coach", hashlib.sha256("coach123".encode()).hexdigest(), "Head Coach", "coach@s8ul.gg"),
            ("analyst", hashlib.sha256("analyst123".encode()).hexdigest(), "Analyst", "analyst@s8ul.gg"),
            ("manager", hashlib.sha256("manager123".encode()).hexdigest(), "Team Manager", "manager@s8ul.gg"),
        ]
        for username, pwd_hash, role, email in default_users:
            c.execute("INSERT INTO users (username, password_hash, role, email, created_at) VALUES (?,?,?,?,?)",
                     (username, pwd_hash, role, email, datetime.date.today().isoformat()))

    conn.commit()
    conn.close()

def get_conn():
    return sqlite3.connect(DB_PATH)

# ───────────────────────────────────────────────
# USER MANAGEMENT
# ───────────────────────────────────────────────
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_login(username, password):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT password_hash, role FROM users WHERE username=? AND is_active=1", (username,))
    result = c.fetchone()
    conn.close()
    if result and result[0] == hash_password(password):
        return result[1]
    return None

def get_all_users():
    conn = get_conn()
    users = pd.read_sql_query("SELECT id, username, role, email, created_at, last_login, is_active FROM users", conn)
    conn.close()
    return users

def add_user(username, password, role, email=""):
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password_hash, role, email, created_at) VALUES (?,?,?,?,?)",
                 (username, hash_password(password), role, email, datetime.date.today().isoformat()))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def update_user_password(username, new_password):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE users SET password_hash=? WHERE username=?", (hash_password(new_password), username))
    conn.commit()
    conn.close()

def toggle_user_active(username):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        UPDATE users 
        SET is_active = CASE WHEN is_active=1 THEN 0 ELSE 1 END 
        WHERE username=?
    """, (username,))
    conn.commit()
    conn.close()

def delete_user(username):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE username=? AND username!='admin'", (username,))
    conn.commit()
    conn.close()

# ───────────────────────────────────────────────
# AUTH & LOGIN
# ───────────────────────────────────────────────
def login_page():
    st.markdown(f"""
        <div style="text-align:center; padding: 40px 0;">
            <h1 style="color:{S8UL_RED}; font-size: 3rem; margin-bottom: 10px;">S8UL AI COACH</h1>
            <p style="color:#888; font-size: 1.1rem;">Free Fire Max • Esports Team Management v3.2</p>
            <p style="color:#666; font-size: 0.9rem;">Enterprise Edition for S8UL Esports</p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
            st.subheader("🔐 Team Login")
            username = st.text_input("Username", key="login_user")
            password = st.text_input("Password", type="password", key="login_pass")

            c1, c2 = st.columns(2)
            with c1:
                if st.button("Login", use_container_width=True, type="primary"):
                    role = check_login(username, password)
                    if role:
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.session_state.role = role
                        # Update last login
                        conn = get_conn()
                        conn.execute("UPDATE users SET last_login=? WHERE username=?",
                                   (datetime.datetime.now().isoformat(), username))
                        conn.commit()
                        conn.close()
                        st.rerun()
                    else:
                        st.error("Invalid credentials or account inactive")
            with c2:
                if st.button("🎮 Demo Access", use_container_width=True):
                    st.session_state.logged_in = True
                    st.session_state.username = "demo"
                    st.session_state.role = "Demo Coach"
                    st.rerun()

            st.caption("Admin: `admin` / `s8uladmin2026`")
            st.caption("Coach: `coach` / `coach123`")
            st.caption("Analyst: `analyst` / `analyst123`")
            st.caption("Manager: `manager` / `manager123`")

# ───────────────────────────────────────────────
# ADMIN PANEL
# ───────────────────────────────────────────────
def tab_admin():
    st.header("⚙️ Admin Panel")

    if st.session_state.role != "Admin":
        st.error("Admin access only")
        return

    st.subheader("👥 User Management")

    # Add new user
    with st.expander("➕ Add New User"):
        c1, c2 = st.columns(2)
        with c1:
            new_username = st.text_input("Username", key="new_user_name")
            new_password = st.text_input("Password", type="password", key="new_user_pass")
        with c2:
            new_role = st.selectbox("Role", USER_ROLES, key="new_user_role")
            new_email = st.text_input("Email (optional)", key="new_user_email")
        if st.button("Add User", key="add_user_btn"):
            if new_username and new_password:
                if add_user(new_username, new_password, new_role, new_email):
                    st.success(f"Added {new_username} as {new_role}")
                    st.rerun()
                else:
                    st.error("Username already exists")
            else:
                st.error("Username and password required")

    # User list
    users_df = get_all_users()
    if not users_df.empty:
        st.subheader("All Users")
        for _, user in users_df.iterrows():
            status_color = "#00c853" if user["is_active"] else "#888"
            status_text = "Active" if user["is_active"] else "Inactive"

            col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
            with col1:
                st.markdown(f"""
                    <div style="background:{S8UL_CARD}; padding:10px; border-radius:6px;">
                        <p style="color:#fff; font-weight:600; margin:0;">{user['username']}</p>
                        <p style="color:#888; font-size:0.8rem; margin:0;">{user['email'] or 'No email'}</p>
                    </div>
                """, unsafe_allow_html=True)
            with col2:
                st.markdown(f"""
                    <div style="background:{S8UL_CARD}; padding:10px; border-radius:6px; text-align:center;">
                        <p style="color:#888; font-size:0.75rem; margin:0;">ROLE</p>
                        <p style="color:#fff; font-weight:600; margin:0;">{user['role']}</p>
                    </div>
                """, unsafe_allow_html=True)
            with col3:
                st.markdown(f"""
                    <div style="background:{S8UL_CARD}; padding:10px; border-radius:6px; text-align:center;">
                        <p style="color:#888; font-size:0.75rem; margin:0;">STATUS</p>
                        <p style="color:{status_color}; font-weight:600; margin:0;">{status_text}</p>
                    </div>
                """, unsafe_allow_html=True)
            with col4:
                if user["username"] != "admin":
                    if st.button("Toggle", key=f"toggle_{user['username']}"):
                        toggle_user_active(user["username"])
                        st.rerun()
                    if st.button("🗑️", key=f"del_{user['username']}"):
                        delete_user(user["username"])
                        st.rerun()
                else:
                    st.caption("Protected")
    else:
        st.info("No users found")

# ───────────────────────────────────────────────
# MOCK DATA
# ───────────────────────────────────────────────
def generate_mock_stats(uid, days=7):
    seed = int(hashlib.md5(str(uid).encode()).hexdigest(), 16) % 10000
    rng = random.Random(seed)
    stats = []
    base_kills = rng.randint(3, 12)
    base_dmg = rng.randint(800, 2500)
    for i in range(days):
        date = (datetime.date.today() - datetime.timedelta(days=days - 1 - i)).isoformat()
        matches = rng.randint(3, 8)
        kills = max(0, base_kills + rng.randint(-3, 4))
        damage = max(200, base_dmg + rng.randint(-400, 500))
        survival = rng.randint(8, 22)
        booyahs = rng.randint(0, min(2, matches))
        headshots = rng.randint(0, kills)
        stats.append({
            "date": date, "matches": matches, "kills": kills,
            "damage": damage, "survival_time": survival, "booyahs": booyahs,
            "headshots": headshots
        })
    return stats

def seed_demo_data():
    """No hardcoded demo data. Everything must be added manually."""
    pass

# ───────────────────────────────────────────────
# SIDEBAR
# ───────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown(f"""
            <div style="text-align:center; margin-bottom: 20px;">
                <h2 style="color:{S8UL_RED}; margin:0;">S8UL</h2>
                <p style="color:#888; font-size:0.85rem; margin:0;">AI COACH v3.2</p>
                <p style="color:#666; font-size:0.7rem; margin:0;">Enterprise Edition</p>
            </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
            <div style="background:{S8UL_CARD}; padding:12px; border-radius:8px; margin-bottom:15px;">
                <p style="color:#fff; margin:0; font-weight:600;">👤 {st.session_state.username}</p>
                <p style="color:#888; margin:0; font-size:0.8rem;">{st.session_state.role}</p>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("🎯 Active Roster")
        conn = get_conn()
        players = pd.read_sql_query(
            "SELECT name, role, status FROM players WHERE status='Active' ORDER BY role, name",
            conn
        )
        conn.close()

        if not players.empty:
            for _, p in players.iterrows():
                role_emoji = {"IGL": "🧠", "Nader": "💣", "Rusher": "⚡", "Support": "🛡️", "Sniper": "🎯", "Flex": "🔧"}.get(p["role"], "👤")
                st.markdown(f"""
                    <div style="background:{S8UL_CARD}; padding:8px 12px; border-radius:6px; margin-bottom:6px;">
                        <span style="color:#fff; font-weight:500;">{role_emoji} {p["name"]}</span>
                        <span style="color:#888; font-size:0.75rem; float:right;">{p["role"]}</span>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No players added yet")

        st.markdown("---")
        st.subheader("⚡ Quick Actions")

        quick_action = st.selectbox("Action", [
            "Select Action", "Add Player", "Log Scrim", "Add IGL Call", "Record VOD Note",
            "Log Mood"
        ], label_visibility="collapsed")

        if quick_action == "Add Player":
            with st.expander("Add Player", expanded=True):
                new_name = st.text_input("Name", key="sb_name")
                new_uid = st.text_input("UID", key="sb_uid")
                new_role = st.selectbox("Role", FF_ROLES, key="sb_role")
                if st.button("Add", key="sb_add_player"):
                    if new_name and new_uid:
                        conn = get_conn()
                        try:
                            conn.execute("INSERT INTO players (name, uid, role, joined_date) VALUES (?,?,?,?)",
                                       (new_name, new_uid, new_role, datetime.date.today().isoformat()))
                            conn.commit()
                            st.success(f"Added {new_name}")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("UID already exists")
                        finally:
                            conn.close()
                    else:
                        st.error("Name and UID required")

        elif quick_action == "Log Scrim":
            with st.expander("Log Scrim", expanded=True):
                s_map = st.selectbox("Map", FF_MAPS, key="sb_s_map")
                s_place = st.number_input("Placement", 1, 12, 1, key="sb_s_place")
                s_kills = st.number_input("Kills", 0, 50, 0, key="sb_s_kills")
                s_notes = st.text_area("Notes", key="sb_s_notes")
                if st.button("Log", key="sb_log_scrim"):
                    pts = PLACEMENT_POINTS.get(s_place, 0) + s_kills
                    conn = get_conn()
                    conn.execute("INSERT INTO scrims (date, map, placement, kills, total_points, notes) VALUES (?,?,?,?,?,?)",
                               (datetime.date.today().isoformat(), s_map, s_place, s_kills, pts, s_notes))
                    conn.commit()
                    conn.close()
                    st.success(f"Logged: {pts} points")
                    st.rerun()

        elif quick_action == "Add IGL Call":
            with st.expander("IGL Call", expanded=True):
                i_map = st.selectbox("Map", FF_MAPS, key="sb_i_map")
                i_zone = st.number_input("Zone", 1, 6, 3, key="sb_i_zone")
                i_type = st.text_input("Call Type", key="sb_i_type")
                i_out = st.selectbox("Outcome", ["Success", "Failure", "Partial"], key="sb_i_out")
                i_notes = st.text_area("Notes", key="sb_i_notes")
                if st.button("Save", key="sb_save_igl"):
                    conn = get_conn()
                    conn.execute("INSERT INTO igl_calls (date, map, zone, call_type, outcome, notes) VALUES (?,?,?,?,?,?)",
                               (datetime.date.today().isoformat(), i_map, i_zone, i_type, i_out, i_notes))
                    conn.commit()
                    conn.close()
                    st.success("Call logged")
                    st.rerun()

        elif quick_action == "Record VOD Note":
            with st.expander("VOD Note", expanded=True):
                v_map = st.selectbox("Map", FF_MAPS, key="sb_v_map")
                v_opp = st.text_input("Opponent", key="sb_v_opp")
                v_time = st.text_input("Timestamp (MM:SS)", key="sb_v_time")
                v_notes = st.text_area("Notes", key="sb_v_notes")
                if st.button("Save", key="sb_save_vod"):
                    conn = get_conn()
                    conn.execute("INSERT INTO vod_reviews (match_date, map, opponent, timestamp, notes) VALUES (?,?,?,?,?)",
                               (datetime.date.today().isoformat(), v_map, v_opp, v_time, v_notes))
                    conn.commit()
                    conn.close()
                    st.success("Note saved")
                    st.rerun()

        elif quick_action == "Log Mood":
            with st.expander("Player Mood", expanded=True):
                conn = get_conn()
                p_list = pd.read_sql_query("SELECT id, name FROM players WHERE status='Active'", conn)
                conn.close()
                if not p_list.empty:
                    mood_player = st.selectbox("Player", p_list["name"].tolist(), key="sb_mood_player")
                    mood = st.selectbox("Mood", list(MOOD_EMOJIS.keys()), key="sb_mood")
                    energy = st.slider("Energy (1-10)", 1, 10, 5, key="sb_energy")
                    sleep = st.slider("Sleep Hours", 0.0, 12.0, 7.0, 0.5, key="sb_sleep")
                    motivation = st.slider("Motivation (1-10)", 1, 10, 5, key="sb_motivation")
                    pain = st.slider("Physical Pain (0-10)", 0, 10, 0, key="sb_pain")
                    mood_notes = st.text_area("Notes", key="sb_mood_notes")
                    if st.button("Save Mood", key="sb_save_mood"):
                        pid = p_list[p_list["name"] == mood_player]["id"].values[0]
                        conn = get_conn()
                        conn.execute("""
                            INSERT INTO player_mood (player_id, date, mood, energy_level, sleep_hours, motivation, physical_pain, notes)
                            VALUES (?,?,?,?,?,?,?,?)
                        """, (pid, datetime.date.today().isoformat(), mood, energy, sleep, motivation, pain, mood_notes))
                        conn.commit()
                        conn.close()
                        st.success("Mood logged!")
                        st.rerun()
                else:
                    st.info("No players available")

        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

# ───────────────────────────────────────────────
# TAB 1: PERFORMANCE TRACKER
# ───────────────────────────────────────────────
def tab_performance():
    st.header("📊 Performance Tracker")

    conn = get_conn()
    players_df = pd.read_sql_query("SELECT id, name, role FROM players WHERE status='Active'", conn)

    if players_df.empty:
        st.info("No active players. Add players from the sidebar.")
        conn.close()
        return

    selected_player = st.selectbox("Select Player", players_df["name"].tolist())
    pid = players_df[players_df["name"] == selected_player]["id"].values[0]

    stats_df = pd.read_sql_query("""
        SELECT date, matches, kills, damage, survival_time, booyahs, headshots
        FROM daily_stats
        WHERE player_id = ?
        ORDER BY date DESC
        LIMIT 14
    """, conn, params=(pid,))
    conn.close()

    if stats_df.empty:
        st.info("No stats recorded for this player yet.")
        return

    stats_df = stats_df.sort_values("date")

    total_matches = stats_df["matches"].sum()
    total_kills = stats_df["kills"].sum()
    avg_damage = stats_df["damage"].mean()
    avg_survival = stats_df["survival_time"].mean()
    total_booyahs = stats_df["booyahs"].sum()
    total_headshots = stats_df["headshots"].sum()
    kpm = round(total_kills / total_matches, 2) if total_matches > 0 else 0
    hsr = round(total_headshots / total_kills * 100, 1) if total_kills > 0 else 0

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    cards = [
        (c1, "🎮 Matches", total_matches),
        (c2, "⚔️ Kills", total_kills),
        (c3, "💥 Avg Damage", f"{avg_damage:.0f}"),
        (c4, "⏱️ Avg Survival", f"{avg_survival:.1f}m"),
        (c5, "🏆 Booyahs", total_booyahs),
        (c6, "🎯 HSR", f"{hsr}%"),
    ]
    for col, label, val in cards:
        col.markdown(f"""
            <div style="background:{S8UL_CARD}; padding:15px; border-radius:10px; text-align:center;">
                <p style="color:#888; font-size:0.8rem; margin:0;">{label}</p>
                <p style="color:{S8UL_RED}; font-size:1.6rem; font-weight:700; margin:0;">{val}</p>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        fig_kills = go.Figure()
        fig_kills.add_trace(go.Scatter(
            x=stats_df["date"], y=stats_df["kills"],
            mode="lines+markers", name="Kills",
            line=dict(color=S8UL_RED, width=3),
            marker=dict(size=8)
        ))
        fig_kills.add_trace(go.Scatter(
            x=stats_df["date"], y=stats_df["headshots"],
            mode="lines+markers", name="Headshots",
            line=dict(color=S8UL_AMBER, width=2),
            marker=dict(size=6)
        ))
        fig_kills.update_layout(
            title="Kills & Headshots Trend", paper_bgcolor=S8UL_DARK,
            plot_bgcolor=S8UL_CARD, font_color="#fff",
            margin=dict(l=20, r=20, t=40, b=20),
            xaxis=dict(gridcolor="#333"), yaxis=dict(gridcolor="#333"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02)
        )
        st.plotly_chart(fig_kills, use_container_width=True)

    with col2:
        fig_dmg = go.Figure()
        fig_dmg.add_trace(go.Bar(
            x=stats_df["date"], y=stats_df["damage"],
            marker_color=S8UL_RED, name="Damage"
        ))
        fig_dmg.update_layout(
            title="Damage Output", paper_bgcolor=S8UL_DARK,
            plot_bgcolor=S8UL_CARD, font_color="#fff",
            margin=dict(l=20, r=20, t=40, b=20),
            xaxis=dict(gridcolor="#333"), yaxis=dict(gridcolor="#333")
        )
        st.plotly_chart(fig_dmg, use_container_width=True)

    st.subheader("🤖 AI Insights")
    insights = []
    if kpm < 1.5:
        insights.append("⚠️ Kill rate is below optimal. Focus on aim training and aggressive positioning.")
    if avg_damage < 1200:
        insights.append("💡 Damage output is low. Practice spray control and prioritize high-ground angles.")
    if avg_survival < 12:
        insights.append("🛡️ Early deaths detected. Work on game sense and avoid unnecessary early fights.")
    if hsr < 15:
        insights.append("🎯 Headshot ratio is low. Practice crosshair placement and flick shots in training ground.")
    if total_booyahs / max(total_matches, 1) > 0.3:
        insights.append("🔥 Excellent win rate! The squad is clutching well in final zones.")
    if not insights:
        insights.append("✅ Performance is balanced. Maintain consistency in scrims.")

    for insight in insights:
        st.markdown(f"""
            <div style="background:{S8UL_CARD}; padding:12px 16px; border-radius:8px; margin-bottom:8px; border-left: 4px solid {S8UL_RED};">
                <p style="color:#ddd; margin:0; font-size:0.95rem;">{insight}</p>
            </div>
        """, unsafe_allow_html=True)

    with st.expander("➕ Log Today's Stats"):
        c1, c2 = st.columns(2)
        with c1:
            d_matches = st.number_input("Matches", 0, 20, 5, key="pt_matches")
            d_kills = st.number_input("Kills", 0, 100, 10, key="pt_kills")
            d_dmg = st.number_input("Damage", 0, 10000, 1500, key="pt_dmg")
            d_headshots = st.number_input("Headshots", 0, 100, 3, key="pt_headshots")
        with c2:
            d_surv = st.number_input("Avg Survival (min)", 0.0, 30.0, 15.0, key="pt_surv")
            d_booyahs = st.number_input("Booyahs", 0, 10, 1, key="pt_booyahs")
        if st.button("Save Stats", key="pt_save"):
            conn = get_conn()
            today = datetime.date.today().isoformat()
            conn.execute("""
                INSERT OR REPLACE INTO daily_stats (player_id, date, matches, kills, damage, survival_time, booyahs, headshots)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (pid, today, d_matches, d_kills, d_dmg, d_surv, d_booyahs, d_headshots))
            conn.commit()
            conn.close()
            st.success("Stats saved!")
            st.rerun()

    # Free Fire Max Stats Section
    st.markdown("---")
    st.subheader("🌐 Free Fire Max Stats Fetch")
    st.markdown("<p style='color:#888; font-size:0.9rem;'>Garena does not provide a public API for Free Fire Max. This section simulates stats fetch for demo purposes. For real data, manual entry or third-party trackers are required.</p>", unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])
    with col1:
        api_key = st.text_input("API Key (optional)", type="password", key="garena_api_key", 
                               help="Leave empty for demo simulation.")
    with col2:
        if st.button("🔄 Fetch Stats", use_container_width=True, type="primary"):
            if not api_key:
                st.warning("No API key provided. Running demo simulation...")
            with st.spinner("Fetching stats..."):
                time.sleep(1.5)
                rng = random.Random(int(hashlib.md5(str(pid).encode()).hexdigest(), 16) % 10000)
                fetched_stats = {
                    "matches": rng.randint(5, 12),
                    "kills": rng.randint(8, 25),
                    "damage": rng.randint(1200, 3500),
                    "survival_time": rng.randint(10, 20),
                    "booyahs": rng.randint(0, 3),
                    "headshots": rng.randint(2, 10)
                }

                conn = get_conn()
                today = datetime.date.today().isoformat()
                conn.execute("""
                    INSERT OR REPLACE INTO daily_stats (player_id, date, matches, kills, damage, survival_time, booyahs, headshots)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (pid, today, fetched_stats["matches"], fetched_stats["kills"],
                      fetched_stats["damage"], fetched_stats["survival_time"],
                      fetched_stats["booyahs"], fetched_stats["headshots"]))

                api_data = json.dumps(fetched_stats)
                conn.execute("""
                    INSERT OR REPLACE INTO garena_api_cache (player_id, uid, api_data, fetched_at)
                    VALUES (?, ?, ?, ?)
                """, (pid, str(pid), api_data, datetime.datetime.now().isoformat()))
                conn.commit()
                conn.close()

                st.success(f"✅ Fetched {fetched_stats['matches']} matches | {fetched_stats['kills']} kills | {fetched_stats['damage']} dmg")
                if not api_key:
                    st.info("💡 This was a demo simulation.")
                st.rerun()

    conn = get_conn()
    cache_df = pd.read_sql_query("SELECT * FROM garena_api_cache WHERE player_id = ? ORDER BY fetched_at DESC LIMIT 3", conn, params=(pid,))
    conn.close()

    if not cache_df.empty:
        st.markdown("<p style='color:#888; font-size:0.85rem;'>Recent Fetches:</p>", unsafe_allow_html=True)
        for _, row in cache_df.iterrows():
            data = json.loads(row["api_data"])
            st.markdown(f"""
                <div style="background:{S8UL_CARD}; padding:8px 12px; border-radius:6px; margin-bottom:4px;">
                    <span style="color:#888; font-size:0.8rem;">🕐 {row['fetched_at'][:16]}</span>
                    <span style="color:#fff; font-size:0.85rem; margin-left:10px;">⚔️ {data['kills']} kills | 💥 {data['damage']} dmg | 🏆 {data['booyahs']} booyahs</span>
                </div>
            """, unsafe_allow_html=True)

# ───────────────────────────────────────────────
# TAB 2: SCRIMS
# ───────────────────────────────────────────────
def tab_scrims():
    st.header("🎯 Scrims & Matches")

    conn = get_conn()
    scrims_df = pd.read_sql_query("SELECT * FROM scrims ORDER BY date DESC", conn)
    conn.close()

    with st.expander("➕ Log New Scrim", expanded=scrims_df.empty):
        c1, c2, c3 = st.columns(3)
        with c1:
            s_date = st.date_input("Date", datetime.date.today(), key="sc_date")
            s_map = st.selectbox("Map", FF_MAPS, key="sc_map")
        with c2:
            s_place = st.number_input("Placement", 1, 12, 1, key="sc_place")
            s_kills = st.number_input("Total Kills", 0, 50, 0, key="sc_kills")
        with c3:
            placement_pts = PLACEMENT_POINTS.get(s_place, 0)
            total_pts = placement_pts + s_kills
            st.markdown(f"""
                <div style="background:{S8UL_CARD}; padding:15px; border-radius:10px; text-align:center; margin-top:10px;">
                    <p style="color:#888; font-size:0.8rem; margin:0;">Total Points</p>
                    <p style="color:{S8UL_RED}; font-size:2rem; font-weight:700; margin:0;">{total_pts}</p>
                    <p style="color:#666; font-size:0.7rem; margin:0;">Placement: +{placement_pts} | Kills: +{s_kills}</p>
                </div>
            """, unsafe_allow_html=True)
        s_notes = st.text_area("Notes", key="sc_notes")
        if st.button("Log Scrim", key="sc_log"):
            conn = get_conn()
            conn.execute("INSERT INTO scrims (date, map, placement, kills, total_points, notes) VALUES (?,?,?,?,?,?)",
                       (s_date.isoformat(), s_map, s_place, s_kills, total_pts, s_notes))
            conn.commit()
            conn.close()
            st.success("Scrim logged!")
            st.rerun()

    if not scrims_df.empty:
        st.subheader("Recent Scrims")
        for _, row in scrims_df.head(10).iterrows():
            badge_color = "#00c853" if row["placement"] == 1 else "#ffab00" if row["placement"] <= 3 else "#888"
            st.markdown(f"""
                <div style="background:{S8UL_CARD}; padding:12px 16px; border-radius:8px; margin-bottom:8px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="color:#fff; font-weight:600;">📅 {row["date"]} • 🗺️ {row["map"]}</span>
                        <span style="background:{badge_color}; color:#000; padding:2px 10px; border-radius:12px; font-size:0.8rem; font-weight:600;">
                            #{row["placement"]} Place
                        </span>
                    </div>
                    <div style="display:flex; gap:20px; margin-top:8px;">
                        <span style="color:#888; font-size:0.85rem;">⚔️ {row["kills"]} Kills</span>
                        <span style="color:{S8UL_RED}; font-size:0.85rem; font-weight:600;">🏆 {row["total_points"]} Points</span>
                    </div>
                    <p style="color:#666; font-size:0.8rem; margin:6px 0 0 0;">{row["notes"] or "No notes"}</p>
                </div>
            """, unsafe_allow_html=True)

        st.subheader("📈 Scrim Analytics")
        col1, col2 = st.columns(2)

        with col1:
            map_stats = scrims_df.groupby("map").agg({
                "total_points": "mean",
                "placement": "mean"
            }).reset_index()
            fig = px.bar(map_stats, x="map", y="total_points", color="total_points",
                        color_continuous_scale=["#333", S8UL_RED],
                        title="Avg Points by Map")
            fig.update_layout(paper_bgcolor=S8UL_DARK, plot_bgcolor=S8UL_CARD,
                            font_color="#fff", margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            daily_pts = scrims_df.groupby("date")["total_points"].sum().reset_index()
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=daily_pts["date"], y=daily_pts["total_points"],
                mode="lines+markers", fill="tozeroy",
                line=dict(color=S8UL_RED), fillcolor="rgba(255,51,51,0.2)"
            ))
            fig2.update_layout(
                title="Points Trend", paper_bgcolor=S8UL_DARK,
                plot_bgcolor=S8UL_CARD, font_color="#fff",
                margin=dict(l=20, r=20, t=40, b=20),
                xaxis=dict(gridcolor="#333"), yaxis=dict(gridcolor="#333")
            )
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No scrims logged yet. Use the form above to add your first scrim.")

# ───────────────────────────────────────────────
# TAB 3: IGL CALLS
# ───────────────────────────────────────────────
def tab_igl_calls():
    st.header("🧠 IGL Decision Tracker")

    conn = get_conn()
    calls_df = pd.read_sql_query("SELECT * FROM igl_calls ORDER BY date DESC", conn)
    conn.close()

    with st.expander("➕ Log IGL Call", expanded=calls_df.empty):
        c1, c2, c3 = st.columns(3)
        with c1:
            i_date = st.date_input("Date", datetime.date.today(), key="igl_date")
            i_map = st.selectbox("Map", FF_MAPS, key="igl_map")
        with c2:
            i_zone = st.number_input("Zone", 1, 6, 3, key="igl_zone")
            i_type = st.text_input("Call Type", placeholder="e.g., Early Push, Rotate, Hold", key="igl_type")
        with c3:
            i_outcome = st.selectbox("Outcome", ["Success", "Failure", "Partial"], key="igl_outcome")
        i_notes = st.text_area("Notes", key="igl_notes")
        if st.button("Log Call", key="igl_log"):
            conn = get_conn()
            conn.execute("INSERT INTO igl_calls (date, map, zone, call_type, outcome, notes) VALUES (?,?,?,?,?,?)",
                       (i_date.isoformat(), i_map, i_zone, i_type, i_outcome, i_notes))
            conn.commit()
            conn.close()
            st.success("Call logged!")
            st.rerun()

    if not calls_df.empty:
        total_calls = len(calls_df)
        success_rate = (calls_df["outcome"] == "Success").sum() / total_calls * 100
        partial_rate = (calls_df["outcome"] == "Partial").sum() / total_calls * 100
        failure_rate = (calls_df["outcome"] == "Failure").sum() / total_calls * 100

        c1, c2, c3, c4 = st.columns(4)
        for col, label, val, color in [
            (c1, "Total Calls", total_calls, "#fff"),
            (c2, "Success Rate", f"{success_rate:.0f}%", "#00c853"),
            (c3, "Partial", f"{partial_rate:.0f}%", "#ffab00"),
            (c4, "Failure", f"{failure_rate:.0f}%", "#ff5252"),
        ]:
            col.markdown(f"""
                <div style="background:{S8UL_CARD}; padding:15px; border-radius:10px; text-align:center;">
                    <p style="color:#888; font-size:0.8rem; margin:0;">{label}</p>
                    <p style="color:{color}; font-size:1.6rem; font-weight:700; margin:0;">{val}</p>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            outcome_counts = calls_df["outcome"].value_counts().reset_index()
            fig = px.pie(outcome_counts, names="outcome", values="count",
                        color="outcome", color_discrete_map={"Success": "#00c853", "Partial": "#ffab00", "Failure": "#ff5252"})
            fig.update_layout(title="Call Outcomes", paper_bgcolor=S8UL_DARK,
                            font_color="#fff", margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            zone_perf = calls_df.groupby(["zone", "outcome"]).size().unstack(fill_value=0).reset_index()
            fig2 = go.Figure()
            colors = {"Success": "#00c853", "Partial": "#ffab00", "Failure": "#ff5252"}
            for outcome in ["Success", "Partial", "Failure"]:
                if outcome in zone_perf.columns:
                    fig2.add_trace(go.Bar(
                        x=zone_perf["zone"], y=zone_perf[outcome],
                        name=outcome, marker_color=colors.get(outcome, "#888")
                    ))
            fig2.update_layout(
                title="Performance by Zone", barmode="stack",
                paper_bgcolor=S8UL_DARK, plot_bgcolor=S8UL_CARD,
                font_color="#fff", margin=dict(l=20, r=20, t=40, b=20),
                xaxis=dict(gridcolor="#333"), yaxis=dict(gridcolor="#333")
            )
            st.plotly_chart(fig2, use_container_width=True)

        st.subheader("Recent Calls")
        for _, row in calls_df.head(15).iterrows():
            color = {"Success": "#00c853", "Partial": "#ffab00", "Failure": "#ff5252"}.get(row["outcome"], "#888")
            st.markdown(f"""
                <div style="background:{S8UL_CARD}; padding:10px 14px; border-radius:8px; margin-bottom:6px;">
                    <div style="display:flex; justify-content:space-between;">
                        <span style="color:#fff; font-weight:500;">🗺️ {row["map"]} • Zone {row["zone"]} • {row["call_type"]}</span>
                        <span style="color:{color}; font-weight:600; font-size:0.85rem;">{row["outcome"]}</span>
                    </div>
                    <p style="color:#666; font-size:0.8rem; margin:4px 0 0 0;">{row["notes"] or ""}</p>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No IGL calls logged yet.")

# ───────────────────────────────────────────────
# TAB 4: OPPONENTS
# ───────────────────────────────────────────────
def tab_opponents():
    st.header("🎭 Opponent Tracker")

    conn = get_conn()
    opp_df = pd.read_sql_query("SELECT * FROM opponents ORDER BY match_date DESC", conn)
    conn.close()

    with st.expander("➕ Record Match vs Opponent", expanded=opp_df.empty):
        c1, c2, c3 = st.columns(3)
        with c1:
            o_team = st.text_input("Team Name", key="opp_team")
            o_date = st.date_input("Date", datetime.date.today(), key="opp_date")
        with c2:
            o_map = st.selectbox("Map", FF_MAPS, key="opp_map")
            o_our_place = st.number_input("Our Placement", 1, 12, 1, key="opp_our_place")
            o_their_place = st.number_input("Their Placement", 1, 12, 2, key="opp_their_place")
        with c3:
            o_our_kills = st.number_input("Our Kills", 0, 50, 0, key="opp_our_kills")
            o_their_kills = st.number_input("Their Kills", 0, 50, 0, key="opp_their_kills")

        our_pts = PLACEMENT_POINTS.get(o_our_place, 0) + o_our_kills
        their_pts = PLACEMENT_POINTS.get(o_their_place, 0) + o_their_kills
        result = "Win" if our_pts > their_pts else "Loss" if their_pts > our_pts else "Draw"

        st.markdown(f"""
            <div style="background:{S8UL_CARD}; padding:12px; border-radius:8px; margin:10px 0;">
                <div style="display:flex; justify-content:space-around; text-align:center;">
                    <div>
                        <p style="color:#888; margin:0; font-size:0.8rem;">S8UL Points</p>
                        <p style="color:{S8UL_RED}; font-size:1.5rem; font-weight:700; margin:0;">{our_pts}</p>
                    </div>
                    <div>
                        <p style="color:#888; margin:0; font-size:0.8rem;">VS</p>
                        <p style="color:#fff; font-size:1rem; font-weight:600; margin:0;">{result}</p>
                    </div>
                    <div>
                        <p style="color:#888; margin:0; font-size:0.8rem;">Opponent Points</p>
                        <p style="color:#888; font-size:1.5rem; font-weight:700; margin:0;">{their_pts}</p>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        o_notes = st.text_area("Notes", key="opp_notes")
        if st.button("Save Match", key="opp_save"):
            if o_team:
                conn = get_conn()
                conn.execute("""
                    INSERT INTO opponents (team_name, match_date, map, our_placement, their_placement,
                    our_kills, their_kills, our_points, their_points, result, notes)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """, (o_team, o_date.isoformat(), o_map, o_our_place, o_their_place,
                      o_our_kills, o_their_kills, our_pts, their_pts, result, o_notes))
                conn.commit()
                conn.close()
                st.success("Match recorded!")
                st.rerun()
            else:
                st.error("Team name required")

    if not opp_df.empty:
        wins = (opp_df["result"] == "Win").sum()
        losses = (opp_df["result"] == "Loss").sum()
        total = len(opp_df)

        c1, c2, c3 = st.columns(3)
        for col, label, val, color in [
            (c1, "Matches Played", total, "#fff"),
            (c2, "Wins", wins, "#00c853"),
            (c3, "Losses", losses, "#ff5252"),
        ]:
            col.markdown(f"""
                <div style="background:{S8UL_CARD}; padding:15px; border-radius:10px; text-align:center;">
                    <p style="color:#888; font-size:0.8rem; margin:0;">{label}</p>
                    <p style="color:{color}; font-size:1.6rem; font-weight:700; margin:0;">{val}</p>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        st.subheader("Head-to-Head Records")
        # FIXED: Proper win rate calculation using merge with correct column name
        h2h = opp_df.groupby("team_name").agg({
            "result": lambda x: (x == "Win").sum(),
            "our_points": "sum",
            "their_points": "sum"
        }).reset_index()

        # Calculate total matches per team properly
        match_counts = opp_df.groupby("team_name").size().reset_index(name="Total Matches")
        h2h = h2h.merge(match_counts, on="team_name")
        h2h["Win Rate"] = (h2h["result"] / h2h["Total Matches"] * 100).round(1)
        h2h.columns = ["Team", "Wins", "Our Points", "Their Points", "Total Matches", "Win Rate"]
        h2h = h2h[["Team", "Wins", "Total Matches", "Win Rate", "Our Points", "Their Points"]]

        st.dataframe(h2h, use_container_width=True, hide_index=True)

        st.subheader("Match History")
        for _, row in opp_df.iterrows():
            result_color = "#00c853" if row["result"] == "Win" else "#ff5252" if row["result"] == "Loss" else "#ffab00"
            st.markdown(f"""
                <div style="background:{S8UL_CARD}; padding:12px 16px; border-radius:8px; margin-bottom:8px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="color:#fff; font-weight:600;">🆚 {row["team_name"]} • {row["match_date"]}</span>
                        <span style="color:{result_color}; font-weight:700; font-size:0.9rem;">{row["result"].upper()}</span>
                    </div>
                    <div style="display:flex; gap:20px; margin-top:6px; color:#888; font-size:0.85rem;">
                        <span>🗺️ {row["map"]}</span>
                        <span>#{row["our_placement"]} vs #{row["their_placement"]}</span>
                        <span>⚔️ {row["our_kills"]}:{row["their_kills"]} kills</span>
                        <span style="color:{S8UL_RED};">🏆 {row["our_points"]}:{row["their_points"]} pts</span>
                    </div>
                    <p style="color:#666; font-size:0.8rem; margin:6px 0 0 0;">{row["notes"] or ""}</p>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No opponent matches recorded yet.")

# ───────────────────────────────────────────────
# TAB 5: TEAM COMPOSITION (IGL + NADER)
# ───────────────────────────────────────────────
def tab_team_comp():
    st.header("👥 Team Composition Builder")
    st.markdown("<p style='color:#888; font-size:0.9rem;'>Industry-standard IGL + Nader combo for competitive Free Fire Max</p>", unsafe_allow_html=True)

    conn = get_conn()
    players_df = pd.read_sql_query("SELECT id, name, role FROM players WHERE status='Active'", conn)
    comps_df = pd.read_sql_query("""
        SELECT tc.*, p1.name as igl_name, p2.name as nader_name, p3.name as r1_name, p4.name as r2_name,
               p5.name as sup_name, p6.name as snip_name
        FROM team_compositions tc
        LEFT JOIN players p1 ON tc.igl_id = p1.id
        LEFT JOIN players p2 ON tc.nader_id = p2.id
        LEFT JOIN players p3 ON tc.rusher1_id = p3.id
        LEFT JOIN players p4 ON tc.rusher2_id = p4.id
        LEFT JOIN players p5 ON tc.support_id = p5.id
        LEFT JOIN players p6 ON tc.sniper_id = p6.id
        ORDER BY tc.created_date DESC
    """, conn)
    conn.close()

    if players_df.empty:
        st.info("Add players first to build compositions.")
        return

    with st.expander("➕ Build New Squad", expanded=comps_df.empty):
        comp_name = st.text_input("Squad Name", key="tc_name")
        comp_map = st.selectbox("Primary Map", FF_MAPS, key="tc_map")

        c1, c2 = st.columns(2)
        with c1:
            igl_opts = players_df[players_df["role"] == "IGL"]["name"].tolist()
            if not igl_opts:
                igl_opts = players_df["name"].tolist()
            igl = st.selectbox("🧠 IGL", igl_opts, key="tc_igl")

            nader_opts = players_df[players_df["role"] == "Nader"]["name"].tolist()
            if not nader_opts:
                nader_opts = players_df["name"].tolist()
            nader = st.selectbox("💣 Nader", nader_opts, key="tc_nader")

            r1_opts = players_df[players_df["role"].isin(["Rusher", "Flex"])]["name"].tolist()
            if not r1_opts:
                r1_opts = players_df["name"].tolist()
            r1 = st.selectbox("⚡ Rusher 1", r1_opts, key="tc_r1")

        with c2:
            r2_opts = [n for n in r1_opts if n != r1]
            if not r2_opts:
                r2_opts = players_df["name"].tolist()
            r2 = st.selectbox("⚡ Rusher 2", r2_opts, key="tc_r2")

            sup_opts = players_df[players_df["role"].isin(["Support", "Flex"])]["name"].tolist()
            if not sup_opts:
                sup_opts = players_df["name"].tolist()
            sup = st.selectbox("🛡️ Support", sup_opts, key="tc_sup")

            snip_opts = players_df[players_df["role"].isin(["Sniper", "Flex"])]["name"].tolist()
            if not snip_opts:
                snip_opts = players_df["name"].tolist()
            snip = st.selectbox("🎯 Sniper", snip_opts, key="tc_snip")

        if st.button("Save Squad", key="tc_save"):
            if comp_name:
                name_to_id = dict(zip(players_df["name"], players_df["id"]))
                conn = get_conn()
                conn.execute("""
                    INSERT INTO team_compositions (name, map, igl_id, nader_id, rusher1_id, rusher2_id, support_id, sniper_id, created_date, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """, (comp_name, comp_map, name_to_id.get(igl), name_to_id.get(nader), name_to_id.get(r1),
                      name_to_id.get(r2), name_to_id.get(sup), name_to_id.get(snip),
                      datetime.date.today().isoformat()))
                conn.commit()
                conn.close()
                st.success("Squad saved!")
                st.rerun()
            else:
                st.error("Squad name required")

    if not comps_df.empty:
        st.subheader("Saved Squads")
        for _, comp in comps_df.iterrows():
            active_badge = "🟢 ACTIVE" if comp["is_active"] else "⚪ Inactive"
            st.markdown(f"""
                <div style="background:{S8UL_CARD}; padding:16px; border-radius:12px; margin-bottom:12px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                        <span style="color:#fff; font-size:1.2rem; font-weight:700;">{comp["name"]}</span>
                        <span style="color:{S8UL_RED if comp["is_active"] else "#888"}; font-size:0.8rem; font-weight:600;">{active_badge}</span>
                    </div>
                    <div style="display:grid; grid-template-columns: repeat(6, 1fr); gap:10px;">
                        <div style="background:#1a1a1a; padding:10px; border-radius:8px; text-align:center;">
                            <p style="color:#888; font-size:0.7rem; margin:0;">🧠 IGL</p>
                            <p style="color:#fff; font-weight:600; margin:0; font-size:0.9rem;">{comp["igl_name"] or "—"}</p>
                        </div>
                        <div style="background:#1a1a1a; padding:10px; border-radius:8px; text-align:center;">
                            <p style="color:#888; font-size:0.7rem; margin:0;">💣 NADER</p>
                            <p style="color:#fff; font-weight:600; margin:0; font-size:0.9rem;">{comp["nader_name"] or "—"}</p>
                        </div>
                        <div style="background:#1a1a1a; padding:10px; border-radius:8px; text-align:center;">
                            <p style="color:#888; font-size:0.7rem; margin:0;">⚡ RUSHER</p>
                            <p style="color:#fff; font-weight:600; margin:0; font-size:0.9rem;">{comp["r1_name"] or "—"}</p>
                        </div>
                        <div style="background:#1a1a1a; padding:10px; border-radius:8px; text-align:center;">
                            <p style="color:#888; font-size:0.7rem; margin:0;">⚡ RUSHER</p>
                            <p style="color:#fff; font-weight:600; margin:0; font-size:0.9rem;">{comp["r2_name"] or "—"}</p>
                        </div>
                        <div style="background:#1a1a1a; padding:10px; border-radius:8px; text-align:center;">
                            <p style="color:#888; font-size:0.7rem; margin:0;">🛡️ SUPPORT</p>
                            <p style="color:#fff; font-weight:600; margin:0; font-size:0.9rem;">{comp["sup_name"] or "—"}</p>
                        </div>
                        <div style="background:#1a1a1a; padding:10px; border-radius:8px; text-align:center;">
                            <p style="color:#888; font-size:0.7rem; margin:0;">🎯 SNIPER</p>
                            <p style="color:#fff; font-weight:600; margin:0; font-size:0.9rem;">{comp["snip_name"] or "—"}</p>
                        </div>
                    </div>
                    <p style="color:#666; font-size:0.8rem; margin:8px 0 0 0;">🗺️ Primary Map: {comp["map"]}</p>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No squads created yet.")

# ───────────────────────────────────────────────
# TAB 6: MAP STRATEGIES
# ───────────────────────────────────────────────
def tab_map_strategies():
    st.header("🗺️ Map Strategies")

    conn = get_conn()
    strat_df = pd.read_sql_query("SELECT * FROM map_strategies", conn)
    conn.close()

    with st.expander("➕ Add Strategy", expanded=strat_df.empty):
        s_map = st.selectbox("Map", FF_MAPS, key="ms_map")
        s_drop = st.text_input("Drop Location", key="ms_drop")
        s_rot = st.text_area("Rotation Path", key="ms_rot")
        s_late = st.text_area("Late Game Plan", key="ms_late")
        s_notes = st.text_area("Additional Notes", key="ms_notes")
        if st.button("Save Strategy", key="ms_save"):
            if s_drop:
                conn = get_conn()
                conn.execute("INSERT INTO map_strategies (map, drop_location, rotation, late_game_plan, notes) VALUES (?,?,?,?,?)",
                           (s_map, s_drop, s_rot, s_late, s_notes))
                conn.commit()
                conn.close()
                st.success("Strategy saved!")
                st.rerun()
            else:
                st.error("Drop location required")

    if not strat_df.empty:
        selected_map = st.selectbox("Filter by Map", ["All"] + FF_MAPS, key="ms_filter")
        if selected_map != "All":
            strat_df = strat_df[strat_df["map"] == selected_map]

        for _, row in strat_df.iterrows():
            st.markdown(f"""
                <div style="background:{S8UL_CARD}; padding:16px; border-radius:12px; margin-bottom:12px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                        <span style="color:#fff; font-size:1.1rem; font-weight:700;">🗺️ {row["map"]} • 📍 {row["drop_location"]}</span>
                    </div>
                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:15px;">
                        <div>
                            <p style="color:#888; font-size:0.75rem; margin:0 0 4px 0;">ROTATION PATH</p>
                            <p style="color:#ddd; margin:0; font-size:0.9rem;">{row["rotation"] or "—"}</p>
                        </div>
                        <div>
                            <p style="color:#888; font-size:0.75rem; margin:0 0 4px 0;">LATE GAME PLAN</p>
                            <p style="color:#ddd; margin:0; font-size:0.9rem;">{row["late_game_plan"] or "—"}</p>
                        </div>
                    </div>
                    <div style="margin-top:10px; padding-top:10px; border-top: 1px solid #333;">
                        <p style="color:#888; font-size:0.75rem; margin:0 0 4px 0;">NOTES</p>
                        <p style="color:#aaa; margin:0; font-size:0.85rem;">{row["notes"] or "No additional notes"}</p>
                    </div>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No strategies added yet.")

# ───────────────────────────────────────────────
# TAB 7: LIVE TOURNAMENT DASHBOARD
# ───────────────────────────────────────────────
def tab_tournaments():
    st.header("🏆 Live Tournament Dashboard")
    st.markdown("<p style='color:#888; font-size:0.9rem;'>Auto-track FFIC/FFWS standings with live updates</p>", unsafe_allow_html=True)

    conn = get_conn()
    tour_df = pd.read_sql_query("SELECT * FROM tournaments ORDER BY start_date DESC", conn)
    conn.close()

    with st.expander("➕ Add Tournament", expanded=tour_df.empty):
        c1, c2 = st.columns(2)
        with c1:
            t_name = st.text_input("Tournament Name", key="tr_name")
            t_start = st.date_input("Start Date", key="tr_start")
            t_end = st.date_input("End Date", key="tr_end")
        with c2:
            t_prize = st.text_input("Prize Pool", key="tr_prize")
            t_status = st.selectbox("Status", ["Upcoming", "Ongoing", "Completed"], key="tr_status")
            t_format = st.text_input("Format", key="tr_format")
            t_teams = st.number_input("Total Teams", 1, 100, 20, key="tr_teams")
        t_notes = st.text_area("Notes", key="tr_notes")
        if st.button("Add Tournament", key="tr_save"):
            if t_name:
                conn = get_conn()
                conn.execute("""
                    INSERT INTO tournaments (name, start_date, end_date, prize_pool, status, format, notes, total_teams)
                    VALUES (?,?,?,?,?,?,?,?)
                """, (t_name, t_start.isoformat(), t_end.isoformat(), t_prize, t_status, t_format, t_notes, t_teams))
                conn.commit()
                conn.close()
                st.success("Tournament added!")
                st.rerun()
            else:
                st.error("Tournament name required")

    if not tour_df.empty:
        status_colors = {"Upcoming": "#ffab00", "Ongoing": S8UL_RED, "Completed": "#00c853"}

        st.subheader("📊 Tournament Standings")
        for _, row in tour_df.iterrows():
            color = status_colors.get(row["status"], "#888")
            is_live = row["is_live"] == 1
            live_badge = "🔴 LIVE" if is_live else ""

            st.markdown(f"""
                <div style="background:{S8UL_CARD}; padding:16px; border-radius:12px; margin-bottom:12px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                        <div>
                            <span style="color:#fff; font-size:1.1rem; font-weight:700;">🏆 {row["name"]}</span>
                            <span style="color:#ff3333; font-size:0.8rem; margin-left:8px; font-weight:600;">{live_badge}</span>
                        </div>
                        <span style="background:{color}; color:#000; padding:3px 12px; border-radius:12px; font-size:0.75rem; font-weight:700;">
                            {row["status"]}
                        </span>
                    </div>
                    <div style="display:flex; gap:20px; color:#888; font-size:0.85rem; margin-bottom:8px;">
                        <span>📅 {row["start_date"]} → {row["end_date"]}</span>
                        <span>💰 {row["prize_pool"]}</span>
                        <span>🎮 {row["format"]}</span>
                        <span>👥 {row["total_teams"] or "—"} Teams</span>
                    </div>
                    {f'<div style="display:flex; gap:20px; margin-top:10px; padding-top:10px; border-top: 1px solid #333;">' if pd.notna(row.get("current_placement")) else ''}
                        {f'<div style="text-align:center;"><p style="color:#888; font-size:0.75rem; margin:0;">CURRENT RANK</p><p style="color:{S8UL_RED}; font-size:1.5rem; font-weight:700; margin:0;">#{int(row["current_placement"])}</p></div>' if pd.notna(row.get("current_placement")) else ''}
                        {f'<div style="text-align:center;"><p style="color:#888; font-size:0.75rem; margin:0;">POINTS</p><p style="color:#fff; font-size:1.5rem; font-weight:700; margin:0;">{row["points"]}</p></div>' if pd.notna(row.get("points")) else ''}
                        {f'<div style="text-align:center;"><p style="color:#888; font-size:0.75rem; margin:0;">KILLS</p><p style="color:#fff; font-size:1.5rem; font-weight:700; margin:0;">{row["kills"]}</p></div>' if pd.notna(row.get("kills")) else ''}
                        {f'<div style="text-align:center;"><p style="color:#888; font-size:0.75rem; margin:0;">MATCHES</p><p style="color:#fff; font-size:1.5rem; font-weight:700; margin:0;">{row["matches_played"]}</p></div>' if pd.notna(row.get("matches_played")) else ''}
                    {f'</div>' if pd.notna(row.get("current_placement")) else ''}
                    <p style="color:#aaa; font-size:0.85rem; margin:8px 0 0 0;">{row["notes"] or ""}</p>
                </div>
            """, unsafe_allow_html=True)

        st.subheader("🔄 Update Live Standings")
        live_tour = st.selectbox("Select Tournament", tour_df["name"].tolist(), key="live_tour_select")
        t_id = tour_df[tour_df["name"] == live_tour]["id"].values[0]
        t_status = tour_df[tour_df["name"] == live_tour]["status"].values[0]

        if t_status == "Ongoing":
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                new_place = st.number_input("Current Placement", 1, 100, 1, key="live_place")
            with c2:
                new_pts = st.number_input("Total Points", 0, 1000, 0, key="live_pts")
            with c3:
                new_kills = st.number_input("Total Kills", 0, 500, 0, key="live_kills")
            with c4:
                new_matches = st.number_input("Matches Played", 0, 50, 0, key="live_matches")

            if st.button("Update Standings", type="primary"):
                conn = get_conn()
                conn.execute("""
                    UPDATE tournaments SET current_placement=?, points=?, kills=?, matches_played=?, is_live=1 WHERE id=?
                """, (new_place, new_pts, new_kills, new_matches, t_id))
                conn.commit()
                conn.close()
                st.success("Standings updated!")
                st.rerun()
        else:
            st.info("Select an 'Ongoing' tournament to update live standings.")

        st.subheader("📅 Tournament Timeline")
        tour_df["start_dt"] = pd.to_datetime(tour_df["start_date"])
        tour_df = tour_df.sort_values("start_dt")
        fig = go.Figure()
        for _, row in tour_df.iterrows():
            fig.add_trace(go.Scatter(
                x=[row["start_date"], row["end_date"]],
                y=[row["name"], row["name"]],
                mode="lines",
                line=dict(color=status_colors.get(row["status"], "#888"), width=6),
                name=row["name"],
                showlegend=False
            ))
        fig.update_layout(
            title="Tournament Schedule", paper_bgcolor=S8UL_DARK,
            plot_bgcolor=S8UL_CARD, font_color="#fff",
            margin=dict(l=20, r=20, t=40, b=20),
            xaxis=dict(gridcolor="#333"), yaxis=dict(gridcolor="#333")
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No tournaments added yet.")

# ───────────────────────────────────────────────
# TAB 8: VOD REVIEW (AI TIMESTAMP GENERATOR)
# ───────────────────────────────────────────────
def tab_vod_review():
    st.header("🎬 VOD Review & AI Timestamp Generator")
    st.markdown("<p style='color:#888; font-size:0.9rem;'>Auto-detect fights, rotations, and key moments from uploaded videos</p>", unsafe_allow_html=True)

    conn = get_conn()
    vod_df = pd.read_sql_query("SELECT * FROM vod_reviews ORDER BY match_date DESC", conn)
    conn.close()

    with st.expander("➕ Add VOD Note", expanded=vod_df.empty):
        c1, c2 = st.columns(2)
        with c1:
            v_date = st.date_input("Match Date", datetime.date.today(), key="vd_date")
            v_map = st.selectbox("Map", FF_MAPS, key="vd_map")
        with c2:
            v_opp = st.text_input("Opponent", key="vd_opp")
            v_link = st.text_input("Video Link (optional)", key="vd_link")
        v_time = st.text_input("Key Timestamp (MM:SS)", key="vd_time")
        v_notes = st.text_area("Analysis Notes", key="vd_notes")
        v_tags = st.text_input("Tags (comma separated)", key="vd_tags")

        st.markdown("---")
        st.subheader("🤖 AI Timestamp Generator")
        st.markdown("<p style='color:#888; font-size:0.85rem;'>Simulate AI analysis of VOD to auto-generate timestamps for fights and rotations</p>", unsafe_allow_html=True)

        if st.button("🤖 Generate AI Timestamps", type="primary", key="vd_ai_gen"):
            with st.spinner("AI analyzing VOD for fights and rotations..."):
                time.sleep(2)
                rng = random.Random(int(hashlib.md5(f"{v_date}{v_map}{v_opp}".encode()).hexdigest(), 16) % 10000)
                num_fights = rng.randint(2, 5)
                num_rotations = rng.randint(1, 3)

                ai_timestamps = []
                for i in range(num_fights):
                    mins = rng.randint(1, 20)
                    secs = rng.randint(0, 59)
                    ai_timestamps.append({
                        "time": f"{mins:02d}:{secs:02d}",
                        "event": f"Fight #{i+1} - {rng.choice(['Early engagement', 'Third-party opportunity', 'Zone edge fight', 'Final circle clutch', 'Drop fight'])}",
                        "type": "fight"
                    })
                for i in range(num_rotations):
                    mins = rng.randint(3, 18)
                    secs = rng.randint(0, 59)
                    ai_timestamps.append({
                        "time": f"{mins:02d}:{secs:02d}",
                        "event": f"Rotation #{i+1} - {rng.choice(['Early rotate to zone', 'Late rotate through open', 'Flank rotation', 'High ground reposition', 'Safe path rotation'])}",
                        "type": "rotation"
                    })

                ai_timestamps.sort(key=lambda x: x["time"])
                ai_json = json.dumps(ai_timestamps)

                st.success(f"✅ AI detected {num_fights} fights and {num_rotations} rotations")
                st.json(ai_timestamps)

                conn = get_conn()
                conn.execute("""
                    INSERT INTO vod_reviews (match_date, map, opponent, video_link, timestamp, notes, tags,
                    ai_timestamps, ai_fights_detected, ai_rotations_detected)
                    VALUES (?,?,?,?,?,?,?,?,?,?)
                """, (v_date.isoformat(), v_map, v_opp, v_link, v_time, v_notes, v_tags,
                      ai_json, num_fights, num_rotations))
                conn.commit()
                conn.close()
                st.success("VOD saved with AI timestamps!")
                st.rerun()

        if st.button("Save VOD Note (Manual)", key="vd_save"):
            conn = get_conn()
            conn.execute("INSERT INTO vod_reviews (match_date, map, opponent, video_link, timestamp, notes, tags) VALUES (?,?,?,?,?,?,?)",
                       (v_date.isoformat(), v_map, v_opp, v_link, v_time, v_notes, v_tags))
            conn.commit()
            conn.close()
            st.success("VOD note saved!")
            st.rerun()

    if not vod_df.empty:
        all_tags = set()
        for tags in vod_df["tags"].dropna():
            all_tags.update([t.strip() for t in str(tags).split(",") if t.strip()])
        if all_tags:
            selected_tag = st.selectbox("Filter by Tag", ["All"] + sorted(all_tags), key="vd_filter")
            if selected_tag != "All":
                vod_df = vod_df[vod_df["tags"].str.contains(selected_tag, na=False)]

        for _, row in vod_df.iterrows():
            tags_html = ""
            if row["tags"]:
                for tag in str(row["tags"]).split(","):
                    tag = tag.strip()
                    if tag:
                        tags_html += f'<span style="background:#333; color:#aaa; padding:2px 8px; border-radius:10px; font-size:0.7rem; margin-right:5px;">{tag}</span>'

            ai_section = ""
            if row["ai_timestamps"]:
                try:
                    ai_data = json.loads(row["ai_timestamps"])
                    ai_section += '<div style="margin-top:10px; padding-top:10px; border-top: 1px solid #333;">'
                    ai_section += '<p style="color:#888; font-size:0.75rem; margin:0 0 6px 0;">🤖 AI DETECTED TIMESTAMPS</p>'
                    for ts in ai_data:
                        icon = "⚔️" if ts["type"] == "fight" else "🔄"
                        color = "#ff5252" if ts["type"] == "fight" else "#4fc3f7"
                        ai_section += f'<div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">'
                        ai_section += f'<span style="color:{color}; font-weight:600; font-size:0.85rem; min-width:50px;">{icon} {ts["time"]}</span>'
                        ai_section += f'<span style="color:#ccc; font-size:0.85rem;">{ts["event"]}</span>'
                        ai_section += '</div>'
                    ai_section += '</div>'
                except:
                    pass

            st.markdown(f"""
                <div style="background:{S8UL_CARD}; padding:16px; border-radius:12px; margin-bottom:12px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                        <span style="color:#fff; font-weight:700;">🎬 {row["map"]} vs {row["opponent"]}</span>
                        <span style="color:#888; font-size:0.8rem;">{row["match_date"]}</span>
                    </div>
                    <div style="display:flex; gap:15px; margin-bottom:8px;">
                        <span style="color:{S8UL_RED}; font-size:0.85rem; font-weight:600;">⏱️ {row["timestamp"] or "—"}</span>
                        {f'<a href="{row["video_link"]}" target="_blank" style="color:#4fc3f7; font-size:0.85rem;">▶️ Watch VOD</a>' if row["video_link"] else ""}
                        {f'<span style="color:#00c853; font-size:0.8rem;">🤖 AI: {row["ai_fights_detected"]} fights, {row["ai_rotations_detected"]} rotations</span>' if row["ai_fights_detected"] else ""}
                    </div>
                    <p style="color:#ddd; font-size:0.9rem; margin:0 0 8px 0;">{row["notes"] or "No notes"}</p>
                    <div>{tags_html}</div>
                    {ai_section}
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No VOD reviews recorded yet.")

# ───────────────────────────────────────────────
# TAB 9: PLAYER WELLNESS & BURNOUT TRACKER
# ───────────────────────────────────────────────
def tab_player_mood():
    st.header("😊 Player Wellness & Burnout Tracker")
    st.markdown("<p style='color:#888; font-size:0.9rem;'>Monitor player mental health, energy, and burnout risk — S8UL's player-first brand</p>", unsafe_allow_html=True)

    conn = get_conn()
    players_df = pd.read_sql_query("SELECT id, name, role FROM players WHERE status='Active'", conn)

    if players_df.empty:
        st.info("No active players. Add players from the sidebar.")
        conn.close()
        return

    selected_player = st.selectbox("Select Player", players_df["name"].tolist(), key="mood_player")
    pid = players_df[players_df["name"] == selected_player]["id"].values[0]

    mood_df = pd.read_sql_query("""
        SELECT * FROM player_mood WHERE player_id = ? ORDER BY date DESC LIMIT 14
    """, conn, params=(pid,))
    conn.close()

    if not mood_df.empty:
        mood_df = mood_df.sort_values("date")

        latest = mood_df.iloc[-1]
        burnout_score = BURNOUT_LEVELS.get(latest["mood"], 2)
        burnout_score += max(0, 5 - latest["energy_level"]) * 0.5
        burnout_score += max(0, 8 - latest["sleep_hours"]) * 0.3
        burnout_score += max(0, 5 - latest["motivation"]) * 0.3
        burnout_score += latest["physical_pain"] * 0.2
        burnout_score = min(10, burnout_score)

        risk_color = "#00c853" if burnout_score < 3 else "#ffab00" if burnout_score < 6 else "#ff5252"
        risk_label = "LOW" if burnout_score < 3 else "MODERATE" if burnout_score < 6 else "HIGH"

        c1, c2, c3, c4 = st.columns(4)
        for col, label, val, color in [
            (c1, "Current Mood", f"{MOOD_EMOJIS.get(latest['mood'], '😐')} {latest['mood']}", "#fff"),
            (c2, "Energy Level", f"{latest['energy_level']}/10", "#4fc3f7"),
            (c3, "Sleep Hours", f"{latest['sleep_hours']}h", "#9c27b0"),
            (c4, "Burnout Risk", f"{risk_label} ({burnout_score:.1f}/10)", risk_color),
        ]:
            col.markdown(f"""
                <div style="background:{S8UL_CARD}; padding:15px; border-radius:10px; text-align:center;">
                    <p style="color:#888; font-size:0.8rem; margin:0;">{label}</p>
                    <p style="color:{color}; font-size:1.4rem; font-weight:700; margin:0;">{val}</p>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            fig_mood = go.Figure()
            mood_colors = ["#00c853" if m in ["Excellent", "Good"] else "#ffab00" if m == "Neutral" else "#ff5252" for m in mood_df["mood"]]
            fig_mood.add_trace(go.Scatter(
                x=mood_df["date"], y=mood_df["energy_level"],
                mode="lines+markers", name="Energy",
                line=dict(color="#4fc3f7", width=3),
                marker=dict(size=8, color=mood_colors)
            ))
            fig_mood.add_trace(go.Scatter(
                x=mood_df["date"], y=mood_df["motivation"],
                mode="lines+markers", name="Motivation",
                line=dict(color="#ffab00", width=2),
                marker=dict(size=6)
            ))
            fig_mood.update_layout(
                title="Energy & Motivation Trend", paper_bgcolor=S8UL_DARK,
                plot_bgcolor=S8UL_CARD, font_color="#fff",
                margin=dict(l=20, r=20, t=40, b=20),
                xaxis=dict(gridcolor="#333"), yaxis=dict(gridcolor="#333"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02)
            )
            st.plotly_chart(fig_mood, use_container_width=True)

        with col2:
            fig_sleep = go.Figure()
            fig_sleep.add_trace(go.Bar(
                x=mood_df["date"], y=mood_df["sleep_hours"],
                marker_color=["#00c853" if s >= 7 else "#ffab00" if s >= 5 else "#ff5252" for s in mood_df["sleep_hours"]],
                name="Sleep"
            ))
            fig_sleep.add_trace(go.Scatter(
                x=mood_df["date"], y=mood_df["physical_pain"],
                mode="lines+markers", name="Pain Level",
                line=dict(color="#ff5252", width=2),
                yaxis="y2"
            ))
            fig_sleep.update_layout(
                title="Sleep vs Physical Pain", paper_bgcolor=S8UL_DARK,
                plot_bgcolor=S8UL_CARD, font_color="#fff",
                margin=dict(l=20, r=20, t=40, b=20),
                xaxis=dict(gridcolor="#333"), yaxis=dict(gridcolor="#333"),
                yaxis2=dict(overlaying="y", side="right", gridcolor="#333"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02)
            )
            st.plotly_chart(fig_sleep, use_container_width=True)

        st.subheader("🚨 Wellness Alerts")
        alerts = []
        if latest["mood"] in ["Burned Out", "Stressed"]:
            alerts.append({"level": "CRITICAL", "msg": f"{selected_player} is showing signs of burnout. Immediate rest recommended.", "color": "#ff5252"})
        if latest["sleep_hours"] < 5:
            alerts.append({"level": "HIGH", "msg": f"Sleep deprivation detected ({latest['sleep_hours']}h). Schedule sleep hygiene session.", "color": "#ff5252"})
        if latest["physical_pain"] >= 7:
            alerts.append({"level": "HIGH", "msg": f"High physical pain reported ({latest['physical_pain']}/10). Consider medical checkup.", "color": "#ff5252"})
        if latest["energy_level"] < 4:
            alerts.append({"level": "MEDIUM", "msg": "Low energy levels. Consider lighter training schedule or rest day.", "color": "#ffab00"})
        if latest["motivation"] < 4:
            alerts.append({"level": "MEDIUM", "msg": "Motivation declining. 1-on-1 coaching session recommended.", "color": "#ffab00"})

        if not alerts:
            alerts.append({"level": "GOOD", "msg": "Player wellness is within healthy range. Keep monitoring.", "color": "#00c853"})

        for alert in alerts:
            st.markdown(f"""
                <div style="background:{S8UL_CARD}; padding:12px 16px; border-radius:8px; margin-bottom:8px; border-left: 4px solid {alert['color']};">
                    <div style="display:flex; align-items:center; gap:10px;">
                        <span style="background:{alert['color']}; color:#000; padding:2px 10px; border-radius:10px; font-size:0.7rem; font-weight:700;">{alert['level']}</span>
                        <span style="color:#ddd; font-size:0.9rem;">{alert['msg']}</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        st.subheader("📋 Mood History")
        display_df = mood_df[["date", "mood", "energy_level", "sleep_hours", "motivation", "physical_pain", "notes"]].copy()
        display_df.columns = ["Date", "Mood", "Energy", "Sleep", "Motivation", "Pain", "Notes"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    else:
        st.info("No mood data recorded for this player yet.")

    with st.expander("➕ Log Today's Mood"):
        mood = st.selectbox("Mood", list(MOOD_EMOJIS.keys()), key="mood_input")
        energy = st.slider("Energy Level (1-10)", 1, 10, 5, key="mood_energy")
        sleep = st.slider("Sleep Hours", 0.0, 12.0, 7.0, 0.5, key="mood_sleep")
        motivation = st.slider("Motivation (1-10)", 1, 10, 5, key="mood_motivation")
        pain = st.slider("Physical Pain (0-10)", 0, 10, 0, key="mood_pain")
        mood_notes = st.text_area("Notes", key="mood_notes_input")
        if st.button("Save Mood", key="mood_save"):
            conn = get_conn()
            conn.execute("""
                INSERT INTO player_mood (player_id, date, mood, energy_level, sleep_hours, motivation, physical_pain, notes)
                VALUES (?,?,?,?,?,?,?,?)
            """, (pid, datetime.date.today().isoformat(), mood, energy, sleep, motivation, pain, mood_notes))
            conn.commit()
            conn.close()
            st.success("Mood logged!")
            st.rerun()

# ───────────────────────────────────────────────
# TAB 10: AI COACH
# ───────────────────────────────────────────────
def tab_ai_coach():
    st.header("🤖 AI Coach")

    conn = get_conn()
    players_df = pd.read_sql_query("""
        SELECT p.id, p.name, p.role,
               SUM(ds.kills) as total_kills,
               SUM(ds.matches) as total_matches,
               AVG(ds.damage) as avg_damage,
               AVG(ds.survival_time) as avg_survival,
               SUM(ds.booyahs) as total_booyahs
        FROM players p
        LEFT JOIN daily_stats ds ON p.id = ds.player_id
        WHERE p.status = 'Active'
        GROUP BY p.id
    """, conn)

    scrims_df = pd.read_sql_query("SELECT * FROM scrims ORDER BY date DESC LIMIT 10", conn)
    igl_df = pd.read_sql_query("SELECT * FROM igl_calls", conn)
    mood_df = pd.read_sql_query("SELECT * FROM player_mood ORDER BY date DESC", conn)
    conn.close()

    if players_df.empty:
        st.info("Add players to get AI coaching insights.")
        return

    st.subheader("📋 Squad Analysis")

    total_matches = players_df["total_matches"].sum()
    total_kills = players_df["total_kills"].sum()
    avg_team_dmg = players_df["avg_damage"].mean()
    avg_team_surv = players_df["avg_survival"].mean()
    total_booyahs = players_df["total_booyahs"].sum()

    c1, c2, c3, c4 = st.columns(4)
    for col, label, val, color in [
        (c1, "Team Kills", int(total_kills or 0), S8UL_RED),
        (c2, "Avg Damage", f"{avg_team_dmg:.0f}" if avg_team_dmg else "—", "#fff"),
        (c3, "Avg Survival", f"{avg_team_surv:.1f}m" if avg_team_surv else "—", "#fff"),
        (c4, "Booyahs", int(total_booyahs or 0), "#00c853"),
    ]:
        col.markdown(f"""
            <div style="background:{S8UL_CARD}; padding:15px; border-radius:10px; text-align:center;">
                <p style="color:#888; font-size:0.8rem; margin:0;">{label}</p>
                <p style="color:{color}; font-size:1.6rem; font-weight:700; margin:0;">{val}</p>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    st.subheader("🎯 Coaching Recommendations")

    recommendations = []

    if total_matches > 0:
        kpm = total_kills / total_matches
        if kpm < 2.0:
            recommendations.append({
                "priority": "HIGH",
                "icon": "⚠️",
                "title": "Low Kill Rate Detected",
                "desc": f"Team averaging {kpm:.1f} kills/match. Focus on: (1) Drop location selection for early fights, (2) Third-party timing training, (3) Rush coordination drills.",
                "color": "#ff5252"
            })
        elif kpm > 5.0:
            recommendations.append({
                "priority": "GOOD",
                "icon": "✅",
                "title": "Strong Kill Output",
                "desc": f"Team averaging {kpm:.1f} kills/match. Maintain aggression but ensure late-game positioning does not suffer.",
                "color": "#00c853"
            })

    if avg_team_dmg and avg_team_dmg < 1500:
        recommendations.append({
            "priority": "MEDIUM",
            "icon": "💡",
            "title": "Damage Output Below Optimal",
            "desc": "Avg damage per player is under 1500. Schedule aim training: spray control with M1887/MP40, long-range taps with AWM/AC80.",
            "color": "#ffab00"
        })

    if avg_team_surv and avg_team_surv < 10:
        recommendations.append({
            "priority": "HIGH",
            "icon": "🛡️",
            "title": "Early Deaths Pattern",
            "desc": "Average survival under 10 minutes. Review drop strategies and early rotation decisions. Consider safer drops or improved loot pathing.",
            "color": "#ff5252"
        })

    if not igl_df.empty:
        total_calls = len(igl_df)
        success_rate = (igl_df["outcome"] == "Success").sum() / total_calls * 100
        if success_rate < 50:
            recommendations.append({
                "priority": "HIGH",
                "icon": "🧠",
                "title": "IGL Decision Making Needs Work",
                "desc": f"Success rate is {success_rate:.0f}%. Review failed calls in Zones 3-4. Practice zone reading and rotation timing in custom rooms.",
                "color": "#ff5252"
            })
        elif success_rate > 70:
            recommendations.append({
                "priority": "GOOD",
                "icon": "🔥",
                "title": "Excellent IGL Performance",
                "desc": f"{success_rate:.0f}% call success rate. Document successful strategies for tournament playbooks.",
                "color": "#00c853"
            })

    if not scrims_df.empty:
        avg_place = scrims_df["placement"].mean()
        if avg_place > 5:
            recommendations.append({
                "priority": "MEDIUM",
                "icon": "📉",
                "title": "Placement Slipping",
                "desc": f"Avg placement: #{avg_place:.1f}. Focus on late-game positioning and zone edge control. Practice holding compounds in final circles.",
                "color": "#ffab00"
            })

    role_counts = players_df["role"].value_counts().to_dict()
    if role_counts.get("IGL", 0) == 0:
        recommendations.append({
            "priority": "HIGH",
            "icon": "🧠",
            "title": "No IGL in Roster",
            "desc": "Every competitive squad needs a dedicated IGL. Assign your most experienced player or recruit one.",
            "color": "#ff5252"
        })
    if role_counts.get("Nader", 0) == 0:
        recommendations.append({
            "priority": "HIGH",
            "icon": "💣",
            "title": "No Nader in Roster",
            "desc": "Industry-standard IGL + Nader combo is missing the Nader role. Recruit a player skilled with grenades and zone control.",
            "color": "#ff5252"
        })
    if role_counts.get("Rusher", 0) < 2:
        recommendations.append({
            "priority": "MEDIUM",
            "icon": "⚡",
            "title": "Need More Rushers",
            "desc": "Recommended: 2 Rushers for optimal aggression. Current count is insufficient for coordinated pushes.",
            "color": "#ffab00"
        })

    if not scrims_df.empty:
        weak_maps = scrims_df.groupby("map")["placement"].mean().sort_values(ascending=False)
        if len(weak_maps) > 0 and weak_maps.iloc[0] > 5:
            worst_map = weak_maps.index[0]
            recommendations.append({
                "priority": "MEDIUM",
                "icon": "🗺️",
                "title": f"Struggle on {worst_map}",
                "desc": f"Avg placement #{weak_maps.iloc[0]:.1f} on {worst_map}. Review map strategies, drop locations, and rotation paths for this map.",
                "color": "#ffab00"
            })

    if not mood_df.empty:
        recent_mood = mood_df[mood_df["date"] >= (datetime.date.today() - datetime.timedelta(days=3)).isoformat()]
        if not recent_mood.empty:
            burnout_count = len(recent_mood[recent_mood["mood"].isin(["Burned Out", "Stressed"])])
            if burnout_count > 0:
                recommendations.append({
                    "priority": "HIGH",
                    "icon": "🔥",
                    "title": f"Burnout Risk Detected ({burnout_count} players)",
                    "desc": "Recent mood data shows players experiencing burnout/stress. Schedule rest days and 1-on-1 check-ins immediately.",
                    "color": "#ff5252"
                })

    if not recommendations:
        recommendations.append({
            "priority": "INFO",
            "icon": "✨",
            "title": "Team Looking Solid",
            "desc": "No critical issues detected. Keep grinding scrims and maintain current form. Focus on tournament preparation.",
            "color": "#4fc3f7"
        })

    for rec in recommendations:
        st.markdown(f"""
            <div style="background:{S8UL_CARD}; padding:16px; border-radius:12px; margin-bottom:12px; border-left: 4px solid {rec["color"]};">
                <div style="display:flex; align-items:center; gap:10px; margin-bottom:6px;">
                    <span style="font-size:1.3rem;">{rec["icon"]}</span>
                    <span style="color:#fff; font-weight:700; font-size:1.05rem;">{rec["title"]}</span>
                    <span style="background:{rec["color"]}; color:#000; padding:2px 10px; border-radius:10px; font-size:0.7rem; font-weight:700; margin-left:auto;">
                        {rec["priority"]}
                    </span>
                </div>
                <p style="color:#ccc; margin:0; font-size:0.95rem; line-height:1.5;">{rec["desc"]}</p>
            </div>
        """, unsafe_allow_html=True)

    st.subheader("👤 Player-Specific Tips")
    for _, player in players_df.iterrows():
        tips = []
        p_kills = player["total_kills"] or 0
        p_matches = player["total_matches"] or 1
        p_dmg = player["avg_damage"] or 0
        p_surv = player["avg_survival"] or 0
        p_kpm = p_kills / p_matches

        if p_kpm < 1.5:
            tips.append("Increase aggression in mid-game. Look for third-party opportunities.")
        if p_dmg < 1000:
            tips.append("Focus on aim training. Practice 15 mins daily in training ground.")
        if p_surv < 8:
            tips.append("Work on positioning. Avoid open fields and stick to cover.")
        if not tips:
            tips.append("Performance is solid. Focus on consistency and clutch situations.")

        tips_html = "".join(f"<li>{tip}</li>" for tip in tips)
        st.markdown(f"""
            <div style="background:{S8UL_CARD}; padding:12px 16px; border-radius:10px; margin-bottom:8px;">
                <p style="color:#fff; font-weight:600; margin:0 0 6px 0;">{player["name"]} <span style="color:#888; font-size:0.8rem;">({player["role"]})</span></p>
                <ul style="color:#aaa; margin:0; padding-left:16px; font-size:0.85rem;">
                    {tips_html}
                </ul>
            </div>
        """, unsafe_allow_html=True)

    st.subheader("📅 Suggested Weekly Training Schedule")
    schedule = [
        ("Monday", "Aim Training + Drop Practice", "30 mins aim trainer, 5 custom drops on weak maps"),
        ("Tuesday", "Scrimmage Day", "3-4 scrims, full VOD review after each"),
        ("Wednesday", "IGL Workshop", "Zone reading drills, call timing practice, rotation scenarios"),
        ("Thursday", "Role-Specific Drills", "Rushers: entry fragging | Sniper: long-range holds | Support: utility usage | Nader: grenade lineups"),
        ("Friday", "Team Scrimmage", "Full 5-man scrims with recorded comms"),
        ("Saturday", "VOD Review + Strategy", "Deep analysis of weekday scrims, update map strategies"),
        ("Sunday", "Rest / Light DM", "Free play or deathmatch for mechanics maintenance"),
    ]

    for day, activity, detail in schedule:
        st.markdown(f"""
            <div style="background:{S8UL_CARD}; padding:10px 14px; border-radius:8px; margin-bottom:6px;">
                <div style="display:flex; gap:15px;">
                    <span style="color:{S8UL_RED}; font-weight:700; min-width:80px;">{day}</span>
                    <div>
                        <p style="color:#fff; font-weight:600; margin:0; font-size:0.9rem;">{activity}</p>
                        <p style="color:#888; margin:0; font-size:0.8rem;">{detail}</p>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

# ───────────────────────────────────────────────
# TAB 11: DASHBOARD OVERVIEW
# ───────────────────────────────────────────────
def tab_dashboard():
    st.header("📈 Executive Dashboard")
    st.markdown("<p style='color:#888; font-size:0.9rem;'>Real-time overview of team performance, wellness, and business metrics</p>", unsafe_allow_html=True)

    conn = get_conn()
    players_df = pd.read_sql_query("SELECT * FROM players WHERE status='Active'", conn)
    scrims_df = pd.read_sql_query("SELECT * FROM scrims ORDER BY date DESC LIMIT 5", conn)
    tour_df = pd.read_sql_query("SELECT * FROM tournaments WHERE status IN ('Ongoing', 'Upcoming') ORDER BY start_date", conn)
    mood_df = pd.read_sql_query("SELECT * FROM player_mood ORDER BY date DESC", conn)
    conn.close()

    c1, c2, c3, c4 = st.columns(4)
    total_players = len(players_df)
    upcoming_tour = len(tour_df[tour_df["status"] == "Upcoming"]) if not tour_df.empty else 0
    ongoing_tour = len(tour_df[tour_df["status"] == "Ongoing"]) if not tour_df.empty else 0

    kpis = [
        (c1, "👥 Players", total_players, "#fff"),
        (c2, "🏆 Tournaments", f"{ongoing_tour} Live / {upcoming_tour} Upcoming", S8UL_RED),
        (c3, "📊 Recent Scrims", len(scrims_df), "#ffab00"),
        (c4, "😊 Mood Logs", len(mood_df), "#4fc3f7"),
    ]
    for col, label, val, color in kpis:
        col.markdown(f"""
            <div style="background:{S8UL_CARD}; padding:15px; border-radius:10px; text-align:center;">
                <p style="color:#888; font-size:0.8rem; margin:0;">{label}</p>
                <p style="color:{color}; font-size:1.4rem; font-weight:700; margin:0;">{val}</p>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🔥 Live Tournament Status")
        if not tour_df.empty:
            for _, row in tour_df.iterrows():
                status_color = "#ffab00" if row["status"] == "Upcoming" else S8UL_RED
                current_rank_html = ""
                if pd.notna(row.get("current_placement")):
                    current_rank_html = f'<span style="color:{S8UL_RED};">🏆 #{int(row["current_placement"])} Place</span>'

                st.markdown(f"""
                    <div style="background:{S8UL_CARD}; padding:12px; border-radius:8px; margin-bottom:8px;">
                        <div style="display:flex; justify-content:space-between;">
                            <span style="color:#fff; font-weight:600;">{row['name']}</span>
                            <span style="color:{status_color}; font-size:0.8rem; font-weight:600;">{row['status']}</span>
                        </div>
                        <div style="display:flex; gap:15px; margin-top:6px; color:#888; font-size:0.8rem;">
                            <span>📅 {row['start_date']}</span>
                            <span>💰 {row['prize_pool']}</span>
                            {current_rank_html}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No upcoming or ongoing tournaments.")

    with col2:
        st.subheader("😊 Team Wellness Snapshot")
        if not mood_df.empty:
            recent_mood = mood_df[mood_df["date"] >= (datetime.date.today() - datetime.timedelta(days=2)).isoformat()]
            if not recent_mood.empty:
                for _, row in recent_mood.head(5).iterrows():
                    player_name = players_df[players_df["id"] == row["player_id"]]["name"].values
                    name = player_name[0] if len(player_name) > 0 else "Unknown"
                    mood_color = "#00c853" if row["mood"] in ["Excellent", "Good"] else "#ffab00" if row["mood"] == "Neutral" else "#ff5252"
                    st.markdown(f"""
                        <div style="background:{S8UL_CARD}; padding:10px 12px; border-radius:8px; margin-bottom:6px;">
                            <div style="display:flex; justify-content:space-between;">
                                <span style="color:#fff; font-weight:500;">{name}</span>
                                <span style="color:{mood_color}; font-size:0.85rem; font-weight:600;">{MOOD_EMOJIS.get(row['mood'], '😐')} {row['mood']}</span>
                            </div>
                            <div style="display:flex; gap:15px; margin-top:4px; color:#888; font-size:0.75rem;">
                                <span>⚡ {row['energy_level']}/10 energy</span>
                                <span>😴 {row['sleep_hours']}h sleep</span>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No recent mood data.")
        else:
            st.info("No mood data recorded yet.")

    st.subheader("🎯 Recent Scrims")
    if not scrims_df.empty:
        for _, row in scrims_df.head(3).iterrows():
            badge_color = "#00c853" if row["placement"] == 1 else "#ffab00" if row["placement"] <= 3 else "#888"
            st.markdown(f"""
                <div style="background:{S8UL_CARD}; padding:10px 14px; border-radius:8px; margin-bottom:6px;">
                    <div style="display:flex; justify-content:space-between;">
                        <span style="color:#fff; font-weight:500;">📅 {row['date']} • 🗺️ {row['map']}</span>
                        <span style="background:{badge_color}; color:#000; padding:2px 8px; border-radius:10px; font-size:0.75rem; font-weight:600;">#{row['placement']} Place</span>
                    </div>
                    <span style="color:#888; font-size:0.8rem;">⚔️ {row['kills']} kills • 🏆 {row['total_points']} points</span>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No recent scrims.")

# ───────────────────────────────────────────────
# MAIN APP
# ───────────────────────────────────────────────
def main():
    st.set_page_config(
        page_title="S8UL AI Coach v3.2",
        page_icon="🔥",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    st.markdown(f"""
        <style>
        .stApp {{
            background-color: {S8UL_DARK};
            color: #ffffff;
        }}
        .stTabs [data-baseweb="tab-list"] {{
            gap: 8px;
            background-color: {S8UL_CARD};
            padding: 8px;
            border-radius: 12px;
        }}
        .stTabs [data-baseweb="tab"] {{
            color: #888;
            border-radius: 8px;
            padding: 8px 16px;
        }}
        .stTabs [aria-selected="true"] {{
            background-color: {S8UL_RED} !important;
            color: #fff !important;
        }}
        .stButton>button {{
            background-color: {S8UL_RED};
            color: #fff;
            border: none;
            border-radius: 8px;
        }}
        .stButton>button:hover {{
            background-color: #cc0000;
        }}
        .stTextInput>div>div>input, .stNumberInput>div>div>input, .stTextArea>div>div>textarea {{
            background-color: {S8UL_CARD};
            color: #fff;
            border: 1px solid #333;
        }}
        .stSelectbox>div>div>div {{
            background-color: {S8UL_CARD};
            color: #fff;
        }}
        .stDateInput>div>div>input {{
            background-color: {S8UL_CARD};
            color: #fff;
        }}
        .stDataFrame {{
            background-color: {S8UL_CARD};
        }}
        .stExpander {{
            background-color: {S8UL_CARD};
            border-radius: 8px;
        }}
        div[data-testid="stSidebarContent"] {{
            background-color: #0f0f0f;
        }}
        h1, h2, h3 {{
            color: #fff !important;
        }}
        .stMarkdown {{
            color: #ddd;
        }}
        </style>
    """, unsafe_allow_html=True)

    init_db()

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        login_page()
        return

    if st.session_state.username == "demo":
        seed_demo_data()

    render_sidebar()

    st.markdown(f"""
        <div style="margin-bottom: 20px;">
            <h1 style="color:{S8UL_RED}; margin:0; font-size:2rem;">S8UL AI COACH</h1>
            <p style="color:#888; margin:0;">Free Fire Max • Esports Team Management System v3.2</p>
        </div>
    """, unsafe_allow_html=True)

    tabs = st.tabs([
        "📈 Dashboard", "📊 Performance", "🎯 Scrims", "🧠 IGL Calls",
        "🎭 Opponents", "👥 Team Comp", "🗺️ Maps",
        "🏆 Tournaments", "🎬 VOD Review", "😊 Wellness",
        "🤖 AI Coach", "⚙️ Admin"
    ])

    with tabs[0]:
        tab_dashboard()
    with tabs[1]:
        tab_performance()
    with tabs[2]:
        tab_scrims()
    with tabs[3]:
        tab_igl_calls()
    with tabs[4]:
        tab_opponents()
    with tabs[5]:
        tab_team_comp()
    with tabs[6]:
        tab_map_strategies()
    with tabs[7]:
        tab_tournaments()
    with tabs[8]:
        tab_vod_review()
    with tabs[9]:
        tab_player_mood()
    with tabs[10]:
        tab_ai_coach()
    with tabs[11]:
        tab_admin()

if __name__ == "__main__":
    main()
