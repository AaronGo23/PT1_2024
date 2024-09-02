import math

def haversine(lat_origin, lng_origin, lat_driver, lng_driver):
    # Convert latitude and longitude from degrees to radians
    lat_origin, lng_origin, lat_driver, lng_driver = map(math.radians, [lat_origin, lng_origin, lat_driver, lng_driver])

    # Haversine formula
    dlat = lat_driver - lat_origin
    dlng = lng_driver - lng_origin
    a = math.sin(dlat / 2) ** 2 + math.cos(lat_origin) * math.cos(lat_driver) * math.sin(dlng / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    radius = 6371  # Radius of the Earth in kilometers. Use 3956 for miles. Determines return value units.
    distance = radius * c

    return distance

distance = haversine(46.945660, 6.841199, 46.942614, 6.846377)
print(distance)