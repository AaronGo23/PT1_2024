import os
import sys
import pytest
from flask import Flask
from flask_mysqldb import MySQL

# Ensure the app directory is in the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app as flask_app, mysql

def refresh_mysql_connection():
    with flask_app.app_context():
        mysql.connection.close()
        mysql.connection.connect()
    print("MySQL connection refreshed")

@pytest.fixture(scope='session')
def app():
    # Use the main flask_app for testing and configure it for testing
    app = flask_app
    app.config['TESTING'] = True
    app.config['MYSQL_HOST'] = 'localhost'
    app.config['MYSQL_USER'] = 'root'
    app.config['MYSQL_PASSWORD'] = ''
    app.config['MYSQL_DB'] = 'test_ride_quest'  # Use a dedicated test database

    # Initialize the test database
    with app.app_context():
        cur = mysql.connection.cursor()
        try:
            cur.execute('DROP DATABASE IF EXISTS test_ride_quest')
            cur.execute('CREATE DATABASE test_ride_quest')
            cur.execute('USE test_ride_quest')

            # Create tables
            cur.execute('''
                CREATE TABLE utilisateur (
                    id_utilisateur INT(11) PRIMARY KEY AUTO_INCREMENT,
                    adresse_email_utilisateur VARCHAR(255) UNIQUE NOT NULL,
                    mdp_utilisateur VARCHAR(255) NOT NULL,
                    prenom_utilisateur VARCHAR(255) NOT NULL,
                    nom_utilisateur VARCHAR(255) NOT NULL,
                    date_naiss_utilisateur DATE NOT NULL,
                    rate FLOAT DEFAULT 0,
                    rates_num INT(11) DEFAULT 0
                )''')
            cur.execute('''
                CREATE TABLE conducteur (
                    id_conducteur INT(11) PRIMARY KEY AUTO_INCREMENT,
                    etat_conducteur VARCHAR(20) NOT NULL,
                    id_permis_conducteur VARCHAR(20) NOT NULL,
                    latitude_conducteur DECIMAL (10,7) NOT NULL,
                    longitude_conducteur DECIMAL (10,7) NOT NULL,
                    FOREIGN KEY (id_conducteur) REFERENCES utilisateur(id_utilisateur) ON DELETE CASCADE ON UPDATE CASCADE
                )''')
            cur.execute('''
                CREATE TABLE passager (
                    id_passager INT(11) PRIMARY KEY AUTO_INCREMENT,
                    etat_passager VARCHAR(20) NOT NULL,
                    FOREIGN KEY (`id_passager`) REFERENCES `utilisateur`(`id_utilisateur`) ON DELETE CASCADE ON UPDATE CASCADE
                )''')
            cur.execute('''
                CREATE TABLE voiture (
                    numero_plaques VARCHAR(20) PRIMARY KEY,
                    nombre_sieges INT(11) NOT NULL,
                    marque VARCHAR(50) NOT NULL,
                    modele VARCHAR(50) NOT NULL,
                    couleur VARCHAR(20) NOT NULL
                )''')
            cur.execute('''
                CREATE TABLE possession (
                    id_condVoiture INT(11) PRIMARY KEY AUTO_INCREMENT,
                    id_utilisateur INT(11) NOT NULL,
                    numero_plaques VARCHAR(20) NOT NULL,
                    en_utilisation_y_n TINYINT(1) DEFAULT 0,
                    FOREIGN KEY (`numero_plaques`) REFERENCES `voiture`(`numero_plaques`) ON DELETE CASCADE ON UPDATE CASCADE,
                    FOREIGN KEY (`id_utilisateur`) REFERENCES `utilisateur`(`id_utilisateur`) ON DELETE CASCADE ON UPDATE CASCADE
                )''')
            cur.execute('''
                CREATE TABLE course (
                    id_course INT(11) PRIMARY KEY AUTO_INCREMENT,
                    etat_course VARCHAR(20) NOT NULL,
                    id_conducteur INT(11) NULL,
                    id_passager INT(11) NOT NULL,
                    nombre_personnes INT(3) NOT NULL,
                    numero_plaques VARCHAR(20) NULL,
                    origine_course VARCHAR(100) NOT NULL,
                    destination_course VARCHAR(100) NOT NULL,
                    debut_course DATETIME NOT NULL,
                    arrivee_course DATETIME NOT NULL,
                    duree_course TIME NOT NULL,
                    distance_course FLOAT NULL,
                    encodedpolyline_course MEDIUMTEXT NULL,
                    only_voiture_y_n TINYINT(4) NOT NULL,
                    FOREIGN KEY (`id_conducteur`) REFERENCES `utilisateur`(`id_utilisateur`) ON DELETE SET NULL ON UPDATE CASCADE,
                    FOREIGN KEY (`id_passager`) REFERENCES `utilisateur`(`id_utilisateur`) ON DELETE CASCADE ON UPDATE CASCADE,
                    FOREIGN KEY (`numero_plaques`) REFERENCES `voiture`(`numero_plaques`) ON DELETE SET NULL ON UPDATE CASCADE
                )''')
            mysql.connection.commit()
        except Exception as e:
            print(f"Error during database setup: {e}")
            raise
        finally:
            cur.close()

    yield app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture(autouse=True)
def clean_database(app):
    """Cleans up the database between tests to ensure test isolation."""
    with app.app_context():
        cur = mysql.connection.cursor()
        try:
            tables = ['course', 'conducteur', 'passager', 'possession', 'voiture', 'utilisateur']
            for table in tables:
                cur.execute(f'DELETE FROM {table}')
            mysql.connection.commit()
        except Exception as e:
            print(f"Error during database cleanup: {e}")
        finally:
            cur.close()
