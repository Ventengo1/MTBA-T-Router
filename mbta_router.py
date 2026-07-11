import csv
import networkx as nx
import requests


API_KEY = "98065d5be6414f3e9cb9657823dfe6cb"
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

headers = {"x-api-key": API_KEY} if API_KEY != "98065d5be6414f3e9cb9657823dfe6cb" else {}


G = nx.Graph()

print("Loading MBTA data and analyzing stops")

response = requests.get(f"{BASE_URL}/stops?filter[route_type]=0,1", headers=headers)

#adding error stuff

if response.status.code != 200:
    print(f"Error fetching data from MBTA API: {response.status_code}")
    exit()

stops_data = response.json().get('data', [])

for stop in stops_data:
    attributes = stop.get('attributes', {})
    stop_id = stop.get('id')
    name = attributes.get('name')

    #classify station environment
    structure = "underground" if name in UNDERGROUND_STATIONS else "surface"

    G.add_node(stop_id, name=name, structure=structure)

print("Successfully loaded stations from api")


print("Working on track connections")

lines_response = requests.get(f"{BASE_URL}/routes?filter[route_type]=0,1", headers=headers)
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



def custom_priority_weight(u, v, edge_attributes):
    #Get base travel time between stations
    base_time = edge_attributes.get('time', 2)
                                    
    #check if statiosd is underground
    target_structure = G.nodes[v].get('structure', 'underground')

    if target_structure == 'underground':
        #add a penalty to underground stations to discourage against them
        return base_time + 25 #penalty of 25
    else:
         return base_time

def print_detailed_route(path_ids, title):
    #Ok, now gotta make this look a lot better

    print(f"{title}:")
    currnet_line = 0
    tranfer_count = 0
    for i in range(len(path_ids)):
        current_id = path_ids[i]
        current_name = G.nodes[current_id]['name']
        current_type = G.nodes[current_id]['structure'].upper()

        #If not wat first station, look at what track being used 
        if i > 0:
            prev_id = path_ids[i]
            prev_name = G.nodes[prev_id]['name']

            detecteed_line = "Subway Link"
            if "place-dngl" in prev_id or "place_new" in prev_id or "Newton" in prev_name:
                detected_line = "Green Line D"
            elif "place"    




if G.has_node(start_station) and G.has_node(end_station):
    print(f"Finding optimal route from {G.nodes[start_station]['name']} to {G.nodes[end_station]['name']}...\n")

    # route calculation
    standard_path_ids = nx.dijkstra_path(G, start_station, end_station, weight='time')
   

    # Custom route calculation
    custom_path_ids = nx.dijkstra_path(G, start_station, end_station, weight=surface_priority_weight)
     #gemini helped me with line above and below, I get it now though
    

    print("Standard fastest route:")
    print_detailed_route(standard_path_ids, "Standard fastest route")

    print("\nCustom route prioritizing surface stations:")
    print_detailed_route(custom_path_ids, "Custom route prioritizing surface stations")

else:
    print("Error: One or both of the specified stations do not exist in the graph.")