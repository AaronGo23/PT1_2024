import os
import MySQLdb
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_mysqldb import MySQL
from datetime import datetime, timedelta
import time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from decimal import Decimal

from routes_api import get_route_passenger, get_distance
from sorting import sort_drivers

# Configure email settings to then be able to send the reports via email to myself
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
EMAIL_USERNAME = 'projecttestfunny@gmail.com'
EMAIL_PASSWORD = 'oxge rqwe tdpn utaf' # Generated password by Application Password (Google)
EMAIL_RECEIVER = 'projecttestfunny@gmail.com' # To send it to the same address

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Configure MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'ride_quest' # Changed database during project as I had an issue where I couldn't start MySQL anymore
mysql = MySQL(app)

# Check MySQL connection
if mysql:
    print("Connection to MySQL database successful!")
else:
    print("Failed to connect to MySQL database.")
    
# Check if the user still has a session     
def check_user_id(user_id):
    if not user_id:
        flash("User ID not found in session. Please log in again.", "error")
        return redirect(url_for('login'))

# Check if the connection is still active and to re-establish it if it's not
def refresh_connection(): 
    try:
        mysql.connection.ping()
    except:
        mysql.connection.reconnect()

# Convert seconds to HH:MM:SS 
def convert_seconds_to_hms(seconds_str):
    seconds = int(seconds_str[:-1])  # Remove the 's' and convert to int
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f"{hours}h:{minutes}m:{seconds}s"

# Convert decimals
def convert_decimals(data):
    if isinstance(data, list):
        return [convert_decimals(i) for i in data]
    elif isinstance(data, dict):
        return {k: convert_decimals(v) for k, v in data.items()}
    elif isinstance(data, Decimal):
        return float(data)
    else:
        return data

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup/', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # Get the information from the form
        new_email = request.form['email']
        new_password = request.form['password']
        new_firstname = request.form['firstname']
        new_lastname = request.form['lastname']
        dob_str = request.form['dob']
        dob_date = datetime.strptime(dob_str, '%Y-%m-%d')
        dob_db = dob_date.strftime('%Y-%m-%d')

        try:
            with mysql.connection.cursor() as cur:
                # Check if the email already exists => it should not exist
                cur.execute("SELECT id_utilisateur FROM utilisateur WHERE adresse_email_utilisateur = %s", [new_email])
                existing_user = cur.fetchone()
                
                if existing_user:
                    flash("This email address is already used, please try another one.", "error")
                    return redirect(url_for('signup'))

                # Insert the information into the utilisateur table
                cur.execute(
                    """INSERT INTO utilisateur (adresse_email_utilisateur, mdp_utilisateur, prenom_utilisateur, 
                    nom_utilisateur, date_naiss_utilisateur) VALUES (%s, %s, %s, %s, %s)""",
                    [new_email, new_password, new_firstname, new_lastname, dob_db]
                )
                mysql.connection.commit()
                
                # Get user_id that will be used in the session and redirect to select_role
                cur.execute("SELECT id_utilisateur FROM utilisateur WHERE adresse_email_utilisateur = %s", [new_email])
                user_id = cur.fetchone()[0]
                session['user_id'] = user_id
                return redirect(url_for('select_role'))
        
        except MySQLdb.Error as e:
            print(f"MySQL Error: {e}")
            flash("An error occurred while signing up. Please try again.", "error")
        except Exception as e:
            print(f"Error: {e}")
            flash("An unexpected error occurred. Please try again.", "error")
    
    return render_template('signup.html')

@app.route('/login/', methods=['GET', 'POST'])
def login():
    # Get the data from the user to log in
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        # Check if email and password match a record in the database
        try:
            with mysql.connection.cursor() as cur:
                cur.execute("SELECT id_utilisateur FROM utilisateur WHERE adresse_email_utilisateur = %s AND mdp_utilisateur = %s", [email, password])
                user = cur.fetchone()
                
                """ cur.execute("SELECT id_conducteur FROM conducteur WHERE id_conducteur = %s", [user])
                driver = cur.fetchone()
                if driver:
                    cur.execute("DELETE id_conducteur FROM conducteur WHERE id_conducteur = %s", [user])
                    mysql.connection.commit()
                    
                cur.execute("SELECT id_passager FROM passager WHERE id_passager = %s", [user])
                passenger = cur.fetchone()
                if passenger:
                    cur.execute("DELETE id_passager FROM passager WHERE id_passager = %s", [user])
                    mysql.connection.commit() """

            if user:
                # Login successful, redirect to select_role
                session['user_id'] = user[0]
                return redirect(url_for('select_role'))
            else:
                # Login failed, show error message
                flash("Login failed. Please check your email and password.", "error")
        except MySQLdb.Error as e:
            print(f"MySQL Error: {e}")
            flash("An error occurred while logging in. Please try again.", "error")
        except Exception as e:
            print(f"Error: {e}")
            flash("An unexpected error occurred. Please try again.", "error")
    
    return render_template('login.html')

@app.route('/select_role/', methods=['GET', 'POST'])
def select_role():
    user_id = session.get('user_id')
    check_user_id(user_id)

    if request.method == 'POST':
        role = request.form['role']
        etat = "libre"

        try:
            with mysql.connection.cursor() as cur:
                if role == 'driver':
                    # Insert the user as a driver
                    cur.execute("INSERT INTO conducteur (id_conducteur) VALUES (%s)", [user_id])
                    mysql.connection.commit()
                    # Redirect to the select_vehicle route
                    return redirect(url_for('select_vehicle'))
                elif role == 'passenger':
                    # Insert the user as a passenger
                    cur.execute("INSERT INTO passager (id_passager, etat_passager) VALUES (%s, %s)", [user_id, etat])
                    mysql.connection.commit()
                    # Redirect to the plan_course route
                    return redirect(url_for('plan_course'))
                else:
                    # The user selects nothing
                    flash("Invalid role selected.", "error")
        except MySQLdb.Error as e:
            print(f"MySQL Error: {e}")
            flash("An error occurred while selecting the role. Please try again.", "error")
        except Exception as e:
            print(f"Error: {e}")
            flash("An unexpected error occurred. Please try again.", "error")
    
    return render_template('select_role.html')

@app.route('/select_vehicle/', methods=['GET', 'POST'])
def select_vehicle():
    user_id = session.get('user_id')
    check_user_id(user_id)

    if request.method == 'GET':
        try:
            with mysql.connection.cursor() as cur:
                # Retrieve the vehicles associated with the user
                cur.execute("SELECT numero_plaques FROM possession WHERE id_utilisateur = %s", [user_id])
                numero_plaques_rows = cur.fetchall()
                    
                vehicles = []
                # For each numero_plaques associated with the user, fetch vehicle details
                for numero_plaques_row in numero_plaques_rows:
                    numero_plaques = numero_plaques_row[0]
                    cur.execute("SELECT numero_plaques, nombre_sieges, marque, modele, couleur FROM voiture WHERE numero_plaques = %s", [numero_plaques])
                    vehicle = cur.fetchone()
                    vehicles.append(vehicle)
            # Send those vehicle details to the select_vehicle.html
            return render_template('select_vehicle.html', vehicles=vehicles)
        except MySQLdb.Error as e:
            print(f"MySQL Error: {e}")
            flash("An error occurred while retrieving vehicles. Please try again.", "error")
            return redirect(url_for('select_vehicle'))

    elif request.method == 'POST':
        # Get the selected vehicle from the form
        selected_vehicle = request.form.get('vehicle')
        in_use = 1
        
        if selected_vehicle:
            try:
                with mysql.connection.cursor() as cur:
                    # Update the selected vehicle as in use (1 meaning yes)
                    cur.execute("UPDATE possession SET en_utilisation_y_n = %s WHERE id_utilisateur = %s AND numero_plaques = %s", [in_use, user_id, selected_vehicle])
                    mysql.connection.commit()
                return redirect(url_for('ask_location'))
            except MySQLdb.Error as e:
                print(f"MySQL Error: {e}")
                flash("An error occurred while updating the vehicle. Please try again.", "error")
        else:
            # The user hasn't selected anything
            flash("No vehicle selected. Please select a vehicle.", "error")
    
    return render_template('select_vehicle.html')

@app.route('/new_vehicle/', methods=['GET', 'POST'])
def new_vehicle():
    user_id = session.get('user_id')
    check_user_id(user_id)

    if request.method == 'POST':
        try:
            # Get the form data for the new vehicle and formate it
            make = request.form['make'].title().replace(' ', '')
            model = request.form['model'].title().replace(' ', '')
            registration_number = request.form['registration_number'].upper().replace(' ', '')
            color = request.form['color'].capitalize()
            num_seats = request.form['num_seats']
            in_use = 0

            with mysql.connection.cursor() as cur:
                # Insert the new vehicle into the database (voiture and possession)
                cur.execute("INSERT INTO voiture (numero_plaques, nombre_sieges, marque, modele, couleur) VALUES (%s, %s, %s, %s, %s)", 
                            [registration_number, num_seats, make, model, color])
                cur.execute("INSERT INTO possession (id_utilisateur, numero_plaques, en_utilisation_y_n) VALUES (%s, %s, %s)", 
                            [user_id, registration_number, in_use])
                mysql.connection.commit()

            return redirect(url_for('select_vehicle'))

        except MySQLdb.IntegrityError as e:
            if e.args[0] == 1062:  # MySQL error code for duplicate entry
                flash("Registration number already exists. Please enter a different registration number.", "error")
            else:
                flash(f"An error occurred while adding the vehicle: {e}", "error")
                print(f"MySQLdb.IntegrityError: {e}")
        except MySQLdb.OperationalError as e:
            flash(f"A database operational error occurred: {e}", "error")
            print(f"MySQLdb.OperationalError: {e}")
        except Exception as e:
            flash(f"An unexpected error occurred: {str(e)}", "error")
            print(f"Exception: {e}")

        return redirect(url_for('new_vehicle'))

    return render_template('new_vehicle.html')

@app.route('/ask_location/', methods=['GET', 'POST'])
def ask_location():
    return render_template('get_gps_location.html')

@app.route('/get_location/', methods=['POST'])
def get_location():
    user_id = session.get('user_id')
    check_user_id(user_id)
    
    etat = "libre"
    # Get the GPS position from the web page
    if request.is_json:
        data = request.get_json()
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        print(f"User's location: Latitude = {latitude}, Longitude = {longitude}")
        
        # Formate into Decimals for the database
        latitude_driver = Decimal(latitude)
        longitude_driver = Decimal(longitude)
        print(f"User's location into decimals: Latitude = {latitude_driver}, Longitude = {longitude_driver}")
        
        try:
            with mysql.connection.cursor() as cur:
                # Update the driver as libre and add the GPS position
                cur.execute("UPDATE conducteur SET etat_conducteur = %s, latitude_conducteur = %s, longitude_conducteur = %s WHERE id_conducteur = %s", 
                            [etat, latitude_driver, longitude_driver, user_id])
                print("conducteur updated")
                mysql.connection.commit()
                print("information committed")
                
            # Return a JSON response with redirect URL
            return jsonify({'status': 'Location received', 'redirect': url_for('waiting_for_course')})
        except MySQLdb.Error as e:
            print(f"MySQL Error: {e}")
            return jsonify({'error': 'Database error occurred'}), 500
        except Exception as e:
            print(f"Error: {e}")
            return jsonify({'error': 'An unexpected error occurred'}), 500
    else:
        return jsonify({'error': 'Unsupported Media Type'}), 415

@app.route('/waiting_for_course/', methods=['GET'])
def waiting_for_course():
    user_id = session.get('user_id')
    check_user_id(user_id)
    
    return render_template('waiting_for_course.html')

@app.route('/check_for_course/', methods=['GET'])
def check_for_course():
    user_id = session.get('user_id')
    check_user_id(user_id)
    
    status_course_wait = "en attente"

    try:
        with mysql.connection.cursor() as cur:
            # Check for a course
            retries = 500
            for _ in range(retries) :
                # Retrieve the course that has the user as conducteur and is en attente (of an answer)
                cur.execute("SELECT id_course FROM course WHERE id_conducteur = %s AND etat_course = %s", [user_id, status_course_wait])
                print("course selected")
                driver_course = cur.fetchone()
                print(user_id)
                print(driver_course)
                time.sleep(2)
                
                if driver_course:
                    return jsonify({'status': 'Course found', 'course': driver_course})
                else :
                    return jsonify({'status': 'No course found'})              
            
    except MySQLdb.Error as e:
        print(f"MySQL Error: {e}")
        return jsonify({'error': 'Database error occurred'}), 500
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

@app.route('/plan_course/', methods=['GET', 'POST'])
def plan_course():
    user_id = session.get('user_id')
    check_user_id(user_id)

    if request.method == 'POST':
        try:
            # Get the form data for the trip
            origin = request.form['origin']
            destination = request.form['destination']
            num_people = request.form['num_people']
            car_trip = int(request.form['car_trip'])
            date_raw = request.form['date']
            date = datetime.strptime(date_raw, '%Y-%m-%d')
            date_db = date.strftime('%Y-%m-%d')
            driver_id = None
            num_plaques = None
            etat = "libre"
            mode = 'DRIVE'
            passenger_status_wait = "en attente"

            print(f"Origin: {origin}, Destination: {destination}, Number of People: {num_people}")
            print(f"Date: {date_db}, Car Trip: {car_trip}")

            # Get the hour type (arrival or departure)
            hour_type = request.form['hour_type']
            arrival_hour = request.form['arrival_hour'] if hour_type == 'arrival' else None
            departure_hour = request.form['departure_hour'] if hour_type == 'departure' else None
            print(f"Hour Type: {hour_type}, Arrival Hour: {arrival_hour}, Departure Hour: {departure_hour}")

            # Get the route from routes_api
            route = get_route_passenger(origin, destination, mode, date_db, arrival_hour, departure_hour)
            print(f"Route Data: {route}")
            if 'error' in route:
                flash(route['error'], "error")
                return redirect(url_for('plan_course'))

            distancem = route['routes'][0]['distanceMeters']
            distancekm = Decimal(distancem) / 1000
            distancekm = f"{distancekm:,.2f}"

            encodedPolyline = route['routes'][0]['polyline']['encodedPolyline']
            course_time_seconds = route['routes'][0]['duration']
            course_time = int(course_time_seconds[:-1])
            course_time_delta = timedelta(seconds=course_time)

            if departure_hour:
                departure_hour_dt = datetime.strptime(date_db + " " + departure_hour + ":00", '%Y-%m-%d %H:%M:%S')
                arrival_hour_dt = departure_hour_dt + course_time_delta
            elif arrival_hour:
                arrival_hour_dt = datetime.strptime(date_db + " " + arrival_hour + ":00", '%Y-%m-%d %H:%M:%S')
                departure_hour_dt = arrival_hour_dt - course_time_delta

            departure_hour_db = departure_hour_dt.strftime('%Y-%m-%d %H:%M:%S')
            arrival_hour_db = arrival_hour_dt.strftime('%Y-%m-%d %H:%M:%S')

            course_time_hms = str(course_time_delta)
            if course_time_delta.days > 0:
                course_time_hms = f"{course_time_delta.days * 24 + course_time_delta.seconds // 3600:02}:{(course_time_delta.seconds % 3600) // 60:02}:{course_time_delta.seconds % 60:02}"

            print("Attempting to insert course into database...")
            with mysql.connection.cursor() as cur:
                cur.execute("UPDATE passager SET etat_passager = %s WHERE id_passager = %s", [passenger_status_wait, user_id])
                cur.execute("""
                    INSERT INTO course (etat_course, id_conducteur, id_passager, nombre_personnes, numero_plaques, origine_course, destination_course, debut_course, arrivee_course, duree_course, distance_course, encodedpolyline_course, only_voiture_y_n) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""", 
                    [etat, driver_id, user_id, num_people, num_plaques, origin, destination, departure_hour_db, arrival_hour_db, course_time_hms, distancekm, encodedPolyline, car_trip])
                mysql.connection.commit()

            print("Course inserted successfully, redirecting to waiting_for_driver")
            return redirect(url_for('waiting_for_driver'))

        except MySQLdb.OperationalError as e:
            print(f"A database operational error occurred: {e}")
            flash(f"A database operational error occurred: {e}", "error")
        except Exception as e:
            print(f"An unexpected error occurred: {str(e)}")
            flash(f"An unexpected error occurred: {str(e)}", "error")

        return redirect(url_for('plan_course'))

    return render_template('course_info.html')

@app.route('/waiting_for_driver/', methods=['GET'])
def waiting_for_driver():
    user_id = session.get('user_id')
    check_user_id(user_id)
    
    return render_template('waiting_for_driver.html')

@app.route('/check_for_driver/', methods=['GET'])
def check_for_driver():
    user_id = session.get('user_id')
    check_user_id(user_id)

    # Read max_retries from query parameters or default to 30
    max_retries = int(request.args.get('max_retries', 30))

    driver_status_free = "libre"
    driver_status_wait = "en attente"
    course_status_wait = "en attente"
    course_status_accepted = "en course"
    course_status_free = "libre"
    in_use = 1
    available_drivers = []

    try:
        # First cursor usage to retrieve available drivers
        with mysql.connection.cursor() as cur:
            cur.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED")
            cur.execute("SELECT id_conducteur FROM conducteur WHERE etat_conducteur = %s", [driver_status_free])
            driver_id_rows = cur.fetchall()
            print(f"Driver ID Rows: {driver_id_rows}")

            for driver_id_row in driver_id_rows:
                driver_info = []

                driver_id = driver_id_row[0]
                print(f"Driver ID: {driver_id}")
                driver_info.append(driver_id)

                # Recreate cursor before each database operation
                with mysql.connection.cursor() as cur:
                    cur.execute("SELECT numero_plaques FROM possession WHERE id_utilisateur = %s", [driver_id])
                    num_plaques_result = cur.fetchone()
                    if num_plaques_result:
                        num_plaques = num_plaques_result[0]

                    cur.execute("SELECT nombre_sieges FROM voiture WHERE numero_plaques = %s", [num_plaques])
                    num_seats_result = cur.fetchone()
                    if num_seats_result:
                        num_seats = num_seats_result[0]
                    print(f"Number of seats: {num_seats}")
                    driver_info.append(num_seats)

                    cur.execute("SELECT rate FROM utilisateur WHERE id_utilisateur = %s", [driver_id])
                    rating_result = cur.fetchone()
                    rating = float(rating_result[0]) if rating_result else 0.0
                    print(f"Rating: {rating}")
                    driver_info.append(rating)

                    cur.execute("SELECT origine_course FROM course WHERE id_passager = %s AND etat_course = %s", [user_id, course_status_free])
                    origin_result = cur.fetchone()
                    if origin_result:
                        origin = origin_result[0]
              
                    cur.execute("SELECT latitude_conducteur, longitude_conducteur FROM conducteur WHERE id_conducteur = %s", [driver_id])
                    lat_lng_result = cur.fetchone()
                    if lat_lng_result:
                        lat_driver, lng_driver = lat_lng_result
                        lat_driver = float(lat_driver)
                        lng_driver = float(lng_driver)
                        distancem = get_distance(origin, lat_driver, lng_driver)
                        distancekm = float(distancem) / 1000.0
                        print(f"Distance: {distancekm}")
                        driver_info.append(distancekm)

                available_drivers.append(convert_decimals(driver_info))

        # Recreate cursor for fetching required seats
        with mysql.connection.cursor() as cur:
            cur.execute("SELECT nombre_personnes FROM course WHERE id_passager = %s AND etat_course = %s", [user_id, course_status_free])
            requested_seats_result = cur.fetchone()
            requested_seats = requested_seats_result[0] if requested_seats_result else None

        sorted_drivers = sort_drivers(available_drivers, requested_seats)
        print(f"Sorted Drivers received: {sorted_drivers}")
        if not sorted_drivers:
            return jsonify({'status': 'No driver found, please try again later'})

        for driver in sorted_drivers:
            driver_id = driver[0]

            with mysql.connection.cursor() as cur:
                cur.execute("SELECT numero_plaques FROM possession WHERE id_utilisateur = %s AND en_utilisation_y_n = %s", [driver_id, in_use])
                num_plaques_result = cur.fetchone()
                if num_plaques_result:
                    num_plaques = num_plaques_result[0]

                cur.execute("UPDATE course SET id_conducteur = %s, etat_course = %s, numero_plaques = %s WHERE id_passager = %s AND etat_course = %s",
                            [driver_id, course_status_wait, num_plaques, user_id, course_status_free])
                cur.execute("UPDATE conducteur SET etat_conducteur = %s WHERE id_conducteur = %s", [driver_status_wait, driver_id])
                mysql.connection.commit()
                print("Course and conducteur updated")

            retries = 0
            while retries <= max_retries:
                print(f"User ID passenger : {user_id}")
                refresh_connection()

                with mysql.connection.cursor() as check_cur:
                    check_cur.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED")
                    check_cur.execute("SELECT etat_course FROM course WHERE id_passager = %s AND (etat_course = %s OR etat_course = %s OR etat_course = %s)",
                                      [user_id, course_status_free, course_status_wait, course_status_accepted])
                    course_answer_result = check_cur.fetchone()
                    course_answer = course_answer_result[0] if course_answer_result else None
                    print(f"Course answer: {course_answer}")

                    if course_answer == course_status_accepted:
                        return jsonify({'status': 'Course accepted'})
                    elif course_answer == course_status_free:
                        break
                    elif course_answer == course_status_wait:
                        retries += 1
                        print(f"Retrying... ({retries}/{max_retries})")
                        time.sleep(10)

            # Reset the driver status if max retries reached
            else:
                with mysql.connection.cursor() as update_cur:
                    update_cur.execute("UPDATE conducteur SET etat_conducteur = %s WHERE id_conducteur = %s", [driver_status_free, driver_id])
                    mysql.connection.commit()
                    print("Conducteur reset to free after max retries")

        return jsonify({'status': 'No driver found, please try again later', 'drivers': convert_decimals(sorted_drivers)})

    except MySQLdb.Error as e:
        print(f"MySQL Error: {e}")
        flash("Database error occurred", "error")
        return redirect(url_for('waiting_for_driver'))
    except Exception as e:
        print(f"Error: {e}")
        flash("An unexpected error occurred", "error")
        return redirect(url_for('waiting_for_driver'))

@app.route('/course_found/', methods=['GET', 'POST'])
def course_found():
    user_id = session.get('user_id')
    check_user_id(user_id)
    
    no_driver = None
    no_car = None
    driver_status_free = "libre"
    driver_status_wait = "en attente"
    status_trip = "en course"
    course_status_free = "libre"
    course_status_wait = "en attente"
    course_status_trip = "en course"    
    
    if request.method == 'GET':
        print("GET request received")  # Debug statement
        try:
            with mysql.connection.cursor() as cur:
                # Retrieve the course information
                cur.execute('SELECT * FROM course WHERE id_conducteur = %s AND etat_course = %s', [user_id, course_status_wait])
                course = cur.fetchone()
                if not course:
                    flash("No course found for this driver.", "error")
                    return redirect(url_for('waiting_for_course'))
                
                num_people = course[4]
                origin = course[6]
                destination = course[7]
                departure_hour = course[8]
                arrival_hour = course[9]
                duration = course[10]
                distance = course[11]
                encodedpolyline = course[12]
                
                print(f"origin: {origin}")
                print(f"destination: {destination}")
                print(f"departure_hour: {departure_hour}")
                print(f"arrival_hour: {arrival_hour}")
                print(f"num_people: {num_people}")
                print(f"distance: {distance}")
                print(f"encodedPolyline: {encodedpolyline}")
                print(f"duration: {duration}")

                # Send the course information to the course_found.html
                return render_template('course_found.html', origin=origin, destination=destination, duration=duration, 
                                       num_people=num_people, distance=distance, encodedpolyline=encodedpolyline, 
                                       departure_hour=departure_hour, arrival_hour=arrival_hour)
                
        except MySQLdb.Error as e:
            print(f"MySQL Error: {e}")
            flash("An error occurred while retrieving the course. Please try again.", "error")
            return redirect(url_for('waiting_for_course'))
        except Exception as e:
            print(f"Error: {e}")
            flash("An unexpected error occurred. Please try again.", "error")
            return redirect(url_for('waiting_for_course'))

    if request.method == 'POST':
        try:
            print("POST request received")  # Debug statement
            print(f"User ID: {user_id}")  # Debug statement

            # Get the button data (yes or no)
            accept_value = request.form['accept']
            with mysql.connection.cursor() as cur:
                
                if accept_value == 'no':
                    print("no")
                    # If the user selected no, update the state of the driver and the course back to libre
                    cur.execute('UPDATE conducteur SET etat_conducteur = %s WHERE id_conducteur = %s', 
                                [driver_status_free, user_id])
                    
                    cur.execute('UPDATE course SET etat_course = %s, id_conducteur = %s, numero_plaques = %s WHERE id_conducteur = %s AND etat_course = %s', 
                                [course_status_free, no_driver, no_car, user_id, course_status_wait])
                    
                    mysql.connection.commit()
                    return redirect(url_for('waiting_for_course'))
                
                elif accept_value == 'yes':
                    print("yes")
                    # Update driver status
                    cur.execute('UPDATE conducteur SET etat_conducteur = %s WHERE id_conducteur = %s', 
                                [status_trip, user_id])
                    
                    # Fetch the passenger ID
                    cur.execute('SELECT id_passager FROM course WHERE id_conducteur = %s', [user_id])
                    passenger_result = cur.fetchone()
                    
                    if passenger_result is None:
                        flash("No passenger found for this course.", "error")
                        return redirect(url_for('course_found'))
                    
                    passenger_id = passenger_result[0]
                    
                    # Update passenger status
                    cur.execute('UPDATE passager SET etat_passager = %s WHERE id_passager = %s', 
                                [status_trip, passenger_id])
                    
                    # Update course status
                    cur.execute('UPDATE course SET etat_course = %s WHERE id_conducteur = %s AND etat_course = %s', 
                                [course_status_trip, user_id, course_status_wait])
                    
                    mysql.connection.commit()
                    return redirect(url_for('course_accepted'))
                
        except MySQLdb.Error as e:
            print(f"MySQL Error: {e}")
            flash("An error occurred while updating the course. Please try again.", "error")
        except Exception as e:
            print(f"Error: {e}")
            flash("An unexpected error occurred. Please try again.", "error")
    
    return render_template('course_found.html') 

@app.route('/course_accepted/', methods=['GET', 'POST'])
def course_accepted():
    user_id = session.get('user_id')
    check_user_id(user_id)
    
    # Get the route
    #route = session.get('route')
    
    if request.method == 'POST':
        try:
            # Get the type (report or end)
            action_type = request.form['accept']

            if action_type == 'report':
                return redirect(url_for('user_report'))
            elif action_type == 'end':
                return redirect(url_for('course_ended'))

        except MySQLdb.OperationalError as e:
            flash(f"A database operational error occurred: {e}", "error")
            print(f"MySQLdb.OperationalError: {e}")
        except Exception as e:
            flash(f"An unexpected error occurred: {str(e)}", "error")
            print(f"Exception: {e}")

        return redirect(url_for('course_accepted'))

    return render_template('course_accepted.html')#, route=route)
    
@app.route('/course_ended/', methods=['GET', 'POST'])
def course_ended():
    user_id = session.get('user_id')
    check_user_id(user_id)
    
    course_status_trip = "en course"
    course_status_done = "fini"
    not_in_use = 0
    
    if request.method == 'GET':
        with mysql.connection.cursor() as cur:
            # Check if the user is a driver or a passenger and update the appropriate fields
            cur.execute('SELECT id_conducteur, id_passager, etat_course FROM course WHERE id_conducteur = %s OR id_passager = %s', [user_id, user_id])
            course = cur.fetchone()

            if course:
                id_conducteur, id_passager, etat_course = course

                # If the user is the driver, update the car status
                if user_id == id_conducteur:
                    cur.execute('UPDATE possession SET en_utilisation_y_n = %s WHERE id_utilisateur = %s', [not_in_use, user_id])
                
                # If the course is still "en course", update it to "fini"
                if etat_course == course_status_trip:
                    cur.execute('UPDATE course SET etat_course = %s WHERE id_conducteur = %s AND id_passager = %s', [course_status_done, id_conducteur, id_passager])
                
                mysql.connection.commit()
    
    if request.method == 'POST':
        try:
            rate_decision = request.form['rate']
            
            if rate_decision == 'yes':
                return redirect(url_for('user_rate'))
            else:
                return redirect(url_for('logout'))

        except MySQLdb.OperationalError as e:
            flash(f"A database operational error occurred: {e}", "error")
            print(f"MySQLdb.OperationalError: {e}")
        except Exception as e:
            flash(f"An unexpected error occurred: {str(e)}", "error")
            print(f"Exception: {e}")

    return render_template('course_ended.html')

@app.route('/user_report/', methods=['GET', 'POST'])
def user_report():
    user_id = session.get('user_id')
    check_user_id(user_id)
    
    course_status_trip = "en course" 

    if request.method == 'POST':
        try:
            # Get the information from the form
            name = request.form['name']
            email = request.form['email']
            subject = request.form['subject']
            message = request.form['message']
            
            with mysql.connection.cursor() as cur:
                cur.execute("SELECT id_course, id_conducteur, id_passager FROM course WHERE (id_conducteur = %s OR id_passager = %s) AND etat_course = %s", [user_id, user_id, course_status_trip])
                course_info = cur.fetchone()
            
            # Create the email
            msg = MIMEMultipart()
            msg['From'] = EMAIL_USERNAME
            msg['To'] = EMAIL_RECEIVER
            msg['Subject'] = f"Report from {name}: {subject}"
            
            # Add the message body
            body = f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}\n\nCourse number:{course_info[0]}\nId driver:{course_info[1]}\nId passager:{course_info[2]}"
            msg.attach(MIMEText(body, 'plain'))
            
            # Send the email
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.starttls()
            server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
            server.sendmail(EMAIL_USERNAME, EMAIL_RECEIVER, msg.as_string())
            server.quit()

            return redirect(url_for('course_accepted'))
            
        except MySQLdb.Error as e:
            flash(f"Database error: {e}", "error")
            print(f"Database error: {e}")
        except Exception as e:
            flash(f"Failed to send the report: {e}", "error")
            print(f"Failed to send the report: {e}")

    return render_template('user_report.html')

@app.route('/user_rate/', methods=['GET', 'POST'])
def user_rate():
    user_id = session.get('user_id')
    check_user_id(user_id)
    
    course_status_done = "fini"
    
    if request.method == 'POST':
        try:
            rate_by_user = float(request.form['rate'])  # Convert rate to float
            
            with mysql.connection.cursor() as cur:
                # Get the ids of the driver and passenger
                cur.execute("SELECT id_conducteur, id_passager FROM course WHERE (id_conducteur = %s OR id_passager = %s) AND etat_course = %s", [user_id, user_id, course_status_done])
                course_info = cur.fetchone()
                if not course_info:
                    flash("No course information found.", "error")
                    return redirect(url_for('user_rate'))

                # Separate them 
                driver_id, passenger_id = course_info
                # And the other one as a binome (not the user)
                id_binome = passenger_id if user_id == driver_id else driver_id

                # Select their rate and number of rates
                cur.execute("SELECT rate, rates_num FROM utilisateur WHERE id_utilisateur = %s", [id_binome])
                user_info = cur.fetchone()
                if not user_info:
                    flash("User information not found.", "error")
                    return redirect(url_for('user_rate'))
                
                # Calculate the new rate
                user_rate, user_rates_num = map(float, user_info)  # Convert user_rate and user_rates_num to float
                new_user_rates_num = user_rates_num + 1
                new_user_rate = (user_rate * user_rates_num + rate_by_user) / new_user_rates_num
                
                # Update the new rate
                cur.execute("UPDATE utilisateur SET rate = %s, rates_num = %s WHERE id_utilisateur = %s", [new_user_rate, new_user_rates_num, id_binome])
                mysql.connection.commit()

            return redirect(url_for('logout'))

        except (MySQLdb.Error, ValueError) as e:
            flash(f"An error occurred: {e}", "error")
            print(f"Error: {e}")
            return redirect(url_for('user_rate'))

    return render_template('user_rate.html')

@app.route('/logout/', methods=['GET', 'POST'])
def logout():
    user_id = session.get('user_id')
    check_user_id(user_id)

    not_in_use = 0
    status_course_abandonnee = "abandonnée"
    status_course_done = "fini"

    try:
        with mysql.connection.cursor() as cur:
            # Set the state of any active course to 'abandonnée' before removing the user
            cur.execute('SELECT id_course FROM course WHERE (id_passager = %s OR id_conducteur = %s) AND etat_course != %s', [user_id, user_id, status_course_done])
            courses = cur.fetchall()
            for course in courses:
                cur.execute('UPDATE course SET etat_course = %s WHERE id_course = %s', [status_course_abandonnee, course[0]])
            
            # If the driver is logging out, update the car as not in use and delete the conducteur tuple
            cur.execute('UPDATE possession SET en_utilisation_y_n = %s WHERE id_utilisateur = %s', [not_in_use, user_id])
            cur.execute('DELETE FROM conducteur WHERE id_conducteur = %s', [user_id])
            
            # If the passenger is logging out, delete the passenger tuple
            cur.execute('DELETE FROM passager WHERE id_passager = %s', [user_id])

            mysql.connection.commit()
            
    except MySQLdb.Error as e:
        flash(f"Database error occurred: {e}", "error")
        print(f"Database error: {e}")
        return redirect(url_for('login'))
    except Exception as e:
        flash(f"An unexpected error occurred: {e}", "error")
        print(f"Unexpected error: {e}")
        return redirect(url_for('login'))

    session.pop('user_id', None)
    
    return render_template('goodbye.html')

if __name__ == '__main__':
    app.run()
