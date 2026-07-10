import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import io
import os
import glob

st.set_page_config(page_title="WavePicker", page_icon="🌊", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 0.5rem; padding-bottom: 0; }
    section[data-testid="stSidebar"] { background-color: #12151f; }
    .stButton>button { width: 100%; border-radius: 6px; font-weight: 600; }
    .pick-p { color: #ff4d4d; font-weight: bold; font-size: 1.2rem; text-align: center; }
    .pick-s { color: #4daaff; font-weight: bold; font-size: 1.2rem; text-align: center; }
    .btn-active-p > button { background-color: #ff4d4d !important; color: white !important; }
    .btn-active-s > button { background-color: #4daaff !important; color: white !important; }
    .mode-label { 
        text-align: center; font-size: 0.95rem; font-weight: bold;
        padding: 6px; border-radius: 6px; margin-bottom: 4px;
    }
</style>
""", unsafe_allow_html=True)

# ── Session state ──────────────────────────────────────────────────
def init_state():
    defaults = {
        'idx': 0, 'picks': {}, 'files': [], 'file_names': [],
        'p_time': None, 's_time': None,
        'click_mode': None,   # 'P' ou 'S' ou None
        'data_folder': 'data',
        'week': None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()


# ── Helpers ────────────────────────────────────────────────────────
def find_burst_start(amp, win=50, step=5, factor=20):
    """Trouve le début du burst initial -> devient t=0."""
    var = np.array([np.var(amp[i:i+win]) for i in range(0, len(amp)-win, step)])
    noise = np.percentile(var, 10)
    for i, v in enumerate(var):
        if v > factor * noise:
            return i * step
    return 0
def load_file(file_obj):
    """Charge un fichier TXT et retourne t (µs depuis burst) et amp."""
    raw = file_obj.read()
    file_obj.seek(0)
    data = np.loadtxt(io.StringIO(raw.decode('utf-8')), delimiter=',')
    t_raw = data[:, 0] * 1e6
    amp   = data[:, 1]
    # Décaler t=0 sur le début du burst
    burst_idx = find_burst_start(amp)
    t = t_raw - t_raw[burst_idx]
    return t, amp

def save_current():
    if not st.session_state.files:
        return
    idx   = st.session_state.idx
    fname = st.session_state.file_names[idx]
    st.session_state.picks[fname] = {
        'P': round(st.session_state.p_time, 3) if st.session_state.p_time is not None else None,
        'S': round(st.session_state.s_time, 3) if st.session_state.s_time is not None else None,
    }

def load_picks_for_current():
    if not st.session_state.files:
        return
    fname = st.session_state.file_names[st.session_state.idx]
    prev  = st.session_state.picks.get(fname, {})
    st.session_state.p_time = prev.get('P')
    st.session_state.s_time = prev.get('S')

def get_weeks():
    base = st.session_state.data_folder
    if not os.path.exists(base):
        return []
    weeks = sorted([d for d in os.listdir(base)
                    if os.path.isdir(os.path.join(base, d))
                    and 'export_ch1' in d.lower()])
    return weeks

def load_week(week_name):
    """Charge tous les CH1.txt d'une semaine depuis data/<week>/."""
    folder = os.path.join(st.session_state.data_folder, week_name)
    files  = sorted(glob.glob(os.path.join(folder, '**', '*CH1.txt'), recursive=True))
    return files


# ── Sidebar ────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🌊 WavePicker")
    st.caption("Picking manuel P & S")
    st.divider()

    tab_local, tab_upload = st.tabs(["📁 Semaines", "⬆️ Upload"])

    # --- Tab Semaines (dossier data/) ---
    with tab_local:
        weeks = get_weeks()
        if weeks:
            selected_week = st.selectbox("Sélectionne une semaine", weeks,
                                          index=weeks.index(st.session_state.week)
                                          if st.session_state.week in weeks else 0)
            if st.button("Charger cette semaine", key="load_week"):
                paths = load_week(selected_week)
                if paths:
                    st.session_state.files      = [open(p, 'rb') for p in paths]
                    st.session_state.file_names = [os.path.basename(p) for p in paths]
                    st.session_state.idx        = 0
                    st.session_state.week       = selected_week
                    st.session_state.p_time     = None
                    st.session_state.s_time     = None
                    st.session_state.click_mode = None
                    load_picks_for_current()
                    st.rerun()
                else:
                    st.warning(f"Aucun CH1.txt dans {selected_week}")
        else:
            st.info("Place tes dossiers Week 1, Week 2... dans le dossier `data/` du repo.")

    # --- Tab Upload ---
    with tab_upload:
        uploaded = st.file_uploader(
            "Charger des fichiers TXT",
            type=['txt'], accept_multiple_files=True,
            help="Fichiers *CH1.txt"
        )
        if uploaded and st.button("Charger ces fichiers", key="load_upload"):
            uploaded_sorted = sorted(uploaded, key=lambda f: f.name)
            st.session_state.files      = uploaded_sorted
            st.session_state.file_names = [f.name for f in uploaded_sorted]
            st.session_state.idx        = 0
            st.session_state.p_time     = None
            st.session_state.s_time     = None
            st.session_state.click_mode = None
            load_picks_for_current()
            st.rerun()

    st.divider()

    if st.session_state.files:
        n   = len(st.session_state.files)
        idx = st.session_state.idx
        fname = st.session_state.file_names[idx]

        st.markdown(f"**{idx+1} / {n}**")
        st.progress((idx+1)/n)
        st.markdown(f"**`{fname.replace('CH1.txt','')}`**")
        st.divider()

        # Temps picks
        p = st.session_state.p_time
        s = st.session_state.s_time
        st.markdown(f'<div class="pick-p">P : {f"{p:.3f} µs" if p is not None else "—"}</div>',
                    unsafe_allow_html=True)
        st.markdown(f'<div class="pick-s">S : {f"{s:.3f} µs" if s is not None else "—"}</div>',
                    unsafe_allow_html=True)
        st.divider()

        # Mode clic
        mode = st.session_state.click_mode
        if mode == 'P':
            st.markdown('<div class="mode-label" style="background:#3a1a1a;color:#ff4d4d">🖱️ Mode P actif — clique sur le graphe</div>', unsafe_allow_html=True)
        elif mode == 'S':
            st.markdown('<div class="mode-label" style="background:#1a2a3a;color:#4daaff">🖱️ Mode S actif — clique sur le graphe</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="mode-label" style="background:#1e1e1e;color:#888">Sélectionne un mode de picking</div>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔴 Placer P", key="btn_p",
                         type="primary" if mode=='P' else "secondary"):
                st.session_state.click_mode = 'P' if mode != 'P' else None
                st.rerun()
        with col2:
            if st.button("🔵 Placer S", key="btn_s",
                         type="primary" if mode=='S' else "secondary"):
                st.session_state.click_mode = 'S' if mode != 'S' else None
                st.rerun()

        if st.button("🗑 Reset picks"):
            st.session_state.p_time = None
            st.session_state.s_time = None
            st.session_state.click_mode = None
            st.rerun()

        st.divider()

        col3, col4 = st.columns(2)
        with col3:
            if st.button("← Préc.", disabled=idx==0):
                save_current()
                st.session_state.idx -= 1
                st.session_state.click_mode = None
                load_picks_for_current()
                st.rerun()
        with col4:
            label = "Suiv. →" if idx < n-1 else "✅ Fin"
            if st.button(label):
                save_current()
                if idx < n-1:
                    st.session_state.idx += 1
                    st.session_state.click_mode = None
                    load_picks_for_current()
                st.rerun()

        st.divider()

        # Export CSV
        if st.session_state.picks:
            rows = []
            for fn, pick in st.session_state.picks.items():
                rows.append({
                    'Fichier':       fn.replace('CH1.txt',''),
                    'Onset P (µs)':  pick.get('P',''),
                    'Onset S (µs)':  pick.get('S',''),
                })
            df_out = pd.DataFrame(rows)
            st.download_button(
                "💾 Télécharger CSV",
                data=df_out.to_csv(index=False).encode('utf-8'),
                file_name="picks_results.csv",
                mime="text/csv"
            )


# ── Main ───────────────────────────────────────────────────────────
if not st.session_state.files:
    st.markdown("## 🌊 WavePicker")
    st.markdown("**👈 Charge tes fichiers dans la barre latérale pour commencer.**")
    st.markdown("""
    **Mode Semaines** : place tes dossiers `Week 1`, `Week 2`... dans le dossier `data/` du repo.
    
    **Mode Upload** : uploade directement des fichiers `*CH1.txt`.
    """)
else:
    idx = st.session_state.idx
    f   = st.session_state.files[idx]
    t, amp = load_file(f)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=t, y=amp, mode='lines',
        line=dict(color='#4a9eff', width=0.9),
        name='Signal'
    ))
    # Ligne t=0 (début burst)
    fig.add_vline(x=0, line_color='#888888', line_dash='dot', line_width=1,
                  annotation_text="t=0 (burst)", annotation_font_color='#888',
                  annotation_position="top left")

    p = st.session_state.p_time
    s = st.session_state.s_time
    if p is not None:
        fig.add_vline(x=p, line_color='#ff4d4d', line_dash='dash', line_width=2,
                      annotation_text=f"P={p:.3f}µs", annotation_font_color='#ff4d4d')
    if s is not None:
        fig.add_vline(x=s, line_color='#4daaff', line_dash='dash', line_width=2,
                      annotation_text=f"S={s:.3f}µs", annotation_font_color='#4daaff')

    fig.update_layout(
        paper_bgcolor='#0f1117', plot_bgcolor='#0f1117',
        font_color='#aaaaaa',
        xaxis=dict(title='Temps depuis début burst (µs)', gridcolor='#1e2130', color='#aaa'),
        yaxis=dict(title='Amplitude (ADC)', gridcolor='#1e2130', color='#aaa'),
        margin=dict(l=60, r=20, t=20, b=50),
        height=460, showlegend=False,
    )

    # Récupérer le clic sur le graphe
    click_event = st.plotly_chart(
        fig, use_container_width=True,
        config={'displayModeBar': True, 'scrollZoom': True, 'displaylogo': False},
        on_select="rerun",
        selection_mode="points",
        key=f"chart_{idx}"
    )

    # Traiter le clic
    mode = st.session_state.click_mode
    if mode and click_event and click_event.selection and click_event.selection.get('points'):
        pt = click_event.selection['points'][0]
        x_click = pt.get('x')
        if x_click is not None:
            if mode == 'P':
                st.session_state.p_time = round(x_click, 3)
            elif mode == 'S':
                st.session_state.s_time = round(x_click, 3)
            st.session_state.click_mode = None
            st.rerun()

    fname = st.session_state.file_names[idx]
    week_label = f" — {st.session_state.week}" if st.session_state.week else ""
    st.caption(f"📄 `{fname.replace('CH1.txt','')}`{week_label}  |  "
               f"💡 Clique sur **🔴 Placer P** ou **🔵 Placer S**, puis clique sur le graphe")
