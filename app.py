import fastf1
from fastf1 import plotting
import matplotlib.pyplot as plt
import streamlit as st
import mplcyberpunk  # This makes it look "Pro"

# 1. Professional Styling
st.set_page_config(page_title="F1 Telemetry Pro", layout="wide")
plt.style.use("cyberpunk") # Applies dark background and neon colors
plotting.setup_mpl(misc_mpl_mods=False)

st.title("📊 F1 Professional Telemetry Dashboard")

# 2. Inputs
with st.sidebar:
    st.header("Race Setup")
    year = st.selectbox("Year", [2025, 2024])
    race = st.selectbox("Grand Prix", ["Silverstone", "Monza", "Spa", "Monaco"])
    driver = st.text_input("Driver (e.g., VEST, HAM, LEC)", "VER").upper()
    metric = st.selectbox("View", ["Tire Life & Strategy", "Race Pace (Lap Times)"])
    btn = st.button("Generate Pro Visuals")

@st.cache_data
def get_clean_data(y, r, d):
    s = fastf1.get_session(y, r, 'R')
    s.load(laps=True, telemetry=False)
    return s.laps.pick_driver(d)

# 3. The Visual Logic
if btn:
    laps = get_clean_data(year, race, driver)
    
    # Create the figure with a dark facecolor
    fig, ax = plt.subplots(figsize=(12, 7), facecolor='#0f0f0f')
    ax.set_facecolor('#0f0f0f')

    if metric == "Tire Life & Strategy":
        for stint in laps['Stint'].unique():
            data = laps[laps['Stint'] == stint]
            compound = data['Compound'].iloc[0]
            # Official F1 Compound Colors
            colors = {'SOFT': '#FF0000', 'MEDIUM': '#FFFF00', 'HARD': '#FFFFFF'}
            color = colors.get(compound, '#00FF00')
            
            ax.plot(data['LapNumber'], data['TyreLife'], color=color, linewidth=4, label=f"Stint {int(stint)}: {compound}")
        
        ax.set_ylabel("Laps on Set", color='white', fontsize=12)
        ax.set_title(f"TIRE DEGRADATION PROFILE: {driver}", color='white', fontsize=16, fontweight='bold')

    else:
        # Polished Lap Time Graph
        quick = laps.pick_quicklaps()
        ax.plot(quick['LapNumber'], quick['LapTime'], color='#00FFFF', marker='o', markersize=4, linewidth=2, label="Raw Lap Time")
        
        # Add a "Rolling Average" to show the trend
        rolling = quick['LapTime'].rolling(window=5).mean()
        ax.plot(quick['LapNumber'], rolling, color='#FF00FF', linewidth=3, label="Race Pace Trend (5-Lap Avg)")
        
        ax.set_ylabel("Lap Time", color='white', fontsize=12)
        ax.set_title(f"RACE PACE ANALYSIS: {driver}", color='white', fontsize=16, fontweight='bold')

    # Apply the Cyberpunk Glow
    mplcyberpunk.add_glow_effects()
    
    # Clean up the axes
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(color='#333333', linestyle='--')
    ax.tick_params(colors='white')
    ax.legend(facecolor='#0f0f0f', edgecolor='white', labelcolor='white')
    
    st.pyplot(fig)
    
    # Add a "Key Stats" section below the graph
    col1, col2, col3 = st.columns(3)
    col1.metric("Fastest Lap", str(laps['LapTime'].min())[7:15])
    col2.metric("Total Stints", int(laps['Stint'].max()))
    col3.metric("Avg Tire Age", f"{int(laps['TyreLife'].mean())} Laps")

else:
    st.info("👈 Use the sidebar to select your driver and hit 'Generate' to see the neon telemetry.")
