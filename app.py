import fastf1
import matplotlib.pyplot as plt
import streamlit as st
from fastf1 import plotting

# 1. Page Config & Styling
st.set_page_config(page_title="F1 Tire Tracker", layout="wide")
plotting.setup_mpl(misc_mpl_mods=False)

st.title("🏎️ F1 Tire Strategy & Degradation")

# 2. Sidebar Dropdowns (The Controls)
st.sidebar.header("Race Settings")

# Dropdown for Year
selected_year = st.sidebar.selectbox("Select Year", [2026, 2025, 2024, 2023])

# Dropdown for Race (Common ones - you can add more!)
races = ["Bahrain", "Saudi Arabia", "Australia", "Japan", "China", "Miami", "Monaco", "Silverstone", "Monza"]
selected_race = st.sidebar.selectbox("Select Grand Prix", races)

# Text Input for Driver (3-letter code)
driver_code = st.sidebar.text_input("Driver Code (e.g. VER, HAM, LEC)", "VER").upper()

# 3. Data Loading Logic
@st.cache_data
def load_tire_data(year, race, driver):
    try:
        # Load the session
        session = fastf1.get_session(year, race, 'R')
        session.load(laps=True, telemetry=False, weather=False)
        
        # Filter for the specific driver
        driver_laps = session.laps.pick_driver(driver)
        return driver_laps, None
    except Exception as e:
        return None, str(e)

# 4. Main App Interface
if st.sidebar.button("Update Dashboard"):
    with st.spinner(f"Downloading {selected_year} {selected_race} data..."):
        laps, error = load_tire_data(selected_year, selected_race, driver_code)

    if error:
        st.error(f"Could not load data: {error}. Note: 2026 data only works for completed races!")
    elif laps.empty:
        st.warning(f"No data found for driver {driver_code} in this race.")
    else:
        # Success! Create the plot
        st.subheader(f"Strategy for {driver_code} at {selected_race} {selected_year}")
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Plot each stint with correct F1 colors
        for stint in laps['Stint'].unique():
            stint_data = laps[laps['Stint'] == stint]
            compound = stint_data['Compound'].iloc[0]
            
            # Map colors to tires
            color_map = {'SOFT': 'red', 'MEDIUM': 'yellow', 'HARD': 'white', 'INTERMEDIATE': 'green', 'WET': 'blue'}
            color = color_map.get(compound, 'gray')
            
            ax.plot(stint_data['LapNumber'], stint_data['TyreLife'], 
                    color=color, label=f"Stint {int(stint)} ({compound})", linewidth=3)

        ax.set_xlabel("Race Lap")
        ax.set_ylabel("Laps on Current Set")
        ax.legend()
        st.pyplot(fig)
        
        # Bonus: Show a small data table below
        st.write("### Stint Summary Table")
        st.dataframe(laps[['LapNumber', 'Stint', 'Compound', 'TyreLife']].tail(5))
else:
    st.info("Set your parameters in the sidebar and click 'Update Dashboard' to see the data.")