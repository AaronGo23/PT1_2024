import pytest
from app import app as flask_app, mysql
import MySQLdb
from datetime import datetime, timedelta
import time
import concurrent.futures
from unittest.mock import patch

# Retry operation for MySQL with a specified number of attempts
def retry_mysql_operation(operation, max_retries=3):
    for attempt in range(max_retries):
        try:
            return operation()
        except MySQLdb.OperationalError as e:
            print(f"MySQL OperationalError on attempt {attempt + 1}/{max_retries}: {e}")
            time.sleep(1)  # Wait a bit before retrying
    raise Exception(f"Operation failed after {max_retries} attempts")

# Function to clean up the database
def cleanup_database():
    def operation():
        with flask_app.app_context():
            cur = mysql.connection.cursor()
            try:
                cur.execute("DELETE FROM course")
                cur.execute("DELETE FROM conducteur")
                cur.execute("DELETE FROM passager")
                cur.execute("DELETE FROM possession")
                cur.execute("DELETE FROM voiture")
                cur.execute("DELETE FROM utilisateur")
                mysql.connection.commit()
            except MySQLdb.Error as e:
                print(f"MySQL Error during setup/teardown: {e}")
                raise
            finally:
                cur.close()
    retry_mysql_operation(operation)

# Fixture to clean up the database before each test
@pytest.fixture(autouse=True)
def setup_and_teardown():
    cleanup_database()  # Clean the database before each test
    yield  # Continue to the test without cleaning up after
    # No teardown, so the database state is preserved after the test


# Function to refresh MySQL connection
def refresh_mysql_connection():
    try:
        mysql.connection.ping(True)
        print("MySQL connection refreshed")
    except MySQLdb.OperationalError:
        mysql.connection.reconnect()
        print("MySQL connection reconnected")

def create_user(client, email, password, firstname, lastname, dob):
    return client.post('/signup/', data={
        'email': email,
        'password': password,
        'firstname': firstname,
        'lastname': lastname,
        'dob': dob
    }, follow_redirects=True)

# Test for signing up a driver
def test_signup_driver(client):
    refresh_mysql_connection()
    response = create_user(client, 'driver@gmail.com', 'password123', 'Driver', 'User', '2000-01-01')
    print("Signup Driver Response:", response.data)
    assert response.status_code == 200
    assert b"select_role" in response.data

# Test for signing up a passenger
def test_signup_passenger(client):
    refresh_mysql_connection()
    response = create_user(client, 'passenger@gmail.com', 'password123', 'Passenger', 'User', '2000-01-01')
    print("Signup Passenger Response:", response.data)
    assert response.status_code == 200
    assert b"select_role" in response.data

# Test for logging in a driver
def test_login_driver(client):
    refresh_mysql_connection()
    # Ensure driver exists
    create_user(client, 'driver@gmail.com', 'password123', 'Driver', 'User', '2000-01-01')
    response = client.post('/login/', data={
        'email': 'driver@gmail.com',
        'password': 'password123'
    }, follow_redirects=True)
    print("Login Driver Response:", response.data)
    assert response.status_code == 200
    assert b"select_role" in response.data

# Test for logging in a passenger
def test_login_passenger(client):
    refresh_mysql_connection()
    # Ensure passenger exists
    create_user(client, 'passenger@gmail.com', 'password123', 'Passenger', 'User', '2000-01-01')
    response = client.post('/login/', data={
        'email': 'passenger@gmail.com',
        'password': 'password123'
    }, follow_redirects=True)
    print("Login Passenger Response:", response.data)
    assert response.status_code == 200
    assert b"select_role" in response.data

# Test for selecting role as driver
def test_select_role_driver(client):
    refresh_mysql_connection()
    create_user(client, 'driver@gmail.com', 'password123', 'Driver', 'User', '2000-01-01')
    client.post('/login/', data={
        'email': 'driver@gmail.com',
        'password': 'password123'
    }, follow_redirects=True)
    response = client.post('/select_role/', data={'role': 'driver'}, follow_redirects=True)
    print("Select Role Driver Response:", response.data)
    assert response.status_code == 200
    assert b"select_vehicle" in response.data

# Test for selecting role as passenger
def test_select_role_passenger(client):
    refresh_mysql_connection()
    create_user(client, 'passenger@gmail.com', 'password123', 'Passenger', 'User', '2000-01-01')
    client.post('/login/', data={
        'email': 'passenger@gmail.com',
        'password': 'password123'
    }, follow_redirects=True)
    response = client.post('/select_role/', data={'role': 'passenger'}, follow_redirects=True)
    print("Select Role Passenger Response:", response.data)
    assert response.status_code == 200
    assert b"plan_course" in response.data

def test_plan_course(client):
    refresh_mysql_connection()
    create_user(client, 'passenger@gmail.com', 'password123', 'Passenger', 'User', '2000-01-01')
    client.post('/login/', data={
        'email': 'passenger@gmail.com',
        'password': 'password123'
    }, follow_redirects=True)

    client.post('/select_role/', data={'role': 'passenger'}, follow_redirects=True)

    future_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    response = client.post('/plan_course/', data={
        'origin': 'Grassilière 14, 2016 Cortaillod, Suisse',
        'destination': 'Croix de Rozon, 1257 Bardonnex',
        'num_people': 2,
        'car_trip': 1,
        'date': future_date,
        'hour_type': 'departure',
        'departure_hour': '09:00'
    }, follow_redirects=True)
    print("Plan Course Post Response:", response.data)
    assert response.status_code == 200
    assert b"Waiting for a Rider to Accept the Trip" in response.data, f"Actual response: {response.data}"

    with flask_app.app_context():
        refresh_mysql_connection()
        cur = mysql.connection.cursor()
        try:
            cur.execute("SELECT * FROM course WHERE id_passager = (SELECT id_utilisateur FROM utilisateur WHERE adresse_email_utilisateur = %s)", ('passenger@gmail.com',))
            course = cur.fetchone()
            print("Created Course:", course)
            assert course is not None, "Course should be created in the database"
            assert course[6] == 'Grassilière 14, 2016 Cortaillod, Suisse', f"Expected origin: 'Grassilière 14, 2016 Cortaillod, Suisse', but got: {course[6]}"
        except MySQLdb.Error as e:
            print(f"MySQL Error: {e}")
            raise
        finally:
            cur.close()

def test_new_vehicle(client):
    refresh_mysql_connection()
    create_user(client, 'driver@gmail.com', 'password123', 'Driver', 'User', '2000-01-01')
    # Log in the driver
    client.post('/login/', data={
        'email': 'driver@gmail.com',
        'password': 'password123'
    }, follow_redirects=True)
    client.post('/select_role/', data={'role': 'driver'}, follow_redirects=True)

    # Simulate clicking "Add a Vehicle" and navigating to the new vehicle form
    response = client.get('/new_vehicle/', follow_redirects=True)
    print("New Vehicle Get Response:", response.data)
    assert response.status_code == 200

    # Define the new vehicle data
    new_vehicle_data = {
        'make': 'TestMarque',  # Original case expected
        'model': 'TestModele',
        'registration_number': 'TEST123',
        'color': 'Blue',
        'num_seats': 4
    }

    # Add a vehicle to the database via POST request
    response = client.post('/new_vehicle/', data=new_vehicle_data, follow_redirects=True)
    print("New Vehicle Post Response:", response.data)
    assert response.status_code == 200
    assert b"Select Your Vehicle" in response.data, "Expected to be redirected to vehicle selection page"

    # Verify the vehicle was added to the database
    with flask_app.app_context():
        refresh_mysql_connection()
        cur = mysql.connection.cursor()
        try:
            cur.execute("SELECT * FROM voiture WHERE numero_plaques = %s", (new_vehicle_data['registration_number'],))
            vehicle = cur.fetchone()
            print("Vehicle in database:", vehicle)
            assert vehicle is not None, "Vehicle should be added to the database"
            # Adjust assertions to account for title case
            assert vehicle[2] == new_vehicle_data['make'].title(), "Make does not match"
            assert vehicle[3] == new_vehicle_data['model'].title(), "Model does not match"
            assert vehicle[4] == new_vehicle_data['color'], "Color does not match"
            assert vehicle[1] == new_vehicle_data['num_seats'], "Number of seats does not match"
        except MySQLdb.Error as e:
            print(f"MySQL Error: {e}")
            raise
        finally:
            cur.close()

def test_select_vehicle(client):
    refresh_mysql_connection()
    create_user(client, 'driver@gmail.com', 'password123', 'Driver', 'User', '2000-01-01')
    # Log in the driver
    client.post('/login/', data={
        'email': 'driver@gmail.com',
        'password': 'password123'
    }, follow_redirects=True)
    client.post('/select_role/', data={'role': 'driver'}, follow_redirects=True)

    # Navigate to the vehicle selection page
    response = client.get('/select_vehicle/', follow_redirects=True)
    print("Select Vehicle Get Response:", response.data)
    assert response.status_code == 200

    # Select the vehicle
    response = client.post('/select_vehicle/', data={'vehicle': 'TEST123'}, follow_redirects=True)
    print("Select Vehicle Post Response:", response.data)
    assert response.status_code == 200
    assert b"get_location" in response.data

def test_get_location(client):
    refresh_mysql_connection()
    create_user(client, 'driver@gmail.com', 'password123', 'Driver', 'User', '2000-01-01')
    # Log in the driver and select the role
    client.post('/login/', data={
        'email': 'driver@gmail.com',
        'password': 'password123'
    }, follow_redirects=True)
    client.post('/select_role/', data={'role': 'driver'}, follow_redirects=True)

    # Simulate clicking "Add a Vehicle" and navigating to the new vehicle form
    response = client.get('/new_vehicle/', follow_redirects=True)
    print("New Vehicle Get Response:", response.data)
    assert response.status_code == 200

    # Define the new vehicle data
    new_vehicle_data = {
        'make': 'TestMarque',  # Original case expected
        'model': 'TestModele',
        'registration_number': 'TEST123',
        'color': 'Blue',
        'num_seats': 4
    }

    # Add a vehicle to the database via POST request
    response = client.post('/new_vehicle/', data=new_vehicle_data, follow_redirects=True)
    print("New Vehicle Post Response:", response.data)
    assert response.status_code == 200
    assert b"Select Your Vehicle" in response.data, "Expected to be redirected to vehicle selection page"
    
    # Navigate to the vehicle selection page
    response = client.get('/select_vehicle/', follow_redirects=True)
    print("Select Vehicle Get Response:", response.data)
    assert response.status_code == 200

    # Select the vehicle
    response = client.post('/select_vehicle/', data={'vehicle': 'TEST123'}, follow_redirects=True)
    print("Select Vehicle Post Response:", response.data)
    assert response.status_code == 200
    assert b"get_location" in response.data

    # Post the driver's location
    response = client.post('/get_location/', json={
        'latitude': 46.942158,
        'longitude': 6.842804
    }, follow_redirects=True)
    print("Get Location Response:", response.data)
    assert response.status_code == 200
    assert b"waiting_for_course" in response.data

@pytest.mark.timeout(120)
def test_check_for_driver_not_found(client, app):
    refresh_mysql_connection()

    # Create users for driver and passenger
    create_user(client, 'driver@gmail.com', 'password123', 'Driver', 'User', '2000-01-01')
    create_user(client, 'passenger@gmail.com', 'password123', 'Passenger', 'User', '2000-01-01')

    # Login and select role as driver
    client.post('/login/', data={'email': 'driver@gmail.com', 'password': 'password123'}, follow_redirects=True)
    client.post('/select_role/', data={'role': 'driver'}, follow_redirects=True)

    # Login and select role as passenger
    response = client.post('/login/', data={'email': 'passenger@gmail.com', 'password': 'password123'}, follow_redirects=True)
    assert response.status_code == 200
    assert b"select_role" in response.data

    response = client.post('/select_role/', data={'role': 'passenger'}, follow_redirects=True)
    assert response.status_code == 200
    assert b"plan_course" in response.data, "Failed to navigate to 'plan_course' after selecting role as passenger."

    # Fetch the correct IDs for the driver and passenger
    with app.app_context():
        cur = mysql.connection.cursor()

        cur.execute("SELECT id_utilisateur FROM utilisateur WHERE adresse_email_utilisateur = 'driver@gmail.com'")
        driver_id = cur.fetchone()[0]

        cur.execute("SELECT id_utilisateur FROM utilisateur WHERE adresse_email_utilisateur = 'passenger@gmail.com'")
        passenger_id = cur.fetchone()[0]

        # Update driver coordinates and set status to 'libre'
        cur.execute('UPDATE conducteur SET latitude_conducteur = %s, longitude_conducteur = %s, etat_conducteur = %s WHERE id_conducteur = %s',
                    [46.942158, 6.842804, "libre", driver_id])
        mysql.connection.commit()

        # Insert the vehicle into the voiture table
        cur.execute("""
            INSERT INTO voiture (numero_plaques, marque, modele, couleur, nombre_sieges)
            VALUES (%s, %s, %s, %s, %s)
        """, ('TEST123', 'TestMarque', 'TestModele', 'Blue', 4))

        # Insert the vehicle into the possession table
        cur.execute("""
            INSERT INTO possession (id_condVoiture, id_utilisateur, numero_plaques, en_utilisation_y_n)
            VALUES (%s, %s, %s, %s)
        """, (1, driver_id, 'TEST123', 1))
        mysql.connection.commit()
        cur.close()

    response = client.get('/plan_course/', follow_redirects=True)
    assert response.status_code == 200

    future_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    response = client.post('/plan_course/', data={
        'origin': 'Grassilière 14, 2016 Cortaillod, Suisse',
        'destination': 'Croix de Rozon, 1257 Bardonnex',
        'num_people': 2,
        'car_trip': 1,
        'date': future_date,
        'hour_type': 'departure',
        'departure_hour': '09:00'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Waiting for a Rider to Accept the Trip" in response.data

    # Manually set the user_id in the session and check for the driver
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = passenger_id  # Set as passenger

        # Set max_retries to 2 and invoke /check_for_driver/
        response = client.get('/check_for_driver/?max_retries=2', follow_redirects=True)
        print(f"Check for Driver Response: {response.data.decode('utf-8')}")

        # Ensure the response indicates that no driver was found
        assert response.status_code == 200
        assert b"No driver found" in response.data, \
            "Expected 'No driver found' but did not receive it in the response."

    # Verify that the driver, passenger, and course all have the status 'libre' or other expected default states
    with app.app_context():
        cur = mysql.connection.cursor()

        # Check driver's status
        cur.execute("SELECT etat_conducteur FROM conducteur WHERE id_conducteur = %s", [driver_id])
        driver_status = cur.fetchone()[0]
        assert driver_status == "libre", f"Expected driver status to be 'libre' but got {driver_status}"

        # Check passenger's status (optional, depending on your logic)
        cur.execute("SELECT etat_passager FROM passager WHERE id_passager = %s", [passenger_id])
        passenger_status = cur.fetchone()[0]
        assert passenger_status == "en attente", f"Expected passenger status to be 'en attente' but got {passenger_status}"

        # Check course status (optional, depending on your logic)
        cur.execute("SELECT etat_course FROM course WHERE id_conducteur = %s AND id_passager = %s", [driver_id, passenger_id])
        course_status = cur.fetchone()
        if course_status:
            assert course_status[0] == "en attente", f"Expected course status to be 'en attente' but got {course_status[0]}"
        else:
            print("No course record found, which is expected in this scenario.")
        
        cur.close()

@pytest.mark.timeout(120)
def test_course_found_accepted(client, app):
    refresh_mysql_connection()

    # Create users for driver and passenger
    create_user(client, 'driver@gmail.com', 'password123', 'Driver', 'User', '2000-01-01')
    create_user(client, 'passenger@gmail.com', 'password123', 'Passenger', 'User', '2000-01-01')

    # Login and select role as driver
    client.post('/login/', data={'email': 'driver@gmail.com', 'password': 'password123'}, follow_redirects=True)
    client.post('/select_role/', data={'role': 'driver'}, follow_redirects=True)

    # Login and select role as passenger
    client.post('/login/', data={'email': 'passenger@gmail.com', 'password': 'password123'}, follow_redirects=True)
    client.post('/select_role/', data={'role': 'passenger'}, follow_redirects=True)

    # Fetch the correct IDs for the driver and passenger
    with app.app_context():
        cur = mysql.connection.cursor()

        cur.execute("SELECT id_utilisateur FROM utilisateur WHERE adresse_email_utilisateur = 'driver@gmail.com'")
        driver_id = cur.fetchone()[0]

        cur.execute("SELECT id_utilisateur FROM utilisateur WHERE adresse_email_utilisateur = 'passenger@gmail.com'")
        passenger_id = cur.fetchone()[0]

        # Insert the vehicle into the voiture table
        cur.execute("""
            INSERT INTO voiture (numero_plaques, marque, modele, couleur, nombre_sieges)
            VALUES (%s, %s, %s, %s, %s)
        """, ('TEST123', 'TestMarque', 'TestModele', 'Blue', 4))

        # Insert the vehicle into the possession table
        cur.execute("""
            INSERT INTO possession (id_condVoiture, id_utilisateur, numero_plaques, en_utilisation_y_n)
            VALUES (%s, %s, %s, %s)
        """, (1, driver_id, 'TEST123', 1))
        mysql.connection.commit()

        # Insert the course into the database
        cur.execute("""
            INSERT INTO course (id_course, etat_course, id_conducteur, id_passager, nombre_personnes, numero_plaques, origine_course, destination_course)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (2, 'en attente', driver_id, passenger_id, 2, 'TEST123', 'Grassilière 14, 2016 Cortaillod, Suisse', 'Croix de Rozon, 1257 Bardonnex'))
        mysql.connection.commit()
        
        # Update the status of the passenger to "en attente"
        cur.execute('UPDATE passager SET etat_passager = %s WHERE id_passager = %s', ['en attente', passenger_id])
        mysql.connection.commit()
        cur.close()

    # Manually set the user_id in the session and simulate driver accepting the course
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = driver_id  # Set as driver

        # Simulate the driver accessing the course_found page (GET request)
        response = client.get('/course_found/', follow_redirects=True)
        print(response.data.decode())  # Debugging: print the full HTML response
        assert response.status_code == 200
        assert "Grassilière 14, 2016 Cortaillod, Suisse".encode('utf-8') in response.data, "Origin was not correctly rendered."
        assert "Croix de Rozon, 1257 Bardonnex".encode('utf-8') in response.data, "Destination was not correctly rendered."

        # Simulate the driver accepting the course (POST request)
        response = client.post('/course_found/', data={'accept': 'yes'}, follow_redirects=True)
        assert response.status_code == 200
        assert b"course_accepted" in response.data, "Driver was not redirected to the course_accepted page."

    # Verify the course and driver statuses have been correctly updated
    with app.app_context():
        cur = mysql.connection.cursor()

        cur.execute("SELECT etat_course FROM course WHERE id_conducteur = %s", [driver_id])
        course_status = cur.fetchone()[0]
        assert course_status == 'en course', "Course status was not updated to 'en course'."

        cur.execute("SELECT etat_conducteur FROM conducteur WHERE id_conducteur = %s", [driver_id])
        driver_status = cur.fetchone()[0]
        assert driver_status == 'en course', "Driver status was not updated to 'en course'."

        cur.execute("SELECT etat_passager FROM passager WHERE id_passager = %s", [passenger_id])
        passenger_status = cur.fetchone()[0]
        assert passenger_status == 'en course', "Passenger status was not updated to 'en course'."

        cur.close()
        
@pytest.mark.timeout(120)
def test_course_found_denied(client, app):
    refresh_mysql_connection()

    # Create users for driver and passenger
    create_user(client, 'driver@gmail.com', 'password123', 'Driver', 'User', '2000-01-01')
    create_user(client, 'passenger@gmail.com', 'password123', 'Passenger', 'User', '2000-01-01')

    # Login and select role as driver
    client.post('/login/', data={'email': 'driver@gmail.com', 'password': 'password123'}, follow_redirects=True)
    client.post('/select_role/', data={'role': 'driver'}, follow_redirects=True)

    # Login and select role as passenger
    client.post('/login/', data={'email': 'passenger@gmail.com', 'password': 'password123'}, follow_redirects=True)
    client.post('/select_role/', data={'role': 'passenger'}, follow_redirects=True)

    # Fetch the correct IDs for the driver and passenger
    with app.app_context():
        cur = mysql.connection.cursor()

        cur.execute("SELECT id_utilisateur FROM utilisateur WHERE adresse_email_utilisateur = 'driver@gmail.com'")
        driver_id = cur.fetchone()[0]

        cur.execute("SELECT id_utilisateur FROM utilisateur WHERE adresse_email_utilisateur = 'passenger@gmail.com'")
        passenger_id = cur.fetchone()[0]

        # Insert the vehicle into the voiture table
        cur.execute("""
            INSERT INTO voiture (numero_plaques, marque, modele, couleur, nombre_sieges)
            VALUES (%s, %s, %s, %s, %s)
        """, ('TEST123', 'TestMarque', 'TestModele', 'Blue', 4))

        # Insert the vehicle into the possession table
        cur.execute("""
            INSERT INTO possession (id_condVoiture, id_utilisateur, numero_plaques, en_utilisation_y_n)
            VALUES (%s, %s, %s, %s)
        """, (1, driver_id, 'TEST123', 1))
        mysql.connection.commit()

        # Insert the course into the database
        cur.execute("""
            INSERT INTO course (id_course, etat_course, id_conducteur, id_passager, nombre_personnes, numero_plaques, origine_course, destination_course)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (2, 'en attente', driver_id, passenger_id, 2, 'TEST123', 'Grassilière 14, 2016 Cortaillod, Suisse', 'Croix de Rozon, 1257 Bardonnex'))
        mysql.connection.commit()
        
        # Update the status of the passenger to "en attente"
        cur.execute('UPDATE passager SET etat_passager = %s WHERE id_passager = %s', ['en attente', passenger_id])
        mysql.connection.commit()
        cur.close()

    # Manually set the user_id in the session and simulate driver denying the course
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = driver_id  # Set as driver

        # Simulate the driver accessing the course_found page (GET request)
        response = client.get('/course_found/', follow_redirects=True)
        assert response.status_code == 200
        assert "Grassilière 14, 2016 Cortaillod, Suisse".encode('utf-8') in response.data, "Origin was not correctly rendered."
        assert "Croix de Rozon, 1257 Bardonnex".encode('utf-8') in response.data, "Destination was not correctly rendered."

        # Simulate the driver denying the course (POST request)
        response = client.post('/course_found/', data={'accept': 'no'}, follow_redirects=True)
        assert response.status_code == 200

        # Verify that the driver was redirected to the "Waiting for Course" page
        assert b"Waiting for a Trip Proposition" in response.data, "Driver was not redirected to the 'waiting_for_course' page correctly."

    # Verify the course and driver statuses have been correctly reset
    with app.app_context():
        cur = mysql.connection.cursor()

        # Check if the course exists and has been reset to 'libre'
        cur.execute("SELECT id_course, etat_course FROM course WHERE id_conducteur = %s OR id_conducteur IS NULL", [driver_id])
        course_status_results = cur.fetchall()

        # Debugging: Print out all found course results
        print(f"Course statuses after denial: {course_status_results}")

        # Ensure there is at least one course with 'libre' status
        found_libre_course = any(status == 'libre' for _, status in course_status_results)
        assert found_libre_course, "No course found with status 'libre' after denial."

        # Check if the driver's status has been reset to 'libre'
        cur.execute("SELECT etat_conducteur FROM conducteur WHERE id_conducteur = %s", [driver_id])
        driver_status = cur.fetchone()[0]
        assert driver_status == 'libre', "Driver status was not reset to 'libre'."

        cur.close()

@pytest.mark.timeout(120)
def test_course_accepted_to_report(client, app):
    refresh_mysql_connection()

    # Create users for driver and passenger
    create_user(client, 'driver@gmail.com', 'password123', 'Driver', 'User', '2000-01-01')
    create_user(client, 'passenger@gmail.com', 'password123', 'Passenger', 'User', '2000-01-01')

    # Login and select role as driver
    client.post('/login/', data={'email': 'driver@gmail.com', 'password': 'password123'}, follow_redirects=True)
    client.post('/select_role/', data={'role': 'driver'}, follow_redirects=True)

    # Login and select role as passenger
    client.post('/login/', data={'email': 'passenger@gmail.com', 'password': 'password123'}, follow_redirects=True)
    client.post('/select_role/', data={'role': 'passenger'}, follow_redirects=True)

    # Fetch the correct IDs for the driver and passenger
    with app.app_context():
        cur = mysql.connection.cursor()

        cur.execute("SELECT id_utilisateur FROM utilisateur WHERE adresse_email_utilisateur = 'driver@gmail.com'")
        driver_id = cur.fetchone()[0]

        cur.execute("SELECT id_utilisateur FROM utilisateur WHERE adresse_email_utilisateur = 'passenger@gmail.com'")
        passenger_id = cur.fetchone()[0]

        # Insert the vehicle into the voiture table
        cur.execute("""
            INSERT INTO voiture (numero_plaques, marque, modele, couleur, nombre_sieges)
            VALUES (%s, %s, %s, %s, %s)
        """, ('TEST123', 'TestMarque', 'TestModele', 'Blue', 4))        

        # Insert the vehicle into the possession table
        cur.execute("""
            INSERT INTO possession (id_condVoiture, id_utilisateur, numero_plaques, en_utilisation_y_n)
            VALUES (%s, %s, %s, %s)
        """, (1, driver_id, 'TEST123', 1))
        mysql.connection.commit()

        # Insert the course into the database
        cur.execute("""
            INSERT INTO course (id_course, etat_course, id_conducteur, id_passager, nombre_personnes, numero_plaques, origine_course, destination_course)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (2, 'en attente', driver_id, passenger_id, 2, 'TEST123', 'Grassilière 14, 2016 Cortaillod, Suisse', 'Croix de Rozon, 1257 Bardonnex'))
        mysql.connection.commit()
        
        # Update the status of the passenger to "en attente"
        cur.execute('UPDATE passager SET etat_passager = %s WHERE id_passager = %s', ['en attente', passenger_id])
        mysql.connection.commit()
        cur.close()

    # Manually set the user_id in the session and simulate course acceptance
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = driver_id  # Set as driver

        # Simulate the driver accepting the course
        response = client.post('/course_accepted/', data={'accept': 'end'}, follow_redirects=True)
        print(f"Course Accepted Response (end): {response.data}")
        assert response.status_code == 200
        assert b"course_ended" in response.data, "The course was not ended correctly."

        # Simulate the driver reporting the course
        response = client.post('/course_accepted/', data={'accept': 'report'}, follow_redirects=True)
        print(f"Course Accepted Response (report): {response.data}")
        assert response.status_code == 200
        assert b"user_report" in response.data, "The course was not reported correctly."

@pytest.mark.timeout(120)
def test_user_report(client, app):
    refresh_mysql_connection()

    # Create users for driver and passenger
    create_user(client, 'driver@gmail.com', 'password123', 'Driver', 'User', '2000-01-01')
    create_user(client, 'passenger@gmail.com', 'password123', 'Passenger', 'User', '2000-01-01')

    # Login and select role as driver
    client.post('/login/', data={'email': 'driver@gmail.com', 'password': 'password123'}, follow_redirects=True)
    client.post('/select_role/', data={'role': 'driver'}, follow_redirects=True)

    # Login and select role as passenger
    client.post('/login/', data={'email': 'passenger@gmail.com', 'password': 'password123'}, follow_redirects=True)
    client.post('/select_role/', data={'role': 'passenger'}, follow_redirects=True)

    # Fetch the correct IDs for the driver and passenger
    with app.app_context():
        cur = mysql.connection.cursor()

        cur.execute("SELECT id_utilisateur FROM utilisateur WHERE adresse_email_utilisateur = 'driver@gmail.com'")
        driver_id = cur.fetchone()[0]

        cur.execute("SELECT id_utilisateur FROM utilisateur WHERE adresse_email_utilisateur = 'passenger@gmail.com'")
        passenger_id = cur.fetchone()[0]

        # Insert the vehicle into the voiture table
        cur.execute("""
            INSERT INTO voiture (numero_plaques, marque, modele, couleur, nombre_sieges)
            VALUES (%s, %s, %s, %s, %s)
        """, ('TEST123', 'TestMarque', 'TestModele', 'Blue', 4))
        mysql.connection.commit()  # Commit the vehicle insertion

        # Insert the course into the database
        cur.execute("""
            INSERT INTO course (id_course, etat_course, id_conducteur, id_passager, nombre_personnes, numero_plaques, origine_course, destination_course)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (2, 'en course', driver_id, passenger_id, 2, 'TEST123', 'Grassilière 14, 2016 Cortaillod, Suisse', 'Croix de Rozon, 1257 Bardonnex'))
        mysql.connection.commit()
        cur.close()

    # Manually set the user_id in the session to simulate the driver reporting
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = driver_id  # Set as driver

        # Simulate submitting the report
        response = client.post('/user_report/', data={
            'name': 'Driver User',
            'email': 'driver@gmail.com',
            'subject': 'Test Report',
            'message': 'This is a test report message.'
        }, follow_redirects=True)

        # Ensure that the user is redirected to the 'course_accepted' page
        assert response.status_code == 200
        assert b'course_accepted' in response.data

@pytest.mark.timeout(120)
def test_course_ended_no_rating(client, app):
    refresh_mysql_connection()

    # Create users for driver and passenger
    create_user(client, 'driver@gmail.com', 'password123', 'Driver', 'User', '2000-01-01')
    create_user(client, 'passenger@gmail.com', 'password123', 'Passenger', 'User', '2000-01-01')

    # Login and select role as driver
    client.post('/login/', data={'email': 'driver@gmail.com', 'password': 'password123'}, follow_redirects=True)
    client.post('/select_role/', data={'role': 'driver'}, follow_redirects=True)

    # Login and select role as passenger
    client.post('/login/', data={'email': 'passenger@gmail.com', 'password': 'password123'}, follow_redirects=True)
    client.post('/select_role/', data={'role': 'passenger'}, follow_redirects=True)

    # Fetch the correct IDs for the driver and passenger
    with app.app_context():
        cur = mysql.connection.cursor()

        cur.execute("SELECT id_utilisateur FROM utilisateur WHERE adresse_email_utilisateur = 'driver@gmail.com'")
        driver_id = cur.fetchone()[0]

        cur.execute("SELECT id_utilisateur FROM utilisateur WHERE adresse_email_utilisateur = 'passenger@gmail.com'")
        passenger_id = cur.fetchone()[0]

        # Insert the vehicle into the voiture table
        cur.execute("""
            INSERT INTO voiture (numero_plaques, marque, modele, couleur, nombre_sieges)
            VALUES (%s, %s, %s, %s, %s)
        """, ('TEST123', 'TestMarque', 'TestModele', 'Blue', 4))
        mysql.connection.commit()

        # Insert the vehicle into the possession table
        cur.execute("""
            INSERT INTO possession (id_condVoiture, id_utilisateur, numero_plaques, en_utilisation_y_n)
            VALUES (%s, %s, %s, %s)
        """, (1, driver_id, 'TEST123', 1))
        mysql.connection.commit()

        # Insert the course into the database
        cur.execute("""
            INSERT INTO course (id_course, etat_course, id_conducteur, id_passager, nombre_personnes, numero_plaques, origine_course, destination_course)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (2, 'en course', driver_id, passenger_id, 2, 'TEST123', 'Grassilière 14, 2016 Cortaillod, Suisse', 'Croix de Rozon, 1257 Bardonnex'))
        mysql.connection.commit()

        # Check if the course is correctly inserted
        cur.execute('SELECT etat_course FROM course WHERE id_passager = %s AND id_conducteur = %s', [passenger_id, driver_id])
        initial_course_status_result = cur.fetchone()
        assert initial_course_status_result is not None, "The course should be found in the database after insertion."
        print(f"Initial course status: {initial_course_status_result[0]}")  # Debugging output
        cur.close()

    # Simulate the driver ending the course
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = driver_id  # Set as driver

        # Simulate the driver accessing the course_ended page (GET request)
        response = client.get('/course_ended/', follow_redirects=True)
        assert response.status_code == 200

        # Driver decides not to rate (POST request)
        response = client.post('/course_ended/', data={'rate': 'no'}, follow_redirects=True)
        assert response.status_code == 200

        # Verify the course status is still in progress
        with app.app_context():
            cur = mysql.connection.cursor()
            cur.execute('SELECT etat_course FROM course WHERE id_passager = %s AND id_conducteur = %s', [passenger_id, driver_id])
            after_driver_course_status = cur.fetchone()
            assert after_driver_course_status is not None, "Course status should still exist after driver ends."
            print(f"Course status after driver ends: {after_driver_course_status[0]}")
            cur.close()

    # Simulate the passenger ending the course
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = passenger_id  # Set as passenger

        # Simulate the passenger accessing the course_ended page (GET request)
        response = client.get('/course_ended/', follow_redirects=True)
        assert response.status_code == 200

        # Passenger decides not to rate (POST request)
        response = client.post('/course_ended/', data={'rate': 'no'}, follow_redirects=True)
        assert response.status_code == 200

        # Check if the course state is updated to 'fini' after both have ended the course
        with app.app_context():
            cur = mysql.connection.cursor()
            cur.execute('SELECT etat_course FROM course WHERE id_passager = %s AND id_conducteur = %s', [passenger_id, driver_id])
            course_status_result = cur.fetchone()
            assert course_status_result is not None, "No course status found for the given driver and passenger IDs."
            assert course_status_result[0] == 'fini', f"The course status should be 'fini', but got '{course_status_result[0]}'."
            cur.close()

    # Simulate the logout for both driver and passenger to clean up the database

    # Driver logout
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = driver_id  # Set as driver
        response = client.get('/logout/', follow_redirects=True)
        assert response.status_code == 200

    # Passenger logout
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = passenger_id  # Set as passenger
        response = client.get('/logout/', follow_redirects=True)
        assert response.status_code == 200

    # Verify that both the driver and passenger are deleted from the database
    with app.app_context():
        cur = mysql.connection.cursor()

        cur.execute('SELECT * FROM conducteur WHERE id_conducteur = %s', [driver_id])
        driver_exists = cur.fetchone()
        assert driver_exists is None, "The driver record should be deleted after logout."

        cur.execute('SELECT * FROM passager WHERE id_passager = %s', [passenger_id])
        passenger_exists = cur.fetchone()
        assert passenger_exists is None, "The passenger record should be deleted after logout."
        cur.close()

@pytest.mark.timeout(120)
def test_course_ended_with_rating(client, app):
    refresh_mysql_connection()

    # Create users for driver and passenger
    create_user(client, 'driver@gmail.com', 'password123', 'Driver', 'User', '2000-01-01')
    create_user(client, 'passenger@gmail.com', 'password123', 'Passenger', 'User', '2000-01-01')

    # Login and select role as driver
    client.post('/login/', data={'email': 'driver@gmail.com', 'password': 'password123'}, follow_redirects=True)
    client.post('/select_role/', data={'role': 'driver'}, follow_redirects=True)

    # Login and select role as passenger
    client.post('/login/', data={'email': 'passenger@gmail.com', 'password': 'password123'}, follow_redirects=True)
    client.post('/select_role/', data={'role': 'passenger'}, follow_redirects=True)

    # Fetch the correct IDs for the driver and passenger
    with app.app_context():
        cur = mysql.connection.cursor()

        cur.execute("SELECT id_utilisateur FROM utilisateur WHERE adresse_email_utilisateur = 'driver@gmail.com'")
        driver_id = cur.fetchone()[0]

        cur.execute("SELECT id_utilisateur FROM utilisateur WHERE adresse_email_utilisateur = 'passenger@gmail.com'")
        passenger_id = cur.fetchone()[0]

        # Insert the vehicle into the voiture table
        cur.execute("""
            INSERT INTO voiture (numero_plaques, marque, modele, couleur, nombre_sieges)
            VALUES (%s, %s, %s, %s, %s)
        """, ('TEST123', 'TestMarque', 'TestModele', 'Blue', 4))
        mysql.connection.commit()

        # Insert the vehicle into the possession table
        cur.execute("""
            INSERT INTO possession (id_condVoiture, id_utilisateur, numero_plaques, en_utilisation_y_n)
            VALUES (%s, %s, %s, %s)
        """, (1, driver_id, 'TEST123', 1))
        mysql.connection.commit()

        # Insert the course into the database
        cur.execute("""
            INSERT INTO course (id_course, etat_course, id_conducteur, id_passager, nombre_personnes, numero_plaques, origine_course, destination_course)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (2, 'en course', driver_id, passenger_id, 2, 'TEST123', 'Grassilière 14, 2016 Cortaillod, Suisse', 'Croix de Rozon, 1257 Bardonnex'))
        mysql.connection.commit()

        # Check if the course is correctly inserted
        cur.execute('SELECT etat_course FROM course WHERE id_passager = %s AND id_conducteur = %s', [passenger_id, driver_id])
        initial_course_status_result = cur.fetchone()
        assert initial_course_status_result is not None, "The course should be found in the database after insertion."
        cur.close()

    # Simulate the driver ending the course
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = driver_id  # Set as driver

        # Simulate the driver accessing the course_ended page (GET request)
        response = client.get('/course_ended/', follow_redirects=True)
        assert response.status_code == 200

        # Driver decides to rate (POST request)
        response = client.post('/course_ended/', data={'rate': 'yes'}, follow_redirects=True)
        assert response.status_code == 200

        # Simulate rating by the driver
        response = client.post('/user_rate/', data={'rate': '4.5'}, follow_redirects=True)
        assert response.status_code == 200

    # Simulate the passenger ending the course
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = passenger_id  # Set as passenger

        # Simulate the passenger accessing the course_ended page (GET request)
        response = client.get('/course_ended/', follow_redirects=True)
        assert response.status_code == 200

        # Passenger decides to rate (POST request)
        response = client.post('/course_ended/', data={'rate': 'yes'}, follow_redirects=True)
        assert response.status_code == 200

        # Simulate rating by the passenger
        response = client.post('/user_rate/', data={'rate': '4.0'}, follow_redirects=True)
        assert response.status_code == 200

        # Check if the course state is updated to 'fini' after both have ended the course
        with app.app_context():
            cur = mysql.connection.cursor()
            cur.execute('SELECT etat_course FROM course WHERE id_passager = %s AND id_conducteur = %s', [passenger_id, driver_id])
            course_status_result = cur.fetchone()
            assert course_status_result is not None, "No course status found for the given driver and passenger IDs."
            assert course_status_result[0] == 'fini', f"The course status should be 'fini', but got '{course_status_result[0]}'."
            cur.close()

    # Simulate the logout for both driver and passenger to clean up the database

    # Driver logout
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = driver_id  # Set as driver
        response = client.get('/logout/', follow_redirects=True)
        assert response.status_code == 200

    # Passenger logout
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = passenger_id  # Set as passenger
        response = client.get('/logout/', follow_redirects=True)
        assert response.status_code == 200

    # Verify that both the driver and passenger are deleted from the database
    with app.app_context():
        cur = mysql.connection.cursor()

        cur.execute('SELECT * FROM conducteur WHERE id_conducteur = %s', [driver_id])
        driver_exists = cur.fetchone()
        assert driver_exists is None, "The driver record should be deleted after logout."

        cur.execute('SELECT * FROM passager WHERE id_passager = %s', [passenger_id])
        passenger_exists = cur.fetchone()
        assert passenger_exists is None, "The passenger record should be deleted after logout."
        cur.close()
