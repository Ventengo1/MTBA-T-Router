import csv
import networkx as nx
import requests
import os
import math
from dotenv import load_dotenv



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

headers = {"x-api-key": API_KEY} if API_KEY != os.getenv("MBTA_API_KEY") else {}


G = nx.Graph()

print("Loading MBTA data and analyzing stops")

response = requests.get(f"{BASE_URL}/stops?filter[route_type]=0,1", headers=headers)

#adding error stuff

if response.status_code != 200:
    print(f"Error fetching data from MBTA API: {response.status_code}")
    exit()

stops_data = response.json().get('data', [])

for stop in stops_data:
    attributes = stop.get('attributes', {})
    stop_id = stop.get('id')
    name = attributes.get('name')
    lat = attributes.get('latitude')
    lon = attributes.get('longitude')

    #classify station environment
    structure = "underground" if name in UNDERGROUND_STATIONS else "surface"

    G.add_node(stop_id, name=name, structure=structure, lat=lat, lon=lon)

print("Successfully loaded stations from api")


print("Working on track connections")

lines_response = requests.get(f"{BASE_URL}/routes?filter[type]=0,1", headers=headers)
routes_data = lines_response.json().get('data', [])

edges_added = 0
for route in routes_data:
    route_id = route.get('id')
    line_name = route.get('attributes', {}).get('long_name')

    #get order esqenune of stiaosn now

    stops_on_route_resp = requests.get(f"{BASE_URL}/stops?filter[route]={route_id}", headers=headers)
    route_stops = stops_on_route_resp.json().get('data', [])

    #translate route to parent hubs

    hub_ids_on_route = []
    for s in route_stops:
        parent = s.get('relationships', {}).get('parent_station', {}).get('data', {})
        parent_id = parent.get('id') if parent else None
        
        if parent_id in G.nodes and parent_id not in hub_ids_on_route:
            hub_ids_on_route.append(parent_id)
        elif s.get('id') in G.nodes and s.get('id') not in hub_ids_on_route:
            hub_ids_on_route.append(s.get('id'))

    for i in range(len(hub_ids_on_route) - 1):

        u = hub_ids_on_route[i]
        v = hub_ids_on_route[i+1]
        if u != v and not G.has_edge(u, v):
            G.add_edge(u, v, time=2, line=line_name)
            edges_added += 1
print(f" Tracks all linked, Finallyaks! Loaded {edges_added} system connections across all lines")

#gps stuff now

def geocode_address(address_str):
    """Converts a street name string into latitude and longitude via Nominatim"""
    url = f"https://nominatim.openstreetmap.org/search?q={address_str},+Boston&format=json&limit=1"
    res = requests.get(url, headers={"User-Agent": "mbta_router_app"})
    if res.status_code == 200 and len(res.json()) > 0:
        data = res.json()[0]
        return float(data['lat']), float(data['lon'])
    return None, None

def haversine_distance(lat1, lon1, lat2, lon2):
   """Calculates miles between two pairs of coordinates."""
   R = 3958.8 #---> radius of earth, gemini told me
   dLat = math.radians(lat2-lat1)
   dLon = math.radians(lon2 - lon1)
   a = math.sin(dLat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon/2) **2
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
        return base_time + (distance * 40)
 


    target_structure = G.nodes[v].get('structure', 'surface')

    if target_structure == 'underground':
        return base_time + 20
    
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
                    print(f"   [TRANSFER] At {G.nodes[prev_id]['name']} -> Switch to {detected_line}")
                current_line = detected_line
                print(f"    Ride [{current_line}] to: {name} ({structure})")

    except nx.NetworkXNoPath:
        print("E rror --> Path could not be resolved.")
        
    
    G.remove_node("START_NODE")
    G.remove_node("END_NODE")

# ---------------------------------------------------------------------
# EXECUTE POINT-TO-POINT SEARCH
# ---------------------------------------------------------------------
# Enter any real-world locations in the Boston area!
origin = "10 Jamaicaway"
destination = "Timeout Market"

build_point_to_point_route(origin, destination)