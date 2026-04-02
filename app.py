import fastf1
import matplotlib.pyplot as plt
import streamlit as st
from fastf1 import plotting

# 1. Setup
st.set_page_config(page_title="F1 Ultimate Tracker", layout="wide")
plotting.setup_mpl(mpl_timedelta_support=True, misc_mpl_mods=False)

st.title("🏁 F1 Ultimate Data Dashboard")

# 2. Sidebar Controls
st.sidebar.header("Race Settings")
year = st.sidebar.selectbox("Year", [2026, 2025, 2024], index=1)
race = st.sidebar.selectbox("Grand Prix", ["Bahrain", "Saudi Arabia", "Australia", "Japan", "Miami", "Monaco", "Silverstone"])
driver_code = st.sidebar.text_input("Driver Code (e.g. VER, HAM, NOR)", "VER").upper()

# NEW: Metric Selector
metric = st.sidebar.selectbox("Select Metric to Track", 
                             ["Tire Strategy", "Lap Times (Pace)", "Pit Stop Durations"])

@st.cache_data
def load_data(y, r, d):
    try:
        session = fastf1.get_session(y, r, 'R')
        session.load(laps=True, telemetry=False, weather=False)
        laps = session.laps.pick_driver(d)
        return laps, None
    except Exception as e:
        return None, str(e)

# 3. Main App Logic
if st.sidebar.button("Run Analysis"):
    laps, error = load_data(year, race, driver_code)
    
    if error:
        st.error(f"Error: {error}")
    elif laps.empty:
        st.warning(f"No data for {driver_code} in {year} {race}")
    else:
        st.header(f"{metric}: {driver_code} at {race} {year}")
        fig, ax = plt.subplots(figsize=(12, 6))

        # --- OPTION 1: TIRE STRATEGY ---
        if metric == "Tire Strategy":
            for stint in laps['Stint'].unique():
                stint_data = laps[laps['Stint'] == stint]
                compound = stint_data['Compound'].iloc[0]
                color = {'SOFT': 'red', 'MEDIUM': 'yellow', 'HARD': 'white'}.get(compound, 'cyan')
                ax.plot(stint_data['LapNumber'], stint_data['TyreLife'], color=color, linewidth=3, label=f"Stint {int(stint)}")
            ax.set_ylabel("Laps on Tire Set")

        # --- OPTION 2: LAP TIMES ---
        elif metric == "Lap Times (Pace)":
            # We use 'pick_quicklaps' to hide slow laps like pit stops or Safety Cars
            quick_laps = laps.pick_quicklaps()
            ax.plot(quick_laps['LapNumber'], quick_laps['LapTime'], marker='o', color='magenta', linestyle='--')
            ax.set_ylabel("Lap Time (Duration)")
            st.info("💡 Note: Outliers (Pit stops/Safety Cars) are hidden to show true race pace.")

        # --- OPTION 3: PIT STOPS ---
        elif metric == "Pit Stop Durations":
            # Filter for laps where the driver actually entered the pits
            pit_stops = laps[laps['PitInTime'].notna()]
            if not pit_stops.empty:
                # We show how long they were in the pit lane
                ax.bar(pit_stops['LapNumber'], pit_stops['Time'] - pit_stops['PitInTime'], color='orange')
                ax.set_ylabel("Time in Pit Lane")
                st.write(f"Total Pit Stops: {len(pit_stops)}")
            else:
                st.warning("No pit stop data recorded for this driver.")

        ax.set_xlabel("Race Lap")
        ax.legend()
        st.pyplot(fig)
        
        # Display the raw data for the curious
        with st.expander("View Raw Lap Data"):
            st.dataframe(laps[['LapNumber', 'Stint', 'Compound', 'LapTime', 'TyreLife']])

else:
    st.info("Choose your settings and click 'Run Analysis' to generate the visuals.")
