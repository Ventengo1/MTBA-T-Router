import csv
import networkx as nx

G = nx.Graph()

print("Loading MBTA data and analyzing stops")

surface_count = 0
underground_count = 0

# The definitive list of downtown underground subway station hubs in Boston.
# If a station is a major subway hub and NOT on this list, it's above ground!
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

with open ('stops.txt', mode = 'r', encoding = 'utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row.get('location_type') == '1':
            stop_id = row['stop_id']
            name = row['stop_name']

            # Make sure it's a primary subway system station, not a commuter rail stop
            if stop_id.startswith('place-'):
                
                # If the station name is in our downtown tunnel list, it's underground.
                # Otherwise, it's a street-level surface stop (like the Green Line branches)!
                if name in UNDERGROUND_STATIONS:
                    structure = "underground"
                    underground_count += 1
                else:
                    structure = "surface"
                    surface_count += 1
                
                # Add the real station to our map
                G.add_node(stop_id, name=name, structure=structure)

print(f"Successfully loaded {G.number_of_nodes()} subway hubs")
print(f"  Surface Stations: {surface_count}")
print(f"   Underground Stations: {underground_count} These are less favorable for what I want")
print(f" The surface stations {surface_count} are more favorable for what I want")

print("MBTA data loaded and analyzed successfully.")


#Part 2 of what I gotta do below----


#This block here should map the platforms and tracks back to their main hubs/parennt statiosn 
platform_to_hub = {}
with open('stops.txt', mode='r', encoding='utf-8') as f: #hopefully this is right...
    reader = csv.DictReader(f)
    for row in reader:
        parent = row.get('parent_station')
        stop_id = row.get('stop_id')

        if parent in G.nodes:
            platform_to_hub[stop_id] = parent


        elif stop_id in G.nodes:
            platform_to_hub[stop_id] = stop_id

print(f"Mapped {len(platform_to_hub)} platforms to parent hubs. AYAY!")

# This part below now should group the stop sequences by thier unique trip ud

trips = {}

with open('stop_times.txt', mode = "r", encoding = 'utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        trip_id = row['trip_id']
        stop_id = row["stop_id"]
        try:
            sequence = int(row['stop_sequence'])
        except ValueError: #Gemini told me to put this line here
            continue
        

        if trip_id not in trips:
            trips[trip_id] = []
        trips[trip_id].append((sequence, stop_id))

print(f"Gathered {len(trips)} unique train trips that its gotta process then... ")

#Third part of this phase 2 or whtever:

edges_added = 0
for trip_id, stop_list in trips.items():
    #here shoudl srot stops by their order on line, hopfully....
    stop_list.sort()

    for i in range(len(stop_list) - 1):
        raw_curr = stop_list[i][1]
        raw_next = stop_list[i+1][1]

        curr_hub = platform_to_hub.get(raw_curr)
        next_hub = platform_to_hub.get(raw_next)

        #not only add track if both endopoints are valid hubs
        if curr_hub and next_hub and curr_hub != next_hub:
            if not G.has_edge(curr_hub, next_hub):
                G.add_edge(curr_hub, next_hub, time=2)
                edges_added +=1 

print("Tracks all linked, finally...!!!!")


#phase 3 --> should do custom routing

def surface_priority_weight(u, v, edge_attributes):
    #Get base travel time between stations
    base_time = edge_attributes.get('time', 2)
                                    
    #check if statiosd is underground
    target_structure = G.nodes[v].get('structure', 'underground')

    if target_structure == 'underground':
        #add a penalty to underground stations to discourage against them
        return base_time + 20 #penalty of 20
    
    else:

        return base_time
    
    
start_station = "place-newto" #Newton Highlands --> surface
end_station = "place-gover" #Government Center --> underground

def print_detailed_route(path_ids, title):
    print(f"\n{title}:  ")

    for i in range(len(path_ids)):
        current_id = path_ids[i]
        current_name = G.nodes[current_id]['name']
        current_type = G.nodes[current_id]['structure']

        if i > 0:
            prev_id = path_ids[i-1]
            prev_type = G.nodes[prev_id]['structure']
            if prev_type != current_type:
                print(f" Level Change ---> Changing from {prev_type} to {current_type}")




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