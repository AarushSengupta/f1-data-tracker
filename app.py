import fastf1
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import pandas as pd

# 1. Page Configuration & Styling
st.set_page_config(page_title="F1 Pro Strategy Tool", layout="wide")

# Professional F1 Theme Colors
F1_BG = '#0f0f0f' 
F1_TEXT = '#FFFFFF'
F1_GRID = '#333333'

# Helper: Seconds -> M:SS.ms
def format_lap_time(seconds):
    if seconds is None or str(seconds) == 'nan' or seconds <= 0:
        return "N/A"
    minutes = int(seconds // 60)
    rem_seconds = seconds % 60
    return f"{minutes}:{rem_seconds:06.3f}"

# Official F1 Tire Colors
TIRE_COLORS = {'SOFT': '#FF0000', 'MEDIUM': '#FFFF00', 'HARD': '#FFFFFF', 
               'INTERMEDIATE': '#00FF00', 'WET': '#0000FF'}

st.title("🏁 F1 Ultimate Analytics & Strategy Dashboard")

# 2. Sidebar Setup & Data Loading
with st.sidebar:
    st.header("Race Settings")
    year = st.selectbox("Year", [2026, 2025, 2024], index=1)
    race_list = ["Bahrain", "Saudi Arabia", "Australia", "Japan", "Miami", "Monaco", "Spain", "Canada", "Silverstone", "Spa", "Monza"]
    race = st.selectbox("Grand Prix", race_list)
    
    @st.cache_data
    def load_full_session(y, r):
        try:
            s = fastf1.get_session(y, r, 'R')
            s.load() 
            d_list = sorted(s.results['Abbreviation'].unique().tolist())
            return s, d_list, None
        except Exception as e:
            return None, [], str(e)

    session, drivers, err = load_full_session(year, race)
    
    if drivers:
        colA, colB = st.columns(2)
        driver1 = colA.selectbox("Driver 1 (Base)", drivers, index=0)
        
        # --- SAFE TEAMMATE SEARCH ---
        try:
            # Find the team of Driver 1
            d1_team = session.results.loc[session.results['Abbreviation'] == driver1, 'TeamName'].iloc[0]
            
            # Find everyone else on that same team
            teammates = session.results.loc[
                (session.results['TeamName'] == d1_team) & 
                (session.results['Abbreviation'] != driver1), 
                'Abbreviation'
            ]
            
            # If a teammate is found, use them. If not, just pick the next driver in the list.
            t_code = teammates.iloc[0] if not teammates.empty else drivers[1]
        except:
            t_code = drivers[1] # Fallback if results are missing
            
        t_idx = drivers.index(t_code) if t_code in drivers else 1
        driver2 = colB.selectbox("Driver 2 (Rival)", drivers, index=t_idx)
    else:
        driver1 = st.text_input("Driver 1", "VER").upper()
        driver2 = st.text_input("Driver 2", "HAM").upper()

    st.markdown("---")
    metric = st.selectbox("Analysis View", 
                         ["Tire Life & Strategy", "Race Pace Comparison", "Pit Stop Performance", "Direct Pace Gap", "Weather Context"])
    
    run_btn = st.button("Update Dashboard", use_container_width=True)

# 3. Graph Layout Styling
plotly_layout = go.Layout(
    paper_bgcolor=F1_BG, plot_bgcolor=F1_BG, font=dict(color=F1_TEXT),
    xaxis=dict(gridcolor=F1_GRID, title='Race Lap', tickcolor=F1_TEXT),
    yaxis=dict(gridcolor=F1_GRID, tickcolor=F1_TEXT),
    hovermode='x unified', margin=dict(l=40, r=40, t=60, b=40),
    legend=dict(bgcolor='rgba(0,0,0,0)', bordercolor=F1_TEXT, borderwidth=1)
)

# 4. Main App Logic
if run_btn and session:
    laps1 = session.laps.pick_driver(driver1)
    laps2 = session.laps.pick_driver(driver2)
    
    if laps1.empty or laps2.empty:
        st.error("One of the selected drivers has no data for this race (DNS/DNF).")
    else:
        st.subheader(f"{metric}: {driver1} vs {driver2}")

        # --- VIEW 1: TIRE STRATEGY ---
        if metric == "Tire Life & Strategy":
            fig = go.Figure()
            for d, l_data, sym in [(driver1, laps1, 'circle'), (driver2, laps2, 'diamond')]:
                for stint in l_data['Stint'].unique():
                    s_data = l_data[l_data['Stint'] == stint]
                    if not s_data.empty:
                        cmp = s_data['Compound'].iloc[0]
                        color = TIRE_COLORS.get(cmp, '#808080')
                        fig.add_trace(go.Scatter(
                            x=s_data['LapNumber'], y=s_data['TyreLife'],
                            name=f"{d}: Stint {int(stint)} ({cmp})",
                            mode='markers+lines', marker=dict(color=color, symbol=sym, size=8),
                            line=dict(width=1, dash='dot'),
                            hovertemplate=f"{d} | Age: %{{y}} Laps<extra></extra>"
                        ))
            fig.update_layout(plotly_layout, yaxis_title="Laps on Set")
            st.plotly_chart(fig, use_container_width=True)

        # --- VIEW 2: RACE PACE ---
        elif metric == "Race Pace Comparison":
            fig = go.Figure()
            for d, l_data, color in [(driver1, laps1, '#00FFFF'), (driver2, laps2, '#FF00FF')]:
                quick = l_data.pick_quicklaps()
                y_vals = quick['LapTime'].dt.total_seconds()
                # Raw Laps
                fig.add_trace(go.Scatter(x=quick['LapNumber'], y=y_vals, name=f"{d} Raw",
                                         mode='markers', marker=dict(color=color, size=4), opacity=0.4))
                # Trend Line
                fig.add_trace(go.Scatter(x=quick['LapNumber'], y=y_vals.rolling(5).mean(), 
                                         name=f"{d} Pace Trend", line=dict(color=color, width=3)))
            fig.update_layout(plotly_layout, yaxis_title="Seconds", yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)

        # --- VIEW 3: PIT STOPS ---
        elif metric == "Pit Stop Performance":
            fig = go.Figure()
            for d, l_data, color in [(driver1, laps1, '#FF8C00'), (driver2, laps2, '#CCCCCC')]:
                pits = l_data[l_data['PitInTime'].notna()]
                durations = (pits['Time'] - pits['PitInTime']).dt.total_seconds()
                fig.add_trace(go.Bar(x=pits['LapNumber'], y=durations, name=f"{d} Pit Time", marker_color=color))
            fig.update_layout(plotly_layout, yaxis_title="Seconds", barmode='group')
            st.plotly_chart(fig, use_container_width=True)

        # --- VIEW 4: DIRECT PACE GAP (The "Interval" Tracker) ---
        elif metric == "Direct Pace Gap":
            l1_sub = laps1[['LapNumber', 'Time']].copy()
            l1_sub['Abs1'] = l1_sub['Time'].dt.total_seconds()
            l2_sub = laps2[['LapNumber', 'Time']].copy()
            l2_sub['Abs2'] = l2_sub['Time'].dt.total_seconds()
            
            merged = pd.merge(l1_sub, l2_sub, on='LapNumber')
            merged['Gap'] = merged['Abs2'] - merged['Abs1'] # + means Driver 2 is behind

            fig = go.Figure()
            fig.add_shape(type="line", x0=merged['LapNumber'].min(), y0=0, x1=merged['LapNumber'].max(), y1=0,
                          line=dict(color="white", width=2, dash="dash"))
            fig.add_trace(go.Scatter(x=merged['LapNumber'], y=merged['Gap'], fill='tozeroy',
                                     line=dict(color='#00FF00', width=4), name=f"Gap {driver2} to {driver1}"))
            fig.update_layout(plotly_layout, yaxis_title="Gap (Seconds)", yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)
            st.info(f"📊 Up = {driver2} is closer/ahead. Down = {driver1} is pulling away.")

        # --- VIEW 5: WEATHER ---
        elif metric == "Weather Context":
            weather = session.laps.get_weather_data()
            weather['Min'] = weather['Time'].dt.total_seconds() / 60
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=weather['Min'], y=weather['TrackTemp'], name="Track Temp", line=dict(color='#00FFFF')))
            fig.add_trace(go.Scatter(x=weather['Min'], y=weather['AirTemp'], name="Air Temp", line=dict(color='#FF00FF')))
            fig.update_layout(plotly_layout, yaxis_title="Temp (°C)", xaxis_title="Race Minutes")
            st.plotly_chart(fig, use_container_width=True)

        # 5. Bottom Metrics
        st.markdown("---")
        c1, c2, c3 = st.columns(3)
        f1 = laps1['LapTime'].min().total_seconds()
        f2 = laps2['LapTime'].min().total_seconds()
        c1.metric(f"Fastest Lap ({driver1})", format_lap_time(f1))
        c2.metric(f"Fastest Lap ({driver2})", format_lap_time(f2))
        c3.metric("Lap Delta", f"{abs(f1-f2):.3f}s", f"{driver1 if f1 < f2 else driver2} faster")

elif err:
    st.error(f"Error: {err}")
else:
    st.info("👈 Pick your drivers and click 'Update Dashboard' to see the telemetry.")
