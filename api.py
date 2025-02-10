from flask import Flask, request, jsonify
import mysql.connector
from datetime import datetime
from rag import create_pipeline  # Assuming you have this module
from dotenv import load_dotenv
import os

load_dotenv()

rag_chain = create_pipeline()

app = Flask(__name__)

# MySQL Configuration (using environment variables)
DB_HOST = os.getenv('MYSQL_HOST')
DB_USER = os.getenv('MYSQL_USER')
DB_PASSWORD = os.getenv('MYSQL_PASSWORD')
DB_NAME = os.getenv('MYSQL_DB')  # Database name from .env


def get_db_connection():
    try:
        mydb = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        return mydb
    except mysql.connector.Error as err:
        print(f"Database connection error: {err}")
        return None

def create_database_if_not_exists():
    mydb_root = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD
    )
    root_cursor = mydb_root.cursor()
    try:
        root_cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
        mydb_root.commit()
        print(f"Database '{DB_NAME}' created (if it didn't exist).")  # Confirmation
    except mysql.connector.Error as err:
        print(f"Error creating database: {err}")
    finally:
        root_cursor.close()
        mydb_root.close()


def create_table_if_not_exists(mydb):
    mycursor = mydb.cursor()
    try:
        mycursor.execute(f"USE {DB_NAME}")
        mycursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                timestamp DATETIME,
                role VARCHAR(255),
                content TEXT
            )
        """)
        mydb.commit()
        print("Table 'chat_history' created (if it didn't exist).") # Confirmation
    except mysql.connector.Error as err:
        print(f"Error creating table: {err}")
    finally:
        mycursor.close()


@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_query = data.get('query')

    if not user_query:
        return jsonify({'error': 'Query is required'}), 400

    create_database_if_not_exists()

    mydb = get_db_connection()
    if not mydb:
        return jsonify({'error': 'Database connection failed'}), 500

    create_table_if_not_exists(mydb)

    mycursor = mydb.cursor()
    try:
        mycursor.execute("INSERT INTO chat_history (timestamp, role, content) VALUES (%s, %s, %s)",
                       (datetime.now(), 'user', user_query))
        mydb.commit()

        answer = ""
        for chunk in rag_chain.stream(user_query):
            answer += chunk

        mycursor.execute("INSERT INTO chat_history (timestamp, role, content) VALUES (%s, %s, %s)",
                       (datetime.now(), 'system', answer))
        mydb.commit()

        return jsonify({'answer': answer})

    except mysql.connector.Error as err:
        mydb.rollback()
        return jsonify({'error': f"Database error: {err}"}), 500

    finally:
        mycursor.close()
        mydb.close()


@app.route('/history', methods=['GET'])
def history():
    create_database_if_not_exists()

    mydb = get_db_connection()
    if not mydb:
        return jsonify({'error': 'Database connection failed'}), 500

    create_table_if_not_exists(mydb)

    mycursor = mydb.cursor()
    try:
        mycursor.execute("SELECT id, timestamp, role, content FROM chat_history ORDER BY id ASC")
        rows = mycursor.fetchall()
        history = [{'id': row[0], 'timestamp': row[1], 'role': row[2], 'content': row[3]} for row in rows]
        return jsonify({'history': history})
    except mysql.connector.Error as err:
        return jsonify({'error': f"Database error: {err}"}), 500
    finally:
        mycursor.close()
        mydb.close()

#if __name__ == '__main__':
#    app.run(host='0.0.0.0', port=os.getenv("FLASK_PORT"), debug=True)
