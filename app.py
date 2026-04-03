import fastf1
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import pandas as pd
import numpy as np

# 1. Page Configuration & Theme
st.set_page_config(page_title="F1 Race Engineer Pro", layout="wide")

# Professional F1 Theme Colors
F1_BG = '#0f0f0f' 
F1_TEXT = '#FFFFFF'
F1_GRID = '#333333'

# Helper: Convert seconds to M:SS.ms
def format_lap_time(seconds):
    if seconds is None or str(seconds) == 'nan' or seconds <= 0: return "N/A"
    minutes = int(seconds // 60)
    rem_seconds = seconds % 60
    return f"{minutes}:{rem_seconds:06.3f}"

# Official F1 Tire Colors
TIRE_COLORS = {'SOFT': '#FF0000', 'MEDIUM': '#FFFF00', 'HARD': '#FFFFFF', 
               'INTERMEDIATE': '#00FF00', 'WET': '#0000FF'}

st.title("🏎️ F1 Race Engineer: Ultimate Strategy & Telemetry Suite")

# 2. Sidebar Data Engine
with st.sidebar:
    st.header("Session Setup")
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
        c1, c2 = st.columns(2)
        d1 = c1.selectbox("Driver 1 (Base)", drivers, index=0)
        
        # Auto-suggest teammate
        try:
            team = session.results.loc[session.results['Abbreviation'] == d1, 'TeamName'].iloc[0]
            tm = session.results.loc[(session.results['TeamName'] == team) & (session.results['Abbreviation'] != d1), 'Abbreviation']
            d2_suggest = tm.iloc[0] if not tm.empty else drivers[1]
        except: d2_suggest = drivers[1]
            
        d2 = c2.selectbox("Driver 2 (Rival)", drivers, index=drivers.index(d2_suggest))

    st.markdown("---")
    metric = st.selectbox("Engineering View", 
                         ["Tire & Stint Map", "GPS Track Analysis", "Driver Inputs (Pedals)", "Strategy Predictor", "Direct Pace Gap"])
    
    run_btn = st.button("Run Full Analysis", use_container_width=True)

# 3. Global Plotly Styling
plotly_layout = go.Layout(
    paper_bgcolor=F1_BG, plot_bgcolor=F1_BG, font=dict(color=F1_TEXT),
    xaxis=dict(gridcolor=F1_GRID, tickcolor=F1_TEXT),
    yaxis=dict(gridcolor=F1_GRID, tickcolor=F1_TEXT),
    hovermode='x unified', margin=dict(l=50, r=50, t=50, b=50),
    legend=dict(bgcolor='rgba(0,0,0,0)', bordercolor=F1_TEXT, borderwidth=1)
)

# 4. Main Engineering Logic
if run_btn and session:
    laps1 = session.laps.pick_driver(d1)
    laps2 = session.laps.pick_driver(d2)
    
    if laps1.empty or laps2.empty:
        st.error("Missing data for one of the selected drivers.")
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
                        fig.add_trace(go.Bar(name=f"{dr} Stint {int(stint)} ({cmp})", x=[len(s_data)], y=[dr], 
                                             orientation='h', marker=dict(color=color, line=dict(color='white', width=1))))
            fig.update_layout(plotly_layout, barmode='stack', title="Race Strategy: Stint Length Comparison (Laps)")
            st.plotly_chart(fig, use_container_width=True)

        # --- VIEW 2: GPS TRACK ANALYSIS ---
        elif metric == "GPS Track Analysis":
            st.subheader(f"Speed Heatmap: {d1}")
            tel = laps1.pick_fastest().get_telemetry()
            fig = px.scatter(tel, x='X', y='Y', color='Speed', color_continuous_scale='Turbo', title=f"Fastest Lap Speed Map - {d1}")
            fig.update_traces(marker=dict(size=3))
            fig.update_layout(plotly_layout, xaxis=dict(showgrid=False, zeroline=False), yaxis=dict(showgrid=False, zeroline=False))
            st.plotly_chart(fig, use_container_width=True)

        # --- VIEW 3: DRIVER INPUTS (PEDALS) ---
        elif metric == "Driver Inputs (Pedals)":
            tel1 = laps1.pick_fastest().get_telemetry().add_distance()
            tel2 = laps2.pick_fastest().get_telemetry().add_distance()
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=tel1['Distance'], y=tel1['Throttle'], name=f"{d1} Throttle", line=dict(color='#00FFFF')))
            fig.add_trace(go.Scatter(x=tel2['Distance'], y=tel2['Throttle'], name=f"{d2} Throttle", line=dict(color='#FF00FF', dash='dot')))
            fig.update_layout(plotly_layout, title="Throttle Application (%) across Lap Distance", yaxis_title="Throttle %")
            st.plotly_chart(fig, use_container_width=True)
            
            fig_b = go.Figure()
            fig_b.add_trace(go.Scatter(x=tel1['Distance'], y=tel1['Brake'], name=f"{d1} Brake", fill='tozeroy', line=dict(color='red')))
            fig_b.add_trace(go.Scatter(x=tel2['Distance'], y=tel2['Brake'], name=f"{d2} Brake", line=dict(color='white', dash='dash')))
            fig_b.update_layout(plotly_layout, title="Braking Events", yaxis_title="Brake On/Off")
            st.plotly_chart(fig_b, use_container_width=True)

        # --- VIEW 4: STRATEGY PREDICTOR ---
        elif metric == "Strategy Predictor":
            q1 = laps1.pick_quicklaps()
            if len(q1) > 5:
                fit = np.polyfit(q1['TyreLife'], q1['LapTime'].dt.total_seconds(), 1)
                predict_fn = np.poly1d(fit)
                future_laps = np.linspace(0, 40, 40)
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=q1['TyreLife'], y=q1['LapTime'].dt.total_seconds(), mode='markers', name="Actual Pace", marker=dict(color='white')))
                fig.add_trace(go.Scatter(x=future_laps, y=predict_fn(future_laps), name="Predicted Decay", line=dict(color='red', width=4)))
                fig.update_layout(plotly_layout, title=f"Tire Performance Decay (Deg: {fit[0]:.4f}s/lap)", xaxis_title="Tire Age", yaxis_title="Seconds")
                st.plotly_chart(fig, use_container_width=True)
                st.warning(f"Strategy Alert: {d1} is losing {fit[0]:.3f}s per lap to tire wear.")

        # --- VIEW 5: DIRECT PACE GAP ---
        elif metric == "Direct Pace Gap":
            l1_sub = laps1[['LapNumber', 'Time']].copy(); l1_sub['Abs1'] = l1_sub['Time'].dt.total_seconds()
            l2_sub = laps2[['LapNumber', 'Time']].copy(); l2_sub['Abs2'] = l2_sub['Time'].dt.total_seconds()
            merged = pd.merge(l1_sub, l2_sub, on='LapNumber')
            merged['Gap'] = merged['Abs2'] - merged['Abs1']

            fig = go.Figure()
            fig.add_shape(type="line", x0=merged['LapNumber'].min(), y0=0, x1=merged['LapNumber'].max(), y1=0, line=dict(color="white", width=2, dash="dash"))
            fig.add_trace(go.Scatter(x=merged['LapNumber'], y=merged['Gap'], fill='tozeroy', line=dict(color='#00FF00', width=4), name=f"{d2} vs {d1}"))
            fig.update_layout(plotly_layout, title=f"Gap Chart: {d2} relative to {d1}", yaxis=dict(autorange="reversed"), yaxis_title="Seconds Behind/Ahead")
            st.plotly_chart(fig, use_container_width=True)

        # 5. Engineering Metrics
        st.markdown("---")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Fastest Lap", format_lap_time(laps1['LapTime'].min().total_seconds()))
        m2.metric("Top Speed (ST)", f"{int(laps1.pick_fastest()['SpeedST'])} km/h")
        m3.metric("Avg Throttle", f"{int(laps1.pick_fastest().get_telemetry()['Throttle'].mean())}%")
        m4.metric("Pit Window", f"Lap {int(laps1['LapNumber'].max()) + 2} (Est)")

elif err: st.error(f"Session Error: {err}")
else: st.info("Welcome, Engineer. Select your parameters to begin.")
