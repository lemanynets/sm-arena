
import sqlite3
import sys
import os

def check_order(order_id):
    db_path = os.path.join("app", "sm_arena.db")
    if not os.path.exists(db_path):
        db_path = "sm_arena.db"
    
    print(f"Checking DB: {db_path}")
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM orders WHERE order_id=?", (order_id,))
        row = cur.fetchone()
        if row:
            print(f"FOUND: {dict(row)}")
        else:
            print("NOT FOUND")
        conn.close()
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    check_order(sys.argv[1] if len(sys.argv) > 1 else "5e697eaa7b8c49dcb57710e919a18558")
