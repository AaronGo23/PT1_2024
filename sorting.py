### This function is to sort which driver is the best for this passenger
    
# Table test
# id(0), seats(1), rating(2), distance(3)

def sort_drivers(available_drivers, seats_requested):
    km = 5
    sorted_drivers = []
    print(f"Available drivers : {available_drivers}")
    
    # If the available_drivers isn't empty, run the sorting script
    if available_drivers:
        while not sorted_drivers and km <= 20:
            # Filter drivers by distance less than the current km value
            drivers_to_sort = [driver for driver in available_drivers if driver[3] < km and driver[1] >= seats_requested]
            
            if drivers_to_sort:
                # 3) Sort by the integer part of the rating (index 2 = rating)
                drivers_to_sort.sort(key=lambda x: x[2], reverse=True) # Highest rating comes first
                print(f"Drivers sorted by rating: {drivers_to_sort}")
                # 2) Sort by the number of seats (index 1 = seats)
                drivers_to_sort.sort(key=lambda x: x[1]) 
                print(f"Drivers sorted by seats: {drivers_to_sort}")
                # 1) Sort by distance (index 3 = distance)
                drivers_to_sort.sort(key=lambda x: x[3])
                print(f"Drivers sorted by distance: {drivers_to_sort}")
            
                sorted_drivers = drivers_to_sort
            else:
                km += 5
            
        # Test output
        if sorted_drivers:
            print("Sorted array by distance, seats and then rating:")
            for row in sorted_drivers:
                print(row)
        else:
            print("No drivers available in a range of 20 km.")
        
        return sorted_drivers
    else:
        print("No driver available in a range of 20 km. Please try again later")
        return []

if __name__ == "__main__":
    """ available_drivers = [
        ("john", 5, 3, 10.15),
        ("jeff", 2, 4.5, 4.60),
        ("johnny", 5, 3.1, 15.15),
        ("jerma", 2, 5.1, 15.30),
        ("jay", 4, 2.1, 20.15),
        ("jeremy", 5, 3, 6)
    ]
    sort_drivers(available_drivers) """
    sort_drivers()