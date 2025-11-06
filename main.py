import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.linear_model import LinearRegression
from db_reader import read_ai_features_view

TARGET = "pv_power_w_avg"
FEATURES  = ["weather_cloud_pct", "sun_azimuth_deg", "sun_elevation_deg", "is_daylight"]

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
    X_pred = X_pred.fillna(X_train.mean())  # enkel imputering
    X_pred_design = np.column_stack([np.ones(len(X_pred)), X_pred.values])
    y_hat = X_pred_design @ w

    # (valfritt) fysikstopp:
    y_hat = np.where(df.loc[mask_pred, "sun_elevation_deg"].values <= 0, 0.0, y_hat)
    y_hat = np.clip(y_hat, 0, None)
    df.loc[mask_pred, TARGET] = y_hat

    df = df.set_index(pd.to_datetime(df["ts"], errors="coerce")).sort_index()

    # Endast 2025-11-07 kl 10–14
    print(df.loc["2025-11-06"].between_time("05:00", "18:00", inclusive="left")[["pv_power_w_avg","weather_cloud_pct", "sun_azimuth_deg", "sun_elevation_deg", "is_daylight"]].to_csv(sep=';', index=True, decimal=','))

def main():
    print("Starting PVBattery project...")

    try:
        # Step 1: Läs data från vy
        dataframe = read_ai_features_view()

        print(f"\nCheck that db connection works. Retrieved {len(dataframe)} records from view: ai_features_quarter_vw3")
        print("\nFirst few rows:")
        print(dataframe.head(n=10))

        # Step 2: Processa data
        processed_dataframe = process(dataframe)


    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
