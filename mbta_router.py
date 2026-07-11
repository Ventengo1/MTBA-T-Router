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

