import sqlite3
import os

def check_db_schema(db_path):
    try:
        print(f"Checking schema for {db_path}:")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get a list of all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        for table in tables:
            table_name = table[0]
            print(f"\nTable: {table_name}")
            
            # Get table schema
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            print("Columns:")
            for column in columns:
                col_id, name, type_name, notnull, default_val, pk = column
                print(f"  - {name} ({type_name}){' PRIMARY KEY' if pk else ''}{' NOT NULL' if notnull else ''}")
            
            # Get sample data (first 5 rows)
            try:
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
                rows = cursor.fetchall()
                
                if rows:
                    print(f"\nSample data (first {len(rows)} rows):")
                    for row in rows:
                        print(f"  {row}")
                else:
                    print("\nNo data in table.")
            except Exception as e:
                print(f"Error getting sample data: {e}")
        
        conn.close()
    except Exception as e:
        print(f"Error checking database {db_path}: {e}")

print("Database Schema Analysis:")
print("-" * 50)

# Check both databases
check_db_schema("cipher_stats.db")
print("\n" + "-" * 50)
check_db_schema("ai_steg_stats.db") 