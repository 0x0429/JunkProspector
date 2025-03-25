import os
import sqlite3
import subprocess
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)
DB_NAME = "auction_items.db"

def reset_database():
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
        print("[Database] Old database removed.")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE lot_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            current_bid TEXT,
            description TEXT,
            url TEXT,
            analysis TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print("[Database] New database created.")

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        start_url = request.form.get('start_url')
        if start_url:
            reset_database()
            subprocess.Popen(["python", "JunkProspector.py", start_url])
            return redirect(url_for('index'))

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT name, current_bid, analysis, url FROM lot_items WHERE analysis IS NOT NULL AND analysis NOT LIKE "Dropped:%"')
    items = cursor.fetchall()
    conn.close()

    return render_template('index.html', items=items)

if __name__ == '__main__':
    reset_database()
    app.run(debug=True)
