import psycopg2

# Supabase PostgreSQL connection details
HOST = "aws-0-ap-southeast-1.pooler.supabase.com"  # Replace with your Supabase host
PORT = "5432"  # Supabase default PostgreSQL port
DBNAME = "postgres"  # Replace with your actual database name
USER = "postgres.edgipgqjsitghqlahajs"  # Replace with your Supabase username
PASSWORD = "gwganteng2003"  # Replace with your actual Supabase password

try:
    # Establish a connection to the Supabase PostgreSQL database
    connection = psycopg2.connect(
        dbname=DBNAME,
        user=USER,
        password=PASSWORD,
        host=HOST,
        port=PORT
    )

    cursor = connection.cursor()

    # Query to list all tables in the database
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables
        WHERE table_schema = 'public';
    """)

    tables = cursor.fetchall()

    if tables:
        print("✅ Tables in your Supabase database:")
        for table in tables:
            print(f" - {table[0]}")
    else:
        print("⚠️ No tables found in the database.")

except Exception as e:
    print("❌ Error connecting to the database:", e)

finally:
    # Clean up the connection
    if 'connection' in locals() and connection:
        connection.close()
        print("🔒 Connection closed.")
