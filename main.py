from db_reader import read_ai_features_view


def main():
    print("Starting PVBattery project...")

    try:
        # Read data from MariaDB
        df = read_ai_features_view()

        print(f"\nRetrieved {len(df)} records from ai_features_quarter_vw3")
        print("\nFirst few rows:")
        print(df.head(n=10))

        # Add your data processing logic here

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
