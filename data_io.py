from datetime import datetime
import os
# Använd SQLAlchemy för databas connection.
# SQLAlchemy är rekommenderat av pandas och ger bättre kompatibilitet.
from sqlalchemy import create_engine, text
import pandas as pd
import numpy as np
from dotenv import load_dotenv

# Hämta environment variables från .env
load_dotenv()
# Skapa dagens datum i textformat
TODAY = (datetime.now()).strftime("%Y-%m-%d")

def get_db_engine():
    # Skapa och returnera SQLAlchemy engine till MariaDB
    try:
        print("Öppnar connection till databas")

        # Skapa connection string för MariaDB med pymysql driver
        connection_string = (
            f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
            f"@{os.getenv('DB_HOST', 'inentriqdb.tallas.se')}:{os.getenv('DB_PORT', '3306')}/{os.getenv('DB_NAME', 'ha_db')}"
        )

        engine = create_engine(connection_string)

        # Testa connection
        with engine.connect() as conn:
            print(f"Lyckades med connection till databas: {os.getenv('DB_NAME')}")

        return engine
    except Exception as e:
        raise Exception(f"Fel vid öppnande av databas connection: {e}")


def read_ai_features_view():
    # Läs data från ai_features_quarter_vw4 view.
    # Returnerar dataframe
    try:
        engine = get_db_engine()

        query = "SELECT * FROM ai_features_quarter_vw4 ORDER BY ts;"
        #print(f"Kör sql: {query}")

        df = pd.read_sql(query, engine)

        print(f"Lyckades hämta {len(df)} rader från ai_features_quarter_vw4")

        # Stäng engine
        engine.dispose()
        print("Database förbindelse stängdes")

        return df

    except Exception as e:
        raise Exception(f"Fel vid databas läsning: {e}")


def write_to_excel(df, date_str, sheet_prefix='Data', filename='prediction.xlsx'):
    """
    Skriv en dataframe till Excel-fil.

    Args:
        df: DataFrame att skriva
        date_str: Datum i format YYYY-MM-DD
        sheet_prefix: Prefix för sheet-namn (default: 'Data')
        filename: Namnet på Excel-filen (default: 'prediction.xlsx')
    """
    try:
        sheet_name = f'{sheet_prefix}_{date_str}'

        if os.path.exists(filename):
            # Fil finns - använd openpyxl för att lägga till sheet
            with pd.ExcelWriter(filename, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                df.to_excel(writer, index=True, sheet_name=sheet_name)
            print(f"{sheet_prefix} för {date_str} tillagt i {filename}")
        else:
            # Fil finns inte - skapa ny med xlsxwriter och formatering
            with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=True, sheet_name=sheet_name)

                workbook = writer.book
                worksheet = writer.sheets[sheet_name]

                # Skapa format med komma som decimaltecken
                number_format = workbook.add_format({'num_format': '#,##0.00'})

                # Applicera format på numeriska kolumner (kolumn B och framåt, rad 1 och framåt)
                worksheet.set_column('B:Z', None, number_format)

            print(f"{sheet_prefix} för {date_str} sparad till ny fil {filename}")
    except Exception as e:
        raise Exception(f"Fel vid skrivning till Excel: {e}")


def write_predictions_to_db(predictions_df):
    """
    Skriv predictions till prediction-tabellen i databasen.

    Args:
        predictions_df: DataFrame med predictions (med timestamp som index)

    Returns:
        antal_rader: Antal rader som skrevs till databasen
    """
    try:
        engine = get_db_engine()

        # Förbered dataframe för insert
        # Gör en kopia för att inte modifiera originalet
        df_to_write = predictions_df.copy()

        # Kontrollera om index är en DatetimeIndex eller om ts redan är en kolumn
        if df_to_write.index.name is None and 'ts' not in df_to_write.columns:
            # Index är timestamps utan namn, återställ och namnge
            df_to_write = df_to_write.reset_index()
            df_to_write = df_to_write.rename(columns={'index': 'ts'})
        elif df_to_write.index.name and 'ts' not in df_to_write.columns:
            # Index har ett namn (t.ex. 'ts' eller annat), återställ det
            df_to_write = df_to_write.reset_index()
            if df_to_write.columns[0] != 'ts':
                df_to_write = df_to_write.rename(columns={df_to_write.columns[0]: 'ts'})
        elif 'ts' in df_to_write.columns:
            # ts finns redan som kolumn, använd den som den är
            pass
        else:
            # Reset index och döp om första kolumnen till ts
            df_to_write = df_to_write.reset_index()
            if 'ts' not in df_to_write.columns:
                df_to_write = df_to_write.rename(columns={df_to_write.columns[0]: 'ts'})

        # Välj kolumner som finns i både DataFrame och prediction-tabellen
        # Kolumner i prediction-tabellen:
        # ts, price_sek_per_kwh, pv_power_w_avg, weather_cloud_pct, weather_pressure_hpa,
        # weather_precip_mm, weather_temperature, weather_condition_text, weather_condition_text2,
        # sun_azimuth_deg, sun_elevation_deg, is_daylight, updated_ts

        available_columns = ['ts', 'pv_power_w_avg', 'weather_cloud_pct', 'weather_pressure_hpa',
                           'weather_precip_mm', 'weather_temperature', 'weather_condition_text',
                           'sun_azimuth_deg', 'sun_elevation_deg', 'is_daylight']

        # Filtrera så vi bara tar kolumner som finns i DataFrame
        columns_to_write = [col for col in available_columns if col in df_to_write.columns]

        df_to_write = df_to_write[columns_to_write]

        # Lägg till updated_ts med aktuell tidstämpel
        df_to_write['updated_ts'] = datetime.now()

        # Rensa eventuell gammal data för samma tidsperiod
        start_ts = df_to_write['ts'].min()
        end_ts = df_to_write['ts'].max()

        with engine.connect() as conn:
            delete_query = text(f"DELETE FROM prediction WHERE ts >= '{start_ts}' AND ts <= '{end_ts}'")
            print(f"Tar bort gammal data för perioden {start_ts} till {end_ts}")
            result = conn.execute(delete_query)
            conn.commit()

        # Skriv ny data till tabellen
        antal_rader = df_to_write.to_sql(
            name='prediction',
            con=engine,
            if_exists='append',
            index=False,
            method='multi'
        )

        print(f"Skrev {len(df_to_write)} rader till prediction-tabellen med kolumner: {columns_to_write}")

        # Stäng engine
        engine.dispose()

        return len(df_to_write)

    except Exception as e:
        raise Exception(f"Fel vid skrivning till databas: {e}")


if __name__ == "__main__":
    # Fristående test av data_io.py
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

        # Spara data till Excel med den nya metoden
        write_to_excel(today_output, TODAY, sheet_prefix='Utfall')

    except Exception as e:
        print(f"Error: {e}")
