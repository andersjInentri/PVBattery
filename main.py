import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from data_io import read_ai_features_view, write_to_excel
from sklearn.linear_model import Lasso
from sklearn.pipeline import Pipeline
from sklearn.model_selection import TimeSeriesSplit, GridSearchCV

TARGET = "pv_power_w_avg"
# Bland features som påverkar är azimuth_deg problematisk då den går från 360 till 1 vid söder. Detta förstör en linjär regression. Därför finns cosinus och sinus av azimuth med istället.
#FEATURES  = ["weather_cloud_pct", "weather_temperature", "weather_precip_mm", "weather_pressure_hpa", "weather_condition_text", "sun_azimuth_sin", "sun_azimuth_cos", "sun_elevation_deg", "is_daylight"]
FEATURES  = ["weather_cloud_pct", "weather_condition_text", "sun_azimuth_sin", "sun_azimuth_cos", "sun_elevation_deg", "is_daylight"]

# Skapa morgondagens datum i textformat
TOMORROW = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")


def evaluate_model(name, model, X, y, sun_elevation=None):
    print(f"Utvärderar modell på {name} data...")
    predictions = model.predict(X)
    # Sanity ändring: Sätt produktion till 0 när solen är under horisonten. Annars blir värdena helt fel.
    if sun_elevation is not None:
        sun_elev = np.array(sun_elevation, dtype=float)
        # Sätt natt = 0
        predictions = np.where(sun_elev <= 0, 0.0, predictions)

    mae = mean_absolute_error(y, predictions)
    mse = mean_squared_error(y, predictions)
    r2 = r2_score(y, predictions)

    print(f"{name} Evaluation: Mean Absolute Error (MAE): {mae:.2f} Mean Squared Error (MSE): {mse:.2f} R-squared (R2 ): {r2:.4f}")
    print("-" * 30)
    return {"split": name, "mae": mae, "mse": mse, "r2": r2}
    
def train_and_validate_model(df):
    print("Tränar och validerar modell...")
    # Splitta upp i träningsdata och prediktionsdata. Föutsätter att df innehåller både historisk data med target-värde och framtida data utan target-värde.
    # Förutsättning: Datan ska tidigare vara indexerad och sorterad på timestamp.
    total_rows = len(df)  # Exkludera de sista 96 raderna (data innehåller ju tom mål-data (pv_power_w_avg) för morgondagen)
    train_end = int(0.8 * total_rows)
    val_end = int(0.9 * total_rows)

    print(f"Totalt antal rader: {total_rows}, Träningsdata: 0 till {train_end}, Valideringsdata: {train_end} till {val_end}, Testdata: {val_end} till {total_rows}")

    train_data = df.iloc[:train_end]
    validation_data = df.iloc[train_end:val_end]
    test_data = df.iloc[val_end:]

    # Träningsdata
    X_train = train_data[FEATURES]
    y_train = train_data[TARGET].astype(float)
   

    # Bygg Lasso-pipeline (skalning + L1-regression)
    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("lasso", Lasso(max_iter=10000, random_state=42))
    ])
    
    # Hyperparametrar att testa för Lasso (L1-styrka)
    param_grid = {
        "lasso__alpha": [0.001, 0.01, 0.1, 1.0, 10.0]
    }

    # TimeSeriesSplit så vi inte blandar framtid och dåtid i CV
    tscv = TimeSeriesSplit(n_splits=5)

    grid = GridSearchCV(
        pipe,
        param_grid,
        cv=tscv,
        scoring="neg_mean_absolute_error",
        n_jobs=-1,
    )

    print("Kör GridSearchCV för att hitta bästa alpha för Lasso...")
    grid.fit(X_train, y_train)

    best_model = grid.best_estimator_
    best_alpha = grid.best_params_["lasso__alpha"]
    print(f"Bästa alpha för Lasso: {best_alpha}")

    # Visa koefficienter (efter skalning) för att se vilka features som "överlever"
    lasso = best_model.named_steps["lasso"]
    print("Lasso-koefficienter:")
    for feat, coef in zip(FEATURES, lasso.coef_):
        print(f"  {feat}: {coef:.4f}")    

    # Skapa och träna modellen
    #model = LinearRegression()
    #model.fit(X_train, y_train)

    # Valideringsdata
    X_val = validation_data[FEATURES]
    y_val = validation_data[TARGET].astype(float)
    # Sanity ändring: Sätt produktion till 0 när solen är under horisonten
    sun_val = validation_data["sun_elevation_deg"]
    
    # Testdata
    X_test = test_data[FEATURES]
    y_test = test_data[TARGET].astype(float)
    # Sanity ändring: Sätt produktion till 0 när solen är under horisonten
    sun_test = test_data["sun_elevation_deg"]

    # Utvärdera modellen
    val_metrics = evaluate_model("Validation", best_model, X_val, y_val, sun_val)
    test_metrics = evaluate_model("Test", best_model, X_test, y_test, sun_test)

    return best_model, val_metrics, test_metrics

def clean_and_prepare_data(df):
    print("Rensar och förbereder data...")
    try:    
        # Viktigt för hela flödet att index är timestamp och sorterat!
        prepared_data = df.set_index(pd.to_datetime(df["ts"], errors="coerce")).sort_index()
        # Det går att ha med sun_azimuth_deg som feature men eftersom huset är delvis mot söder blir azimuth fel då det går från 360 till 1 i söder.
        # Det förstör en linjär regression. Räkna om till sinus och cosinus.
        prepared_data["sun_azimuth_sin"] = np.sin(np.radians(prepared_data["sun_azimuth_deg"]))
        prepared_data["sun_azimuth_cos"] = np.cos(np.radians(prepared_data["sun_azimuth_deg"]))

        # Ta bort dagens data för dagens datum eftersom den är ofullständig, mål-kolumnen är inte komplett och innehåller NULL för framtida tider idag.
        yesterday = datetime.now() - timedelta(days=1)
        prepared_data = prepared_data.loc[prepared_data.index.date <= yesterday.date()]
        return prepared_data
    except Exception as e:
        if e.args[0] == TOMORROW:
            raise Exception(f"Fel vid datarensning. {e} Det finns ingen data för morgondagen ({TOMORROW}) i databasen. Denna körning kan bara göras mellan 15:00 och 23:00 dagen innan för att få korrekt prediktion för morgondagen.")
        else:
            raise Exception(f"Fel vid datarensning: {e}")

def tomorrow_data(df):
    print("Extraherar data för morgondagen...")
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
    print("Skriver ut prediktion för morgondagen...")
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

def run_model(model, tomorrow_df):
    print("Kör modell för morgondagens prediktion...")
    X_tomorrow = tomorrow_df[FEATURES]
    predictions = model.predict(X_tomorrow)

    # Sanity ändring: Sätt produktion till 0 när solen är under horisonten
    # Plocka ut solhöjden som numpy-array
    sun_elev = tomorrow_df["sun_elevation_deg"].astype(float).values

    # Sätt all produktion till 0 när solen är under horisonten
    predictions = np.where(sun_elev <= 0, 0.0, predictions)

    result = tomorrow_df.copy()
    result[TARGET] = predictions
    return result

def main():
    print("Startar PVBattery...")

    try:
        # Step 1: READ DATA. Importera data - Läs data från en databas-vy där data är samlad per kvart.
        raw_dataframe = read_ai_features_view()

        print(f"Kontroll att db-förbindelse fungerade. Hämtade {len(raw_dataframe)} rader från vy: ai_features_quarter_vw3")

        # Step 2: CLEAN DATA och PREPARE DATA rättare sagt kontrollera data. Vi vill veta att det finns data för träning och prediktion för imorgon
        # Raise exception med meddelande om det inte finns data för imorgon.
        tomorrow_df = tomorrow_data(raw_dataframe)
        cleaned_df = clean_and_prepare_data(raw_dataframe)

        # Step 3: TRAIN MODEL.
        # Ta bort sista 96 raderna (data innehåller ju tom mål-data (pv_power_w_avg) för morgondagen)
        cleaned_df = cleaned_df.iloc[:-96]   
        trained_model, val_metrics, test_metrics = train_and_validate_model(cleaned_df)

        # Step 3: RUN MODEL. Prediktion för morgondagen
        predictions_df = run_model(trained_model, tomorrow_df)

        # Step 4: OUTPUT RESULT. Filtrera data för morgondagen
        # Skriv ut prediktion för morgondagen i CSV-format, till excel och console
        output(predictions_df)

        # Räkna ut total produktion imorgon i kWh
        tomorrow_df["energy_kWh"] = predictions_df["pv_power_w_avg"].clip(lower=0) * 0.25 / 1000
        total_kWh = tomorrow_df["energy_kWh"].sum()
        print("Förväntad produktion imorgon:", total_kWh, "kWh")


    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
