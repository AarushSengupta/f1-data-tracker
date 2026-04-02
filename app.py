import fastf1
from fastf1 import plotting
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import pandas as pd

# 1. Page Configuration & Professional Theme
st.set_page_config(page_title="F1 Ultimate Strategy Pro", layout="wide")
plt_template = "plotly_dark"

# Helper function to convert raw seconds into M:SS.ms
def format_lap_time(seconds):
    if seconds is None or str(seconds) == 'nan' or seconds <= 0:
        return "N/A"
    minutes = int(seconds // 60)
    rem_seconds = seconds % 60
    return f"{minutes}:{rem_seconds:06.3f}"

# Official F1 Tire Colors
TIRE_COLORS = {
    'SOFT': '#FF0000', 'MEDIUM': '#FFFF00', 'HARD': '#FFFFFF',
    'INTERMEDIATE': '#00FF00', 'WET': '#0000FF'
}

st.title("🏁 F1 Ultimate Strategy Professional")

# 2. Sidebar Controls & Data Engine
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
        col1, col2 = st.columns(2)
        d1 = col1.selectbox("Driver 1 (Base)", drivers, index=0)
        
        # Safe teammate lookup
        try:
            team = session.results.loc[session.results['Abbreviation'] == d1, 'TeamName'].iloc[0]
            tm = session.results.loc[(session.results['TeamName'] == team) & (session.results['Abbreviation'] != d1), 'Abbreviation']
            d2_suggest = tm.iloc[0] if not tm.empty else drivers[1]
        except:
            d2_suggest = drivers[1]
            
        d2 = col2.selectbox("Driver 2 (Rival)", drivers, index=drivers.index(d2_suggest))

    st.markdown("---")
    metric = st.selectbox("Analysis View", 
                         ["Tire & Stint Map", "Race Pace & Sectors", "Direct Pace Gap", "Weather Context"])
    
    run_btn = st.button("Update Analysis", use_container_width=True)

# 3. Graph Styling
plotly_layout = go.Layout(
    paper_bgcolor='#0f0f0f', plot_bgcolor='#0f0f0f', font=dict(color='#FFFFFF'),
    xaxis=dict(gridcolor='#333333', tickcolor='#FFFFFF'),
    yaxis=dict(gridcolor='#333333', tickcolor='#FFFFFF'),
    hovermode='x unified', margin=dict(l=40, r=40, t=60, b=40),
    legend=dict(bgcolor='rgba(0,0,0,0)', bordercolor='#FFFFFF', borderwidth=1)
)

# 4. Main App Logic
if run_btn and session:
    laps1 = session.laps.pick_driver(d1)
    laps2 = session.laps.pick_driver(d2)
    
    if laps1.empty or laps2.empty:
        st.error(f"One of the selected drivers ( {d1} or {d2} ) has no data for this race.")
    else:
        st.header(f"{metric.upper()}: {d1} vs {d2}")

        # --- VIEW 1: TIRE & STINT MAP ---
        if metric == "Tire & Stint Map":
            fig = go.Figure()
            for dr, l_data in [(d1, laps1), (d2, laps2)]:
                for stint in l_data['Stint'].unique():
                    s_data = l_data[l_data['Stint'] == stint]
                    if not s_data.empty:
                        cmp = s_data['Compound'].iloc[0]
                        color = TIRE_COLORS.get(cmp, '#808080')
                        # Use horizontal bars to show stint duration
                        fig.add_trace(go.Bar(
                            name=f"{dr} Stint {int(stint)} ({cmp})",
                            x=[len(s_data)], y=[dr], orientation='h',
                            marker=dict(color=color, line=dict(color='white', width=1)),
                            hovertemplate=f"{dr} | {cmp}<br>Laps: %{{x}}<extra></extra>"
                        ))
            fig.update_layout(plotly_layout, barmode='stack', title="Race Strategy: Stint Length Comparison")
            st.plotly_chart(fig, use_container_width=True)

        # --- VIEW 2: RACE PACE & SECTORS ---
        elif metric == "Race Pace & Sectors":
            col_a, col_b = st.columns(2)
            
            # Pace Trend Chart
            fig_pace = go.Figure()
            for dr, l_data, color in [(d1, laps1, '#00FFFF'), (d2, laps2, '#FF00FF')]:
                quick = l_data.pick_quicklaps()
                y_vals = quick['LapTime'].dt.total_seconds()
                fig_pace.add_trace(go.Scatter(x=quick['LapNumber'], y=y_vals.rolling(5).mean(), 
                                              name=f"{dr} Pace Trend", line=dict(color=color, width=4)))
            fig_pace.update_layout(plotly_layout, title="5-Lap Rolling Average Pace", yaxis=dict(autorange="reversed"))
            col_a.plotly_chart(fig_pace, use_container_width=True)
            
            # Sector Analysis Chart
            sector_data = []
            for dr, l_data in [(d1, laps1), (d2, laps2)]:
                fastest = l_data.pick_fastest()
                for s in ['Sector1Time', 'Sector2Time', 'Sector3Time']:
                    sector_data.append({'Driver': dr, 'Sector': s.replace('Time', ''), 'Time': fastest[s].total_seconds()})
            
            df_s = pd.DataFrame(sector_data)
            fig_s = px.bar(df_s, x='Sector', y='Time', color='Driver', barmode='group', template=plt_template, title="Best Individual Sectors")
            col_b.plotly_chart(fig_s, use_container_width=True)

        # --- VIEW 3: DIRECT PACE GAP ---
        elif metric == "Direct Pace Gap":
            l1_sub = laps1[['LapNumber', 'Time']].copy(); l1_sub['Abs1'] = l1_sub['Time'].dt.total_seconds()
            l2_sub = laps2[['LapNumber', 'Time']].copy(); l2_sub['Abs2'] = l2_sub['Time'].dt.total_seconds()
            merged = pd.merge(l1_sub, l2_sub, on='LapNumber')
            merged['Gap'] = merged['Abs2'] - merged['Abs1'] # Positive = D2 is behind

            fig = go.Figure()
            fig.add_shape(type="line", x0=merged['LapNumber'].min(), y0=0, x1=merged['LapNumber'].max(), y1=0, line=dict(color="white", width=2, dash="dash"))
            fig.add_trace(go.Scatter(x=merged['LapNumber'], y=merged['Gap'], fill='tozeroy', line=dict(color='#00FF00', width=4), name=f"{d2} relative to {d1}"))
            fig.update_layout(plotly_layout, title=f"Gap Chart: {d2} vs {d1}", yaxis=dict(autorange="reversed"), yaxis_title="Gap (Seconds)")
            st.plotly_chart(fig, use_container_width=True)

        # --- VIEW 4: WEATHER ---
        elif metric == "Weather Context":
            weather = session.laps.get_weather_data()
            weather['Min'] = weather['Time'].dt.total_seconds() / 60
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=weather['Min'], y=weather['TrackTemp'], name="Track Temp", line=dict(color='#00FFFF')))
            fig.add_trace(go.Scatter(x=weather['Min'], y=weather['AirTemp'], name="Air Temp", line=dict(color='#FF00FF')))
            fig.update_layout(plotly_layout, title="Race Weather Conditions", yaxis_title="Temp (°C)", xaxis_title="Race Minutes")
            st.plotly_chart(fig, use_container_width=True)

        # --- 5. TOP-LEVEL METRICS ---
        st.markdown("---")
        m1, m2, m3 = st.columns(3)
        f1 = laps1['LapTime'].min().total_seconds()
        f2 = laps2['LapTime'].min().total_seconds()
        m1.metric(f"Fastest Lap ({d1})", format_lap_time(f1))
        m2.metric(f"Fastest Lap ({d2})", format_lap_time(f2))
        m3.metric("Top Speed (ST)", f"{int(laps1.pick_fastest()['SpeedST'])} km/h", f"vs {int(laps2.pick_fastest()['SpeedST'])} km/h")

elif err:
    st.error(f"Error loading session: {err}")
else:
    st.info("👈 Set your race parameters in the sidebar and click 'Update Analysis'.")
