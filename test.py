import sqlite3
db = sqlite3.connect('mydb.db')
cursor = db.cursor()
cursor.execute("SELECT * FROM notes WHERE city = 'Москва'")
print(not(cursor.fetchall()))