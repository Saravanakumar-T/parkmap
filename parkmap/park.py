import streamlit as st
import pandas as pd
import osmnx as ox
import networkx as nx
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import folium_static
import random
import time

# --- Streamlit Title ---
st.title("🚗 Chennai Smart Parking Route Finder with Data Extraction")

# --- File Upload ---
st.sidebar.header("📂 Upload Parking Data (CSV)")
uploaded_file = st.sidebar.file_uploader("Upload a CSV file", type=["csv"])

# --- Load Graph Data with Caching ---
place_name = "Chennai, India"

@st.cache_data
def load_graph():
    """Load or fetch the graph for the specified place."""
    for attempt in range(3):
        try:
            return ox.graph_from_place(place_name, network_type="drive")
        except Exception:
            st.warning(f"Attempt {attempt + 1}: Retrying in 5 seconds...")
            time.sleep(5)
    st.error("❌ Failed to load road network. Check your connection and try again.")
    return None

st.sidebar.write("🔄 Loading Map Data...")
graph = load_graph()

if graph is None or len(graph.edges) == 0:
    st.error("❌ No roads found in the graph. Please check the region.")
    st.stop()
else:
    st.success(f"✅ Map loaded with {len(graph.edges)} edges.")

# --- Data Extraction and Display ---
if uploaded_file:
    df = pd.read_csv(uploaded_file)
    st.write("### 📊 Parking Data Preview", df.head())

    # Extract Parking Details
    if {'Latitude', 'Longitude', 'Action'}.issubset(df.columns):
        congested_df = df[df["Action"].isin(["Searching", "Left"])]
        available_df = df[df["Action"] == "Parked"]
        st.write(f"🔴 **Congested Spots:** {len(congested_df)}")
        st.write(f"🟢 **Available Spots:** {len(available_df)}")
    else:
        st.warning("⚠️ CSV file missing required columns: Latitude, Longitude, Action.")
        congested_df = available_df = pd.DataFrame()
else:
    congested_df = available_df = pd.DataFrame()

# --- Route Generation Controls ---
st.sidebar.header("🔀 Route Generator")
num_routes = st.sidebar.slider("Number of Routes", min_value=1, max_value=5, value=3)

# --- Generate Random Routes ---
st.write("### 🔥 Random Routes with Parking Data")
m = folium.Map(location=[13.0827, 80.2707], zoom_start=12)
marker_cluster = MarkerCluster().add_to(m)

nodes = list(graph.nodes())  # Cache node list for performance

for _ in range(num_routes):
    if len(nodes) < 2:
        st.error("❌ Not enough nodes in the graph to generate routes.")
        break

    try:
        orig_node, dest_node = random.sample(nodes, 2)
        if nx.has_path(graph, orig_node, dest_node):
            route = nx.shortest_path(graph, orig_node, dest_node, weight="length")
            route_coords = [(graph.nodes[node]['y'], graph.nodes[node]['x']) for node in route]

            folium.PolyLine(route_coords, color=random.choice(['blue', 'green', 'purple', 'orange']),
                            weight=5, opacity=0.8, tooltip="Random Route").add_to(m)

            folium.Marker([graph.nodes[orig_node]['y'], graph.nodes[orig_node]['x']],
                          popup="Start Point", icon=folium.Icon(color="green")).add_to(marker_cluster)
            folium.Marker([graph.nodes[dest_node]['y'], graph.nodes[dest_node]['x']],
                          popup="Destination", icon=folium.Icon(color="red")).add_to(marker_cluster)
        else:
            st.warning("⚠️ No path found between selected nodes.")
    except Exception as e:
        st.error(f"❌ Error generating route: {e}")

# --- Add Parking Markers (from uploaded file) ---
if not congested_df.empty and not available_df.empty:
    for _, row in congested_df.iterrows():
        folium.Marker([row["Latitude"], row["Longitude"]], popup="🚦 Congested Parking Spot",
                      icon=folium.Icon(color="red")).add_to(marker_cluster)

    for _, row in available_df.iterrows():
        folium.Marker([row["Latitude"], row["Longitude"]], popup="✅ Available Parking Spot",
                      icon=folium.Icon(color="green")).add_to(marker_cluster)

# --- Display the map ---
folium_static(m)
