from datetime import datetime
import os
# Använd pymysql istället för MySQLdb för MariaDB connection.
# Undgår kompileringsproblem med MariaDB.
import pymysql
import pandas as pd
import numpy as np
from dotenv import load_dotenv

# Hämta environment variables från .env
load_dotenv()
# Skapa dagens datum i textformat
TODAY = (datetime.now()).strftime("%Y-%m-%d")


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

        query = "SELECT * FROM ai_features_quarter_vw4 ORDER BY ts"
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

        # Eftersom huset är delvis mot söder blir azimuth fel då det går från 360 till 1 i söder. Det förstör en linjär regression. Räkna om till sinus och cosinus.
        df["sun_azimuth_sin"] = np.sin(np.radians(df["sun_azimuth_deg"]))
        df["sun_azimuth_cos"] = np.cos(np.radians(df["sun_azimuth_deg"]))

        # Skriv ut data för idag mellan 00:00 och 23:59
        # Använd semikolon som separator och komma som decimalpunkt, dvs format för Excel.
        today_output = df.loc[TODAY].between_time("00:00", "23:59", inclusive="left")[
            ["pv_power_w_avg","weather_temperature", "weather_cloud_pct", "weather_precip_mm",
             "weather_pressure_hpa", "weather_condition_text", "sun_azimuth_sin",
             "sun_azimuth_cos", "sun_elevation_deg", "is_daylight"]
        ]

        # Skriv ut prediktion för morgondagen i CSV-format.
        # Använd semikolon som separator och komma som decimalpunkt, dvs format för Excel.
        print(today_output.to_csv(sep=';', index=True, decimal=','))

        # Spara data - lägg till som nytt sheet i befintlig fil eller skapa ny fil
        import os
        filename = 'prediction.xlsx'

        if os.path.exists(filename):
            # Fil finns - använd openpyxl för att lägga till sheet
            with pd.ExcelWriter(filename, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                today_output.to_excel(writer, index=True, sheet_name=f'Utfall_{TODAY}')
            print(f"Utfall för {TODAY} tillagt i {filename}")
        else:
            # Fil finns inte - skapa ny med xlsxwriter och formatering
            with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
                today_output.to_excel(writer, index=True, sheet_name=f'Utfall_{TODAY}')

                workbook = writer.book
                worksheet = writer.sheets[f'Utfall_{TODAY}']

                # Skapa format med komma som decimaltecken
                number_format = workbook.add_format({'num_format': '#,##0.00'})

                # Applicera format på numeriska kolumner (kolumn B och framåt, rad 1 och framåt)
                worksheet.set_column('B:Z', None, number_format)

            print(f"Utfall för {TODAY} sparad till ny fil {filename}")


    except Exception as e:
        print(f"Failed to read from database: {e}")
