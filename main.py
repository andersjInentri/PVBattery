import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.linear_model import LinearRegression
from db_reader import read_ai_features_view

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

    df = df.set_index(pd.to_datetime(df["ts"], errors="coerce")).sort_index()

    return df

def main():
    print("Starting PVBattery project...")

    try:
        # Step 1: READ DATA. Importera data - Läs data från en databas-vy där data är samlad per kvart.
        dataframe = read_ai_features_view()

        print(f"\nCheck that db connection works. Retrieved {len(dataframe)} records from view: ai_features_quarter_vw3")

        # Step 2: CLEAN DATA eller rättare sagt kontrollera data. Vi vill veta att det finns data för träning och prediktion för imorgon
        # Raise exception med meddelande om det inte finns data för imorgon.
        dataframe = dataframe.set_index(pd.to_datetime(dataframe["ts"], errors="coerce")).sort_index()
        tomorrow_data = dataframe.loc[TOMORROW]
        print(f"Hittade {len(tomorrow_data)} rader för {TOMORROW}")
        if tomorrow_data.empty:
            raise ValueError(f"Ingen data för {TOMORROW}. Förberedande data för morgondagen hämtas mellan kl 14:00 och 15:00. Detta program bör därmed köras mellan 15:00 och 23:00 för att få korrekt prediktion för morgondagen.")
        
        # Eftersom huset är delvis mot söder blir azimuth_deg fel då det går från 360 till 1 i söder. Det förstör en linjär regression. Räkna om till sinus och cosinus.
        dataframe["sun_azimuth_sin"] = np.sin(np.radians(dataframe["sun_azimuth_deg"]))
        dataframe["sun_azimuth_cos"] = np.cos(np.radians(dataframe["sun_azimuth_deg"]))

        # Step 3: PROCESS DATA.
        processed_dataframe = process(dataframe)

        # Step 4: OUTPUT RESULT. Filtrera data för morgondagen
        tomorrow_output = processed_dataframe.loc[TOMORROW].between_time("00:00", "23:59", inclusive="left")[
            ["pv_power_w_avg","weather_temperature", "weather_cloud_pct", "weather_precip_mm",
             "weather_pressure_hpa", "weather_condition_text", "sun_azimuth_sin",
             "sun_azimuth_cos", "sun_elevation_deg", "is_daylight"]
        ]

        # Skriv ut prediktion för morgondagen i CSV-format.
        # Använd semikolon som separator och komma som decimalpunkt, dvs format för Excel.
        print(tomorrow_output.to_csv(sep=';', index=True, decimal=','))

        # Spara data - lägg till som nytt sheet i befintlig fil eller skapa ny fil
        import os
        filename = 'prediction.xlsx'

        if os.path.exists(filename):
            # Fil finns - använd openpyxl för att lägga till sheet
            with pd.ExcelWriter(filename, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                tomorrow_output.to_excel(writer, index=True, sheet_name=f'Prediction_{TOMORROW}')
            print(f"Prediktion för {TOMORROW} tillagt i {filename}")
        else:
            # Fil finns inte - skapa ny med xlsxwriter och formatering
            with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
                tomorrow_output.to_excel(writer, index=True, sheet_name=f'Prediction_{TOMORROW}')

                workbook = writer.book
                worksheet = writer.sheets[f'Prediction_{TOMORROW}']

                # Skapa format med komma som decimaltecken
                number_format = workbook.add_format({'num_format': '#,##0.00'})

                # Applicera format på numeriska kolumner (kolumn B och framåt, rad 1 och framåt)
                worksheet.set_column('B:Z', None, number_format)

            print(f"Prediktion för {TOMORROW} sparad till ny fil {filename}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
