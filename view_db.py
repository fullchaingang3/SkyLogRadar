import sqlite3

conn = sqlite3.connect("skylog.db")
cursor = conn.cursor()

cursor.execute('SELECT * FROM aircraft_passes')

rows = cursor.fetchall()

for row in rows:
    print(row)

conn.close()
