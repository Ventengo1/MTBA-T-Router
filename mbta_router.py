import csv
import networkx as nx
import requests
import os
import math
import streamlit as st
from dotenv import load_dotenv

# Redirect print statements directly to the Streamlit app
def print(*args, **kwargs):
    st.text(" ".join(map(str, args)))

st.title("MBTA T-Router")

origin = st.text_input("Enter a origin: ", "10 Jamaicaway")
destination = st.text_input("Enter destination", "Timeout Market")

load_dotenv()

API_KEY = os.getenv("MBTA_API_KEY")
BASE_URL = "https://api-v3.mbta.com"

UNDERGROUND_STATIONS = {
    "North Station", "Haymarket", "Government Center", "Park Street", 
    "Boylston", "Arlington", "Copley", "Hynes Convention Center", "Kenmore",
    "Downtown Crossing", "State", "South Station", "Chinatown", "Tufts Medical Center",
    "Back Bay", "Mass Ave", "Ruggles", "Roxbury Crossing", "Jackson Square", 
    "Stony Brook", "Green Street", "Forest Hills", "Malden Center", "Wellington", 
    "Assembly", "Sullivan Square", "Community College", "Maverick", "Airport", 
    "Wood Island", "Orient Heights", "Suffolk Downs", "Beachmont", "Revere Beach", 
    "Wonderland", "Aquarium", "Bowdoin", "Charles/MGH", "Kendall/MIT", "Central", 
    "Harvard", "Porter", "Davis", "Alewife", "Symphony", "Prudential", "Lechmere",
    "Science Park / West End", "Union Square", "East Somerville", "Gilman Square", 
    "Magoun Square", "Ball Square", "Medford/Tufts"
}

#Got this list from AI

headers = {"x-api-key": API_KEY} if API_KEY else {}

@st.cache_resource
def get_mbta_graph():
    G = nx.Graph()

    print("Loading MBTA data and analyzing stops")

    response = requests.get(f"{BASE_URL}/stops?filter[route_type]=0,1", headers=headers)

    #adding error stuff

    if response.status_code != 200:
        print(f"Error fetching data from MBTA API: {response.status_code}")
        return None

    stops_data = response.json().get('data', [])

    for stop in stops_data:
        attributes = stop.get('attributes', {})
        stop_id = stop.get('id')
        name = attributes.get('name')
        lat = attributes.get('latitude')
        lon  =  attributes.get('longitude')

        #classify station environment
        structure = "underground" if name in UNDERGROUND_STATIONS else "surface"

        G.add_node(stop_id, name=name, structure=structure, lat=lat, lon=lon)

    print("Successfully loaded stations from api")


    print("Working on track connections")


    routes_resp = requests.get(f"{BASE_URL}/routes?filter[type]=0,1", headers=headers)
    route_ids = [r['id'] for r in routes_resp.json().get('data', [])] if routes_resp.status_code == 200 else []
    print(f"  Found {len(route_ids)} subway/light-rail routes: {route_ids}")

    edges_added = 0

    if route_ids:
        lines_response = requests.get(
            f"{BASE_URL}/route_patterns?filter[route]={','.join(route_ids)}&include=representative_trip.stops",
            headers=headers
        )

        if lines_response.status_code == 200:
            payload = lines_response.json()
            route_patterns = payload.get('data', [])
            included = payload.get('included', [])

            trips_by_id = {item['id']: item for item in included if item.get('type') == 'trip'}
            stops_by_id = {item['id']: item for item in included if item.get('type') == 'stop'}

            print(f"  Found {len(route_patterns)} route patterns, {len(trips_by_id)} trips, {len(stops_by_id)} stops in response")

            for rp in route_patterns:
                line_name = rp.get('attributes', {}).get('name', 'MBTA Line')
                trip_rel = rp.get('relationships', {}).get('representative_trip', {}).get('data')
                if not trip_rel:
                    continue
                trip = trips_by_id.get(trip_rel['id'])
                if not trip:
                    continue

                stop_refs = trip.get('relationships', {}).get('stops', {}).get('data', [])

                hub_ids_on_route = []
                for ref in stop_refs:
                    sid = ref.get('id')
                    if sid in G.nodes and sid not in hub_ids_on_route:
                        hub_ids_on_route.append(sid)
                    else:
                        stop_obj = stops_by_id.get(sid)
                        if stop_obj:
                            parent_rel = stop_obj.get('relationships', {}).get('parent_station', {}).get('data')
                            parent_id = parent_rel.get('id') if parent_rel else None
                            if parent_id and parent_id in G.nodes and parent_id not in hub_ids_on_route:
                                hub_ids_on_route.append(parent_id)

                for i in range(len(hub_ids_on_route) - 1):
                    u = hub_ids_on_route[i]
                    v = hub_ids_on_route[i+1]
                    if u != v and not G.has_edge(u, v):
                        G.add_edge(u, v, time=2, line=line_name)
                        edges_added   += 1
        else:
            print(f"  Warning: route_patterns request failed with status {lines_response.status_code}: {lines_response.text[:300]}")
    else:
        print("  Warning: could not fetch route list, skipping track connections")

    print(f" Tracks all linked, Finallyaks! Loaded {edges_added} system connections across all lines")
    return G

# Initialize/Load cached graph
G = get_mbta_graph()

#gps stuff now

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def _resolve_with_gemini(place_query):
    if not GEMINI_API_KEY:
        return None

    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    gemini_headers = {"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"}
    prompt = f"Give me the single, exact, full mailing address (street number, street name, city, state) for this place in or near Boston, MA: '{place_query}'. Reply with ONLY the address, nothing else. If you genuinely don't know, reply with exactly: UNKNOWN"
    body = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        res = requests.post(url, headers=gemini_headers, json=body, timeout=8)
    except requests.exceptions.RequestException as e:
        print(f"  (Gemini request failed for '{place_query}': {e})")
        return None

    if res.status_code == 200:
        try:
            text = res.json()['candidates'][0]['content']['parts'][0]['text'].strip()
        except (KeyError, IndexError):
            return None
        if text == "UNKNOWN" or not text:
            return None
        return text
    else:
        print(f"  (Gemini returned status {res.status_code} for '{place_query}')")
        return None


def _geocode_nominatim(address_str):
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": f"{address_str}, Boston, MA", "format": "json", "limit": 1}
    req_headers = {"User-Agent": "mbta_router_app (personal project, contact: replace-with-your-email)"}

    try:
        res = requests.get(url, params=params, headers=req_headers, timeout=8)
    except requests.exceptions.RequestException as e:
        print(f"  (Nominatim request failed for '{address_str}': {e})")
        return None, None

    if res.status_code == 200:
        results = res.json()
        if results:
            data = results[0]
            return float(data['lat']), float(data['lon'])
        return None, None
    else:
        print(f"  (Nominatim returned status {res.status_code} for '{address_str}')")
        return None, None


LOCATIONIQ_API_KEY = os.getenv("LOCATIONIQ_API_KEY")

def _geocode_locationiq(address_str):
    """LocationIQ -- free tier, no credit card, better at business/POI names than raw Nominatim."""
    if not LOCATIONIQ_API_KEY:
        return None, None

    url = "https://us1.locationiq.com/v1/search"
    params = {
        "key": LOCATIONIQ_API_KEY,
        "q": f"{address_str}, Boston, MA",
        "format": "json",
        "limit": 1
    }

    try:
        res  = requests.get(url, params=params, timeout=8)
    except requests.exceptions.RequestException as e:
        print(f"  (LocationIQ request failed for '{address_str}': {e})")
        return None, None

    if res.status_code == 200:
        results = res.json()
        if results:
            data = results[0]
            return float(data['lat']), float(data['lon'])
        return None, None
    else:
        # rate limited or bad key or whatever, just fall through to the next geocoder
        print(f"  (LocationIQ returned status {res.status_code} for '{address_str}')")
        return None, None


def _geocode_photon(address_str):
    url = "https://photon.komoot.io/api/"
    params = {"q": f"{address_str}, Boston", "limit": 1, "lat": 42.3601, "lon": -71.0589}

    try:
        res = requests.get(url, params=params, timeout=8)
    except requests.exceptions.RequestException as e:
        print(f"  (Photon request failed for '{address_str}': {e})")
        return None, None

    if res.status_code == 200:
        features = res.json().get('features', [])
        if features:
            coords = features[0].get('geometry', {}).get('coordinates', [])
            if len(coords) == 2:
                return float(coords[1]), float(coords[0])  # GeoJSON is [lon, lat]
        return None, None
    else:
        print(f"  (Photon returned status {res.status_code} for '{address_str}')")
        return None, None


def geocode_address(address_str):

    lat, lon = _geocode_nominatim(address_str)
    if lat is not None:
        return lat, lon

    print(f"  (Nominatim found no results for '{address_str}', trying LocationIQ...)")
    lat, lon = _geocode_locationiq(address_str)
    if lat is not None:
        return lat, lon

    print(f"  (trying Photon...)")
    lat, lon = _geocode_photon(address_str)
    if lat is not None:
        return lat, lon

    print(f"  (all geocoders failed on '{address_str}', asking Gemini for the exact address...)")
    resolved = _resolve_with_gemini(address_str)
    if resolved:
        print(f"  (Gemini guessed '{resolved}' -- worth double-checking this is right)")
        lat, lon = _geocode_nominatim(resolved)
        if lat is not None:
            return lat, lon
        lat, lon = _geocode_locationiq(resolved)
        if lat is not None:
            return lat, lon
        lat, lon = _geocode_photon(resolved)
        if lat is not None:
            return lat, lon

    print(f"  (No geocoder could resolve '{address_str}' -- check spelling/formatting)")
    return None, None

def haversine_distance(lat1, lon1, lat2, lon2):
   """Calculates miles between two pairs of coordinates."""
   R = 3958.8 #---> radius of earth, gemini told me
   dLat = math.radians(lat2-lat1)
   dLon = math.radians(lon2 - lon1)
   a = math.sin(dLat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon/2)**2
   c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
   #this line above gmeini had to help me with, this distance stuff was really nwew to me
   return R * c



def custom_priority_weight(u, v, edge_attributes):
    edge_type = edge_attributes.get('type', 'transit')
    base_time = edge_attributes.get('time', 2)
    
    # If is wlaking, how far
    if edge_type == "walk":
        distance = edge_attributes.get('distance', 0)

        # Heavy Penalty: Multiply distance by 40 to prioritize sitting on trains over walking.. ---> Im kinda lazy :)
        weight = base_time + (distance * 40)

        # only unfavor boarding underground -- transferring/exiting underground is fine, no extra fare either way
        if u == "START_NODE":
            board_structure = G.nodes[v].get('structure', 'surface')
            if board_structure == 'underground':
                weight += 20

        return weight
 

    return base_time

def build_point_to_point_route(origin_addr, dest_addr):

    print(f"\nLocation stuff and planning low walk travl")
    orig_lat, orig_lon = geocode_address(origin_addr)

    dest_lat, dest_lon = geocode_address(dest_addr)
    
    if not orig_lat or not dest_lat:
        print("Error --> Could not determine GPS coordinates for addresses")
        return

    # Temporarily plant the start and end addresses as special nodes in the graph network
    G.add_node("START_NODE", name=origin_addr, type="location")
    G.add_node("END_NODE", name=dest_addr, type="location")


    for node, data in list(G.nodes(data=True)):
        if node in ["START_NODE", "END_NODE"]:
            continue

        st_lat, st_lon = data.get('lat'), data.get('lon')


        if st_lat and st_lon:
            # Connect origin to all stations

            dist_to_start = haversine_distance(orig_lat, orig_lon, st_lat, st_lon)

            walk_time_start = dist_to_start * 20  # Roughly 20 minutes per mile walking speed
            G.add_edge("START_NODE", node, time=walk_time_start, distance=dist_to_start, type="walk")

            # Connect final stations to destination
            dist_to_end = haversine_distance(dest_lat, dest_lon, st_lat, st_lon)
            walk_time_end = dist_to_end * 20
            G.add_edge(node, "END_NODE", time=walk_time_end, distance=dist_to_end, type="walk")

#spent a lot of reasearch time on this part
    try:
        path = nx.dijkstra_path(G, "START_NODE", "END_NODE", weight=custom_priority_weight)
        
   
        print(" CUSTOMIZED TRANSIT PLAN:")

        
        current_line = None
        for i in range(len(path)):
            node_id = path[i]
            
            if node_id == "START_NODE":
                print(f" START WALKING FROM: {origin_addr}")
                continue
            elif node_id == "END_NODE":
           
                prev_id = path[i-1]
                edge_data = G.get_edge_data(prev_id, node_id)
                final_dist  = edge_data.get('distance', 0)

                print(f"\n  Exit train and walk final {final_dist:.2f} miles to your destination.")
                print(f"\n ARRIVED AT: {dest_addr}!")
                continue
                
            name = G.nodes[node_id]['name']
            structure = G.nodes[node_id]['structure'].upper()
            
            # Look back at track properties
            prev_id = path[i-1]
            edge_data = G.get_edge_data(prev_id, node_id)

            segment_type = edge_data.get('type', 'transit')
            

            if segment_type == "walk":
                dist = edge_data.get('distance', 0)
                if prev_id == "START_NODE":

                    print(f"  Walk {dist:.2f} miles to nearest optimal station: {name} ({structure})")
                else:
                    print(f"\n  Exit train and walk final {dist:.2f} miles to your destination.")
            else:
                detected_line = edge_data.get('line', 'Transit Line')
                if current_line and current_line != detected_line:
                    print(f"    [TRANSFER] At {G.nodes[prev_id]['name']} -> Switch to {detected_line}")
                current_line = detected_line
                print(f"     Ride [{current_line}] to: {name} ({structure})")

    except nx.NetworkXNoPath:
        print("E rror --> Path could not be resolved.")
        
    
    G.remove_node("START_NODE")
    G.remove_node("END_NODE")


if st.button("Calculate Route"):
    if G is not None:
        build_point_to_point_route(origin, destination)