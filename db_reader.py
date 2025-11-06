import os
import pymysql
import pandas as pd
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def get_db_connection():
    """
    Establish a connection to the MariaDB database.

    Returns:
        pymysql.connections.Connection: Database connection object
    """
    try:
        print(f"onnecting to MariaDB: {os.getenv('DB_PASSWORD')}")
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
    """
    Read data from the ai_features_quarter_vw3 view.

    Returns:
        pandas.DataFrame: DataFrame containing the view data
    """
    conn = None
    try:
        # Establish connection
        conn = get_db_connection()

        # Query the view
        query = "SELECT * FROM ai_features_quarter_vw3 ORDER BY ts"
        print(f"Executing query: {query}")

        # Read data into pandas DataFrame
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
        # Always close the connection
        if conn:
            conn.close()
            print("Database connection closed")


def read_custom_query(query):
    """
    Execute a custom SQL query and return results as DataFrame.

    Args:
        query (str): SQL query to execute

    Returns:
        pandas.DataFrame: Query results
    """
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
    # Example usage
    try:
        # Read from the view
        df = read_ai_features_view()

        # Display basic info
        print("\n=== DataFrame Info ===")
        print(df.info())

        print("\n=== First rows ===")
        print(df.head(n=10))

        print("\n=== Column names ===")
        print(df.columns.tolist())

        # Example: Filter or process data
        # df_filtered = df[df['some_column'] > 100]

    except Exception as e:
        print(f"Failed to read from database: {e}")
