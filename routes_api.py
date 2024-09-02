import requests
from datetime import datetime

def get_lat_lng(api_key, location) :
    # My Google Maps API key
    api_key = api_key
    
    # Call Geocode API to get the code of the origin and destination
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        'address': location,
        'key': api_key
    }
    response = requests.get(url, params=params)
    data = response.json()

    if data['status'] == 'OK':
        results = data.get('results', [])
        if results:
            location = results[0]['geometry']['location']
            lat = location['lat']
            lng = location['lng']
            print(f"Latitude: {lat}, Longitude: {lng}")
        else:
            print("No results found")
    else:
        print(f"Error: {data['status']} - {data.get('error_message', '')}")
        
    return (lat,lng)

def get_route_passenger(origin, destination, mode, date_db, arrival_hour=None, departure_hour=None):
    # Get the route from passenger POV, arrival_hour=None, departure_hour=None says that they are optional
    api_key = "AIzaSyCR5EJzIIeA5yKR53kWfjRKfVHp21KTqYI" 
    
    # Get the latitude and longitude of the locations to be able to send them in Routes API
    lat_origin, lng_origin = get_lat_lng(api_key, origin)
    lat_destination, lng_destination = get_lat_lng(api_key, destination)

    # Endpoint URL for the Routes API
    url = "https://routes.googleapis.com/directions/v2:computeRoutes"
    
    headers = {
        'Content-Type': 'application/json',
        'X-Goog-Api-Key': api_key,
        'X-Goog-FieldMask': 'routes.distanceMeters,routes.duration,routes.polyline.encodedPolyline'
    }
    
    body = {
        'origin': {
            'location': {
                'latLng': {
                    'latitude': lat_origin,
                    'longitude': lng_origin,
                }
            }
        },
        'destination': {
            'location': {
                'latLng': {
                    'latitude': lat_destination,
                    'longitude': lng_destination,
                }
            }
        },
        'travelMode': mode,
        'routingPreference': 'TRAFFIC_AWARE_OPTIMAL',
        'computeAlternativeRoutes': False,
        'requestedReferenceRoutes': ['FUEL_EFFICIENT'],
    }

    if departure_hour:
        departure_time_str = f"{date_db}T{departure_hour}:00"
        departure_time = datetime.strptime(departure_time_str, '%Y-%m-%dT%H:%M:%S')
        body['departureTime'] = departure_time.isoformat() + 'Z'
    elif arrival_hour:
        arrival_time_str = f"{date_db}T{arrival_hour}:00"
        arrival_time = datetime.strptime(arrival_time_str, '%Y-%m-%dT%H:%M:%S')
        body['arrivalTime'] = arrival_time.isoformat() + 'Z'    
    
    response = requests.post(url, json=body, headers=headers)
    #print(response)
    # Checking the status code of the response
    if response.status_code == 200:
        data = response.json()
        #print(data)
        if 'routes' in data:
            return {'routes': data['routes']}
        else:
            return {'error': f"Error: {data.get('status', 'UNKNOWN')} - {data.get('error_message', '')}"}
    else:
        return {'error': f"HTTP Error: {response.status_code} - {response.text}"}
    
def get_distance(origin, lat_driver, lng_driver):
    api_key = "AIzaSyCR5EJzIIeA5yKR53kWfjRKfVHp21KTqYI" 

    # Get the latitude and longitude of the locations to be able to send them in Routes API
    lat_origin, lng_origin = get_lat_lng(api_key, origin)
    
    # Endpoint URL for the Routes API
    url = "https://routes.googleapis.com/directions/v2:computeRoutes"
    
    headers = {
        'Content-Type': 'application/json',
        'X-Goog-Api-Key': api_key,
        'X-Goog-FieldMask': 'routes.distanceMeters,routes.duration,routes.polyline.encodedPolyline'
    }
    
    body = {
        'origin': {
            'location': {
                'latLng': {
                    'latitude': lat_origin,
                    'longitude': lng_origin,
                }
            }
        },
        'destination': {
            'location': {
                'latLng': {
                    'latitude': lat_driver,
                    'longitude': lng_driver,
                }
            }
        },
        'travelMode': "DRIVE",
        'routingPreference': 'TRAFFIC_AWARE_OPTIMAL',
        'computeAlternativeRoutes': False,
        'requestedReferenceRoutes': ['FUEL_EFFICIENT'],
    }   
    
    response = requests.post(url, json=body, headers=headers)
    #print(response)
    # Checking the status code of the response
    if response.status_code == 200:
        data = response.json()
        #print(data)
        if 'routes' in data and len(data['routes']) > 0:
            distance_meters = data['routes'][0]['distanceMeters']
            return distance_meters
        else:
            return {'error': f"Error: {data.get('status', 'UNKNOWN')} - {data.get('error_message', '')}"}
    else:
        return {'error': f"HTTP Error: {response.status_code} - {response.text}"}


if __name__ == "__main__":
    # Testing the function
    routes = get_route_passenger()
    #print(routes)
    #origin = "1600 Amphitheatre Parkway, Mountain View, CA"
    #lat_driver = 37.423021
    #lng_driver = -122.083739

    distance = get_distance()
    #print(f"The distance is {distance} meters.")