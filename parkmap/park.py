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

# --- Define Place & Bounding Box ---
place_name = "Chennai, India"
graph_path = "chennai_graph.graphml"  # Cached graph file

# --- Load or Fetch Graph ---
st.sidebar.write("🔄 Loading Map Data...")

try:
    # Try loading from a cached file first
    graph = ox.load_graphml(graph_path)
    st.success("✅ Cached map data loaded.")
except FileNotFoundError:
    st.warning("⚠️ Cached data not found. Fetching new data...")

    attempt = 0
    while attempt < 3:
        try:
            graph = ox.graph_from_place(place_name, network_type="drive")
            ox.save_graphml(graph, graph_path)  # Save for future use
            st.success("✅ Map data fetched successfully.")
            break
        except Exception as e:
            attempt += 1
            st.warning(f"Attempt {attempt}: Failed to fetch map data. Retrying in 5 sec...")
            time.sleep(5)
    else:
        st.error("❌ Could not fetch map data. Check your connection or try later.")
        st.stop()

# --- Validate Graph ---
if len(graph.edges) == 0:
    st.error("❌ No roads found in the graph. Please check the region.")
    st.stop()

# --- Data Extraction and Display ---
if uploaded_file:
    df = pd.read_csv(uploaded_file)

    # Display File Preview
    st.write("### 📊 Parking Data Preview")
    st.write(df.head())

    # Extract Parking Details
    st.write("### 🚦 Extracted Parking Details")
    if {'Latitude', 'Longitude', 'Action'}.issubset(df.columns):
        congested_df = df[df["Action"].isin(["Searching", "Left"])]
        available_df = df[df["Action"] == "Parked"]

        st.write(f"🔴 **Congested Spots:** {len(congested_df)}")
        st.write(f"🟢 **Available Spots:** {len(available_df)}")
    else:
        st.warning("⚠️ CSV file missing required columns: Latitude, Longitude, Action.")
        congested_df = available_df = pd.DataFrame()
else:
    st.write("📂 Please upload a CSV file to analyze parking data.")
    congested_df = available_df = pd.DataFrame()

# --- Route Generation Controls ---
st.sidebar.header("🔀 Route Generator")
num_routes = st.sidebar.slider("Number of Routes", min_value=1, max_value=5, value=3)

# --- Generate Random Routes ---
st.write("### 🔥 Random Routes with Parking Data")
m = folium.Map(location=[13.0827, 80.2707], zoom_start=12)
marker_cluster = MarkerCluster().add_to(m)

for _ in range(num_routes):
    try:
        orig_node, dest_node = random.sample(list(graph.nodes()), 2)
        if nx.has_path(graph, orig_node, dest_node):
            route = nx.shortest_path(graph, orig_node, dest_node, weight="length")
            route_coords = [(graph.nodes[node]['y'], graph.nodes[node]['x']) for node in route]

            folium.PolyLine(
                locations=route_coords,
                color=random.choice(['blue', 'green', 'purple', 'orange']),
                weight=5, opacity=0.8, tooltip="Random Route"
            ).add_to(m)

            folium.Marker([graph.nodes[orig_node]['y'], graph.nodes[orig_node]['x']],
                          popup="Start Point", icon=folium.Icon(color="green")).add_to(marker_cluster)
            folium.Marker([graph.nodes[dest_node]['y'], graph.nodes[dest_node]['x']],
                          popup="Destination", icon=folium.Icon(color="red")).add_to(marker_cluster)
        else:
            st.warning("⚠️ No path found between random nodes.")
    except Exception as e:
        st.error(f"❌ Error generating route: {e}")

# --- Add Parking Markers (from uploaded file) ---
if not congested_df.empty and not available_df.empty:
    for _, row in congested_df.iterrows():
        folium.Marker([row["Latitude"], row["Longitude"]],
                      popup="🚦 Congested Parking Spot",
                      icon=folium.Icon(color="red")).add_to(marker_cluster)

    for _, row in available_df.iterrows():
        folium.Marker([row["Latitude"], row["Longitude"]],
                      popup="✅ Available Parking Spot",
                      icon=folium.Icon(color="green")).add_to(marker_cluster)

# --- Display the map ---
folium_static(m)
