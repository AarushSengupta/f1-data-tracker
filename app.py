import fastf1
from fastf1 import plotting
import matplotlib.pyplot as plt
import streamlit as st
import mplcyberpunk

# 1. Page Configuration
st.set_page_config(page_title="F1 Pro Telemetry", layout="wide")
plt.style.use("cyberpunk")
plotting.setup_mpl(misc_mpl_mods=False)

st.title("🏁 F1 Ultimate Analytics Dashboard")

# 2. Sidebar Controls
with st.sidebar:
    st.header("Race Settings")
    year = st.selectbox("Select Year", [2026, 2025, 2024], index=1)
    race = st.selectbox("Select Grand Prix", ["Bahrain", "Saudi Arabia", "Australia", "Japan", "Miami", "Monaco", "Silverstone", "Spa", "Monza"])
    driver = st.text_input("Driver Initials (e.g., VER, HAM, NOR)", "VER").upper()
    
    st.markdown("---")
    metric = st.selectbox("Choose Analysis View", 
                         ["Tire Life & Strategy", "Race Pace (Lap Times)", "Pit Stop Performance"])
    
    run_btn = st.button("Generate Dashboard", use_container_width=True)

# 3. Data Loading Engine
@st.cache_data
def get_f1_data(y, r, d):
    try:
        session = fastf1.get_session(y, r, 'R')
        session.load(laps=True, telemetry=False, weather=False)
        driver_laps = session.laps.pick_driver(d)
        return driver_laps, None
    except Exception as e:
        return None, str(e)

# 4. Dashboard Logic
if run_btn:
    laps, error = get_f1_data(year, race, driver)
    
    if error:
        st.error(f"❌ Connection Error: {error}")
    elif laps.empty:
        st.warning(f"⚠️ No data found for {driver} at {race} {year}.")
    else:
        # Create a high-end dark figure
        fig, ax = plt.subplots(figsize=(12, 6.5), facecolor='#0f0f0f')
        ax.set_facecolor('#0f0f0f')

        # --- OPTION 1: TIRE STRATEGY (The Smooth & Fixed Version) ---
        if metric == "Tire Life & Strategy":
            for stint in laps['Stint'].unique():
                stint_data = laps[laps['Stint'] == stint]
                compound = stint_data['Compound'].iloc[0]
                
                # Official F1 Colors
                color_map = {'SOFT': '#FF0000', 'MEDIUM': '#FFFF00', 'HARD': '#FFFFFF'}
                color = color_map.get(compound, '#00FF00')
                
                # Plot the line and the "Smooth Fill"
                ax.plot(stint_data['LapNumber'], stint_data['TyreLife'], 
                        color=color, linewidth=4, label=f"Stint {int(stint)} ({compound})")
                ax.fill_between(stint_data['LapNumber'], stint_data['TyreLife'], 
                                color=color, alpha=0.1)
            
            ax.set_ylabel("Laps on Current Tire Set", color='white')
            ax.set_title(f"TIRE DEGRADATION PROFILE: {driver}", color='white', fontsize=16, pad=20)

        # --- OPTION 2: RACE PACE ---
        elif metric == "Race Pace (Lap Times)":
            quick_laps = laps.pick_quicklaps()
            # Convert lap time to seconds for plotting
            y_values = quick_laps['LapTime'].dt.total_seconds()
            
            ax.plot(quick_laps['LapNumber'], y_values, color='#00FFFF', marker='o', markersize=3, linewidth=1, label="Raw Lap Time")
            
            # Trend Line (5-lap Rolling Average)
            rolling = y_values.rolling(window=5).mean()
            ax.plot(quick_laps['LapNumber'], rolling, color='#FF00FF', linewidth=3, label="Pace Trend")
            
            ax.set_ylabel("Lap Time (Seconds)", color='white')
            ax.set_title(f"RACE PACE ANALYSIS: {driver}", color='white', fontsize=16, pad=20)

        # --- OPTION 3: PIT STOPS ---
        elif metric == "Pit Stop Performance":
            pit_stops = laps[laps['PitInTime'].notna()]
            if not pit_stops.empty:
                # Calculate pit duration in seconds
                pit_duration = (pit_stops['Time'] - pit_stops['PitInTime']).dt.total_seconds()
                ax.bar(pit_stops['LapNumber'], pit_duration, color='#FF8C00', alpha=0.8, label="Pit Lane Time")
                ax.set_ylabel("Seconds in Pit Lane", color='white')
                ax.set_title(f"PIT STOP DURATIONS: {driver}", color='white', fontsize=16, pad=20)
            else:
                st.warning("No pit stops recorded for this driver.")

        # --- POLISHING STEPS ---
        # Add Neon Glow Effects
        mplcyberpunk.add_glow_effects()
        
        # Clean Legend (Removes the repetitions)
        handles, labels = plt.gca().get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        ax.legend(by_label.values(), by_label.keys(), facecolor='#1a1a1a', edgecolor='white', loc='upper left')

        # Clean Borders
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.grid(color='#333333', linestyle='--', alpha=0.5)
        ax.tick_params(colors='white')

        # Display Graph
        st.pyplot(fig)
        
        # Key Performance Metrics (The big numbers)
        c1, c2, c3 = st.columns(3)
        c1.metric("Fastest Lap", f"{laps['LapTime'].min().total_seconds():.3f}s")
        c2.metric("Total Stops", int(laps['Stint'].max() - 1))
        c3.metric("Avg Tire Age", f"{int(laps['TyreLife'].mean())} Laps")

else:
    st.info("👈 Configure your race data in the sidebar and click 'Generate Dashboard' to begin.")
