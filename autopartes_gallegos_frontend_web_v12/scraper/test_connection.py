import pyodbc
from dotenv import load_dotenv
import os

load_dotenv()

connection_string = (
    f"DRIVER={{{os.getenv('DB_DRIVER')}}};"
    f"SERVER={os.getenv('DB_SERVER')};"
    f"DATABASE={os.getenv('DB_NAME')};"
    f"Trusted_Connection={os.getenv('DB_TRUSTED_CONNECTION')};"
    f"Encrypt={os.getenv('DB_ENCRYPT')};"
    f"TrustServerCertificate={os.getenv('DB_TRUST_SERVER_CERTIFICATE')};"
)

try:
    connection = pyodbc.connect(connection_string)

    cursor = connection.cursor()
    cursor.execute("SELECT DB_NAME(), SYSTEM_USER")

    result = cursor.fetchone()

    print("CONEXIÓN EXITOSA")
    print("Base de datos:", result[0])
    print("Usuario:", result[1])

    connection.close()

except Exception as e:
    print("ERROR DE CONEXIÓN:")
    print(e)