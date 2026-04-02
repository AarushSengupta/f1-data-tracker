import fastf1
from fastf1 import plotting
import matplotlib.pyplot as plt
import streamlit as st
import mplcyberpunk

# 1. Page Configuration & Styling
st.set_page_config(page_title="F1 Pro Telemetry", layout="wide")
plt.style.use("cyberpunk")
plotting.setup_mpl(misc_mpl_mods=False)

# Helper function to convert raw seconds (e.g. 94.5) into M:SS.ms (e.g. 1:34.500)
def format_lap_time(seconds):
    if seconds is None or str(seconds) == 'nan':
        return "N/A"
    minutes = int(seconds // 60)
    rem_seconds = seconds % 60
    return f"{minutes}:{rem_seconds:06.3f}"

st.title("🏁 F1 Ultimate Analytics Dashboard")

# 2. Sidebar Controls
with st.sidebar:
    st.header("Race Settings")
    year = st.selectbox("Select Year", [2026, 2025, 2024], index=1)
    # Common F1 Tracks
    race_list = ["Bahrain", "Saudi Arabia", "Australia", "Japan", "Miami", "Monaco", "Spain", "Canada", "Austria", "Silverstone", "Hungary", "Spa", "Monza"]
    race = st.selectbox("Select Grand Prix", race_list)
    
    # Logic to load the entry list for the dropdown
    @st.cache_data
    def get_session_info(y, r):
        try:
            s = fastf1.get_session(y, r, 'R')
            s.load(laps=True, telemetry=False, weather=False)
            # Pull unique driver abbreviations from the results table
            driver_list = sorted(s.results['Abbreviation'].unique().tolist())
            return s, driver_list, None
        except Exception as e:
            return None, [], str(e)

    # Automatically fetch the drivers for the chosen race
    session, drivers, err = get_session_info(year, race)
    
    if drivers:
        selected_driver = st.selectbox("Select Driver", drivers)
    else:
        selected_driver = st.text_input("Driver Initials (Manual)", "VER").upper()

    st.markdown("---")
    metric = st.selectbox("Choose Analysis View", 
                         ["Tire Life & Strategy", "Race Pace (Lap Times)", "Pit Stop Performance"])
    
    run_btn = st.button("Generate Dashboard", use_container_width=True)

# 3. Main Logic Execution
if run_btn and session:
    laps = session.laps.pick_driver(selected_driver)
    
    if laps.empty:
        st.warning(f"⚠️ No data found for {selected_driver} at {race} {year}. They may have DNF'd or didn't start.")
    else:
        # Create a professional dark figure
        fig, ax = plt.subplots(figsize=(12, 6.5), facecolor='#0f0f0f')
        ax.set_facecolor('#0f0f0f')

        # --- VIEW 1: TIRE STRATEGY ---
        if metric == "Tire Life & Strategy":
            for stint in laps['Stint'].unique():
                stint_data = laps[laps['Stint'] == stint]
                if not stint_data.empty:
                    compound = stint_data['Compound'].iloc[0]
                    color = {'SOFT': '#FF0000', 'MEDIUM': '#FFFF00', 'HARD': '#FFFFFF'}.get(compound, '#00FF00')
                    
                    ax.plot(stint_data['LapNumber'], stint_data['TyreLife'], color=color, linewidth=4, label=f"Stint {int(stint)} ({compound})")
                    ax.fill_between(stint_data['LapNumber'], stint_data['TyreLife'], color=color, alpha=0.1)
            
            ax.set_ylabel("Laps on Current Tire Set", color='white')
            ax.set_title(f"TIRE DEGRADATION PROFILE: {selected_driver}", color='white', fontsize=16, pad=20)

        # --- VIEW 2: RACE PACE ---
        elif metric == "Race Pace (Lap Times)":
            quick = laps.pick_quicklaps()
            if not quick.empty:
                y_vals = quick['LapTime'].dt.total_seconds()
                ax.plot(quick['LapNumber'], y_vals, color='#00FFFF', marker='o', markersize=3, linewidth=1, label="Raw Lap Time")
                
                # Trend Line (5-lap Rolling Average)
                rolling = y_vals.rolling(window=5).mean()
                ax.plot(quick['LapNumber'], rolling, color='#FF00FF', linewidth=3, label="Pace Trend")
                
                ax.set_ylabel("Lap Time (Seconds)", color='white')
                ax.set_title(f"RACE PACE ANALYSIS: {selected_driver}", color='white', fontsize=16, pad=20)
            else:
                st.warning("Not enough clean laps to generate a pace chart.")

        # --- VIEW 3: PIT STOPS ---
        elif metric == "Pit Stop Performance":
            pits = laps[laps['PitInTime'].notna()]
            if not pits.empty:
                durations = (pits['Time'] - pits['PitInTime']).dt.total_seconds()
                ax.bar(pits['LapNumber'], durations, color='#FF8C00', alpha=0.8, label="Pit Lane Time")
                ax.set_ylabel("Seconds in Pit Lane", color='white')
                ax.set_title(f"PIT STOP DURATIONS: {selected_driver}", color='white', fontsize=16, pad=20)
            else:
                st.warning("No pit stop data recorded for this driver.")

        # 4. Final Visual Polish
        mplcyberpunk.add_glow_effects()
        
        # Legend De-duplication Fix
        handles, labels = plt.gca().get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        if by_label:
            ax.legend(by_label.values(), by_label.keys(), facecolor='#1a1a1a', edgecolor='white', loc='upper left')

        # Clean Borders & Grid
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.grid(color='#333333', linestyle='--', alpha=0.5)
        ax.tick_params(colors='white')
        
        # Render Graph
        st.pyplot(fig)
        
        # --- 5. KEY PERFORMANCE METRICS ---
        st.markdown("### Race Highlights")
        c1, c2, c3 = st.columns(3)
        
        # Fastest Lap in M:SS.ms
        f_lap_raw = laps['LapTime'].min().total_seconds()
        c1.metric("Fastest Lap", format_lap_time(f_lap_raw))
        
        # Total Pit Stops
        total_stints = int(laps['Stint'].max())
        c2.metric("Pit Stops", total_stints - 1)
        
        # Average Quick Lap Pace in M:SS.ms
        if not laps.pick_quicklaps().empty:
            avg_pace_raw = laps.pick_quicklaps()['LapTime'].mean().total_seconds()
            c3.metric("Avg Race Pace", format_lap_time(avg_pace_raw))
        else:
            c3.metric("Avg Race Pace", "N/A")

elif err:
    st.error(f"Failed to load F1 Session: {err}")
else:
    st.info("👈 Select a race and driver in the sidebar, then click 'Generate Dashboard'.")
