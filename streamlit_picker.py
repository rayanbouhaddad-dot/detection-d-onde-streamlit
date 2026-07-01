import streamlit as st
import os
import glob
import csv
import numpy as np
import plotly.graph_objects as go
from io import StringIO
import base64

# Configuration de la page
st.set_page_config(
    page_title="WavePicker — P & S Wave Picker",
    page_icon="🌊",
    layout="wide"
)

# Styles CSS
st.markdown("""
<style>
    .main { background-color: #0f1117; }
    .stApp { background-color: #0f1117; }
    .stButton > button {
        background-color: #1e2130;
        color: #e0e0e0;
        border: 1px solid #333;
        border-radius: 6px;
        padding: 8px 18px;
        width: 100%;
    }
    .stButton > button:hover {
        background-color: #2a2f45;
        border-color: #4a9eff;
    }
    .file-info {
        background-color: #1e2130;
        padding: 15px;
        border-radius: 8px;
        border-left: 3px solid #4a9eff;
        margin-bottom: 15px;
    }
    .pick-label-p { color: #ff4d4d; font-weight: bold; }
    .pick-label-s { color: #4daaff; font-weight: bold; }
    .title-text { color: #4a9eff; font-size: 24px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# Initialisation de l'état
def init_session_state():
    if 'files' not in st.session_state:
        # Cherche automatiquement dans le dossier data
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        if os.path.exists(data_dir):
            st.session_state.files = sorted(glob.glob(os.path.join(data_dir, '*CH1.txt')))
        else:
            st.session_state.files = []
    if 'idx' not in st.session_state:
        st.session_state.idx = 0
    if 'picks' not in st.session_state:
        st.session_state.picks = {}
    if 'current_data' not in st.session_state:
        st.session_state.current_data = None
    if 'current_p_time' not in st.session_state:
        st.session_state.current_p_time = None
    if 'current_s_time' not in st.session_state:
        st.session_state.current_s_time = None
    if 'folder_loaded' not in st.session_state:
        st.session_state.folder_loaded = bool(st.session_state.files)

init_session_state()

def load_file(filepath):
    """Charge un fichier texte et retourne les données"""
    try:
        data = np.loadtxt(filepath, delimiter=',')
        if data.ndim == 1:
            data = data.reshape(-1, 1)
        if data.shape[1] >= 2:
            t = data[:, 0] * 1e6  # conversion en µs
            amp = data[:, 1]
            return t, amp
        else:
            return None, None
    except:
        return None, None

def plot_waveform(t, amp, p_time=None, s_time=None, height=500):
    """Crée un graphique Plotly avec les picks P et S"""
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=t, y=amp,
        mode='lines',
        name='Signal',
        line=dict(color='#4a9eff', width=1.5),
        hovertemplate='Temps: %{x:.3f} µs<br>Amplitude: %{y:.2f}<extra></extra>'
    ))
    
    if p_time is not None:
        fig.add_vline(
            x=p_time,
            line=dict(color='#ff4d4d', width=2, dash='dash'),
            annotation_text=f'P = {p_time:.3f} µs',
            annotation_position="top right",
            annotation_font=dict(color='#ff4d4d', size=11)
        )
    
    if s_time is not None:
        fig.add_vline(
            x=s_time,
            line=dict(color='#4daaff', width=2, dash='dash'),
            annotation_text=f'S = {s_time:.3f} µs',
            annotation_position="top left",
            annotation_font=dict(color='#4daaff', size=11)
        )
    
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor='#0f1117',
        plot_bgcolor='#0f1117',
        font=dict(color='#e0e0e0'),
        xaxis=dict(
            title='Temps (µs)',
            gridcolor='#333333',
            gridwidth=0.5,
            showgrid=True,
            color='#aaaaaa'
        ),
        yaxis=dict(
            title='Amplitude (ADC)',
            gridcolor='#333333',
            gridwidth=0.5,
            showgrid=True,
            color='#aaaaaa'
        ),
        hovermode='x',
        margin=dict(l=50, r=50, t=50, b=50),
        height=height
    )
    return fig

def save_picks_to_csv(picks_dict):
    """Génère un fichier CSV à partir des picks"""
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Fichier', 'Onset P (µs)', 'Onset S (µs)'])
    for fname, picks in picks_dict.items():
        writer.writerow([
            fname.replace('CH1.txt', ''),
            picks.get('P', ''),
            picks.get('S', '')
        ])
    return output.getvalue()

# Interface principale
st.markdown('<span class="title-text">🌊 WavePicker</span>', unsafe_allow_html=True)
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("📂 Gestion des fichiers")
    
    # Afficher le nombre de fichiers chargés
    if st.session_state.files:
        st.success(f"✅ {len(st.session_state.files)} fichiers trouvés dans le dossier 'data'")
    else:
        st.warning("⚠️ Aucun fichier CH1.txt trouvé dans le dossier 'data'")
        st.info("📁 Créez un dossier 'data' dans votre dépôt avec vos fichiers CH1.txt")
    
    st.markdown("---")
    
    if st.session_state.files:
        st.header("📄 Navigation")
        total_files = len(st.session_state.files)
        current_idx = st.session_state.idx
        
        # Progression
        st.progress((current_idx + 1) / total_files)
        st.caption(f"{current_idx + 1} / {total_files}")
        
        # Boutons de navigation
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← Précédent", disabled=(current_idx == 0), use_container_width=True):
                if current_idx > 0:
                    # Sauvegarder les picks actuels
                    fname = os.path.basename(st.session_state.files[current_idx])
                    if st.session_state.current_p_time is not None or st.session_state.current_s_time is not None:
                        st.session_state.picks[fname] = {
                            'P': round(st.session_state.current_p_time, 3) if st.session_state.current_p_time else None,
                            'S': round(st.session_state.current_s_time, 3) if st.session_state.current_s_time else None,
                        }
                    
                    st.session_state.idx -= 1
                    t, amp = load_file(st.session_state.files[st.session_state.idx])
                    st.session_state.current_data = (t, amp)
                    
                    # Récupérer les picks précédents
                    prev_fname = os.path.basename(st.session_state.files[st.session_state.idx])
                    prev_picks = st.session_state.picks.get(prev_fname, {})
                    st.session_state.current_p_time = prev_picks.get('P')
                    st.session_state.current_s_time = prev_picks.get('S')
                    st.rerun()
        
        with col2:
            if st.button("Suivant →", use_container_width=True):
                if current_idx < total_files - 1:
                    # Sauvegarder les picks actuels
                    fname = os.path.basename(st.session_state.files[current_idx])
                    if st.session_state.current_p_time is not None or st.session_state.current_s_time is not None:
                        st.session_state.picks[fname] = {
                            'P': round(st.session_state.current_p_time, 3) if st.session_state.current_p_time else None,
                            'S': round(st.session_state.current_s_time, 3) if st.session_state.current_s_time else None,
                        }
                    
                    st.session_state.idx += 1
                    t, amp = load_file(st.session_state.files[st.session_state.idx])
                    st.session_state.current_data = (t, amp)
                    
                    # Récupérer les picks précédents
                    next_fname = os.path.basename(st.session_state.files[st.session_state.idx])
                    next_picks = st.session_state.picks.get(next_fname, {})
                    st.session_state.current_p_time = next_picks.get('P')
                    st.session_state.current_s_time = next_picks.get('S')
                    st.rerun()
        
        st.markdown("---")
        
        # Informations sur les picks
        st.header("🎯 Picks")
        st.markdown("**Clic sur le graphique pour placer les marqueurs :**")
        st.markdown('- <span class="pick-label-p">🔴 Clic gauche → P</span>', unsafe_allow_html=True)
        st.markdown('- <span class="pick-label-s">🔵 Clic droit → S</span>', unsafe_allow_html=True)
        
        p_val = st.session_state.current_p_time
        s_val = st.session_state.current_s_time
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f'<span class="pick-label-p">P : {p_val:.3f} µs</span>' if p_val else '<span class="pick-label-p">P : —</span>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<span class="pick-label-s">S : {s_val:.3f} µs</span>' if s_val else '<span class="pick-label-s">S : —</span>', unsafe_allow_html=True)
        
        # Boutons pour effacer les picks
        if st.button("🗑 Reset picks", use_container_width=True):
            st.session_state.current_p_time = None
            st.session_state.current_s_time = None
            st.rerun()
        
        st.markdown("---")
        
        # Sauvegarde
        st.header("💾 Sauvegarde")
        if st.button("📊 Sauvegarder CSV", use_container_width=True):
            if st.session_state.picks:
                # Sauvegarder le fichier courant
                fname = os.path.basename(st.session_state.files[st.session_state.idx])
                if st.session_state.current_p_time is not None or st.session_state.current_s_time is not None:
                    st.session_state.picks[fname] = {
                        'P': round(st.session_state.current_p_time, 3) if st.session_state.current_p_time else None,
                        'S': round(st.session_state.current_s_time, 3) if st.session_state.current_s_time else None,
                    }
                
                csv_content = save_picks_to_csv(st.session_state.picks)
                b64 = base64.b64encode(csv_content.encode()).decode()
                href = f'<a href="data:text/csv;base64,{b64}" download="picks_results.csv">📥 Télécharger CSV</a>'
                st.markdown(href, unsafe_allow_html=True)
                st.success("✅ CSV prêt à être téléchargé")
            else:
                st.warning("⚠️ Aucun pick enregistré")

# Zone principale
if st.session_state.files:
    # Charger le premier fichier si pas encore chargé
    if st.session_state.current_data is None:
        t, amp = load_file(st.session_state.files[0])
        st.session_state.current_data = (t, amp)
    
    current_file = st.session_state.files[st.session_state.idx]
    fname_display = os.path.basename(current_file).replace('CH1.txt', '')
    
    st.markdown(f"""
    <div class="file-info">
        <strong>📄 Fichier :</strong> {fname_display}
        <br>
        <span style="color: #888888; font-size: 12px;">
            {st.session_state.idx + 1} / {len(st.session_state.files)}
        </span>
    </div>
    """, unsafe_allow_html=True)
    
    t, amp = st.session_state.current_data
    
    if t is not None and amp is not None:
        fig = plot_waveform(
            t, amp,
            p_time=st.session_state.current_p_time,
            s_time=st.session_state.current_s_time,
            height=550
        )
        
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': True})
        st.info("💡 **Picking interactif :** Cliquez sur le graphique pour placer les marqueurs P (gauche) et S (droit).")
        
        # Interface pour le picking manuel
        st.markdown("### 🎯 Picking manuel")
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            p_input = st.number_input(
                "Temps P (µs)",
                value=float(st.session_state.current_p_time) if st.session_state.current_p_time else float(t.min()),
                min_value=float(t.min()),
                max_value=float(t.max()),
                step=0.1,
                format="%.3f",
                key="p_input"
            )
            if st.button("✅ Valider P", use_container_width=True):
                st.session_state.current_p_time = p_input
                st.rerun()
        
        with col2:
            s_input = st.number_input(
                "Temps S (µs)",
                value=float(st.session_state.current_s_time) if st.session_state.current_s_time else float(t.min()),
                min_value=float(t.min()),
                max_value=float(t.max()),
                step=0.1,
                format="%.3f",
                key="s_input"
            )
            if st.button("✅ Valider S", use_container_width=True):
                st.session_state.current_s_time = s_input
                st.rerun()
        
        with col3:
            if st.button("🧹 Effacer", use_container_width=True):
                st.session_state.current_p_time = None
                st.session_state.current_s_time = None
                st.rerun()
        
        # Résumé des picks
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.session_state.current_p_time:
                st.metric("⚡ P", f"{st.session_state.current_p_time:.3f} µs")
            else:
                st.metric("⚡ P", "—")
        with col2:
            if st.session_state.current_s_time:
                st.metric("📈 S", f"{st.session_state.current_s_time:.3f} µs")
            else:
                st.metric("📈 S", "—")

else:
    # Message si aucun fichier n'est trouvé
    st.markdown("""
    <div style="text-align: center; padding: 40px 20px; background-color: #1e2130; border-radius: 10px; border: 1px solid #333;">
        <h2 style="color: #4a9eff;">🌊 WavePicker</h2>
        <p style="color: #e0e0e0;">Interface pour le picking manuel des ondes P et S</p>
        <br>
        <p style="color: #888888;">📁 Aucun fichier trouvé dans le dossier <code>data/</code></p>
        <p style="color: #888888;">Créez un dossier <code>data</code> dans votre dépôt et mettez vos fichiers <code>*CH1.txt</code></p>
        <br>
        <p style="color: #666666; font-size: 12px;">
            Format des fichiers : 2 colonnes (temps, amplitude) séparées par des virgules
        </p>
    </div>
    """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.caption("🌊 WavePicker - P & S Wave Picker • Cliquez sur le graphique pour placer les marqueurs")
