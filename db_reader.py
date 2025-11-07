from datetime import datetime
import os
# Använd pymysql istället för MySQLdb för MariaDB connection.
# Undgår kompileringsproblem med MariaDB.
import pymysql
import pandas as pd
from dotenv import load_dotenv

# Hämta environment variables från .env
load_dotenv()


def get_db_connection():
    # Skapa och returnera db connection till MariaDB
    try:
        print(f"Connecting to MariaDB")
        conn = pymysql.connect(
            host=os.getenv('DB_HOST'),
            port=int(os.getenv('DB_PORT', 3306)),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME')
        )
        print(f"Successfully connected to database: {os.getenv('DB_NAME')}")
        return conn
    except pymysql.Error as e:
        print(f"Error connecting to MariaDB: {e}")
        raise


def read_ai_features_view():
    # Läs data från ai_features_quarter_vw3 view.
    # Returnerar dataframe
    conn = None
    try:
        conn = get_db_connection()

        query = "SELECT * FROM ai_features_quarter_vw3 ORDER BY ts"
        print(f"Executing query: {query}")

        df = pd.read_sql(query, conn)

        print(f"Successfully retrieved {len(df)} rows from ai_features_quarter_vw3")
        return df

    except pymysql.Error as e:
        print(f"Database error: {e}")
        raise
    except Exception as e:
        print(f"Error: {e}")
        raise
    finally:
        # Stäng db connection
        if conn:
            conn.close()
            print("Database connection closed")


def read_custom_query(query):
    # Kör en SQL och returnerar resultatet som en dataframe.
    conn = None
    try:
        conn = get_db_connection()
        df = pd.read_sql(query, conn)
        print(f"Successfully retrieved {len(df)} rows")
        return df
    except pymysql.Error as e:
        print(f"Database error: {e}")
        raise
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    # Fristående test av db_reader.py
    try:
        # Hämta dataframes från view
        df = read_ai_features_view()

        # Sätt timestamp som index och sortera
        df = df.set_index(pd.to_datetime(df["ts"], errors="coerce")).sort_index()

        # Skapa dagens datum i textformat
        today = (datetime.now()).strftime("%Y-%m-%d")

        # Skriv ut data för idag mellan 05:00 och 18:00
        # Använd semikolon som separator och komma som decimalpunkt, dvs format för Excel.
        print(df.loc[today].between_time("05:00", "18:00", inclusive="left")[["pv_power_w_avg","weather_cloud_pct", "sun_azimuth_deg", "sun_elevation_deg", "is_daylight"]].to_csv(sep=';', index=True, decimal=','))

    except Exception as e:
        print(f"Failed to read from database: {e}")
