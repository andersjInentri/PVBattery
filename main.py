import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.linear_model import LinearRegression
from data_io import read_ai_features_view, write_to_excel

TARGET = "pv_power_w_avg"
# Bland features som påverkar är azimuth_deg problematisk då den går från 360 till 1 vid söder. Detta förstör en linjär regression. Därför finns cosinus och sinus av azimuth med istället.
FEATURES  = ["weather_cloud_pct", "weather_temperature", "weather_precip_mm", "weather_pressure_hpa", "weather_condition_text", "sun_azimuth_sin", "sun_azimuth_cos", "is_daylight"]

# Skapa morgondagens datum i textformat
TOMORROW = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

def process(df):
    mask_train = df[TARGET].notna()
    mask_pred  = df[TARGET].isna()

    X_train = df.loc[mask_train, FEATURES]
    y_train = df.loc[mask_train, TARGET].astype(float)

    # Ta bort NaN i träningen
    train_ok = X_train.notna().all(axis=1)
    X_train = X_train[train_ok]
    y_train = y_train[train_ok]

    # Lägg till intercept-kolumn (1:or)
    X_design = np.column_stack([np.ones(len(X_train)), X_train.values])

    # Minsta-kvadrat (normalekvation / lstsq)
    w, *_ = np.linalg.lstsq(X_design, y_train.values, rcond=None)
    intercept = w[0]
    coefs = w[1:]

    print("Intercept:", intercept)
    print(pd.Series(coefs, index=FEATURES))

    # Prediktion
    X_pred = df.loc[mask_pred, FEATURES].copy()
    X_pred = X_pred.fillna(X_train.mean())
    X_pred_design = np.column_stack([np.ones(len(X_pred)), X_pred.values])
    y_hat = X_pred_design @ w

    # Bara positiva värden och noll vid natt
    y_hat = np.where(df.loc[mask_pred, "sun_elevation_deg"].values <= 0, 0.0, y_hat)
    y_hat = np.clip(y_hat, 0, None)
    df.loc[mask_pred, TARGET] = y_hat

    return df

def clean_and_prepare_data(df):
    try:    
        tomorrow_data = df.set_index(pd.to_datetime(df["ts"], errors="coerce")).sort_index()
        tomorrow_data = tomorrow_data.loc[TOMORROW]
        print(f"Hittade {len(tomorrow_data)} rader för {TOMORROW}")

        # Eftersom huset är delvis mot söder blir azimuth_deg fel då det går från 360 till 1 i söder. Det förstör en linjär regression. Räkna om till sinus och cosinus.
        tomorrow_data["sun_azimuth_sin"] = np.sin(np.radians(tomorrow_data["sun_azimuth_deg"]))
        tomorrow_data["sun_azimuth_cos"] = np.cos(np.radians(tomorrow_data["sun_azimuth_deg"]))
        return tomorrow_data
    except Exception as e:
        if e.args[0] == TOMORROW:
            raise Exception(f"Fel vid datarensning. {e} Det finns ingen data för morgondagen ({TOMORROW}) i databasen. Denna körning kan bara göras mellan 15:00 och 23:00 dagen innan för att få korrekt prediktion för morgondagen.")
        else:
            raise Exception(f"Fel vid datarensning: {e}")


def output(output_dataframe):
    output_dataframe = output_dataframe.set_index(pd.to_datetime(output_dataframe["ts"], errors="coerce")).sort_index()

    tomorrow_output = output_dataframe.loc[TOMORROW].between_time("00:00", "23:59", inclusive="left")[
            ["pv_power_w_avg","weather_temperature", "weather_cloud_pct", "weather_precip_mm",
             "weather_pressure_hpa", "weather_condition_text", "sun_azimuth_sin",
             "sun_azimuth_cos", "sun_elevation_deg", "is_daylight"]
        ]

    # Skriv ut prediktion för morgondagen i CSV-format.
    # Använd semikolon som separator och komma som decimalpunkt, dvs format för Excel.
    print(tomorrow_output.to_csv(sep=';', index=True, decimal=','))

    # Spara data till Excel med den nya metoden
    write_to_excel(tomorrow_output, TOMORROW, sheet_prefix='Prediction')

def main():
    print("Starting PVBattery project...")

    try:
        # Step 1: READ DATA. Importera data - Läs data från en databas-vy där data är samlad per kvart.
        dataframe = read_ai_features_view()

        print(f"Kontroll att db förbindelse fungerade. Hämtade {len(dataframe)} rader från vy: ai_features_quarter_vw3")

        # Step 2: CLEAN DATA och PREPARE DATA rättare sagt kontrollera data. Vi vill veta att det finns data för träning och prediktion för imorgon
        # Raise exception med meddelande om det inte finns data för imorgon.
        tomorrow_data = clean_and_prepare_data(dataframe)
        
        # Step 3: PROCESS DATA.
        processed_dataframe = process(tomorrow_data)

        # Step 4: OUTPUT RESULT. Filtrera data för morgondagen
        output(processed_dataframe)
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
