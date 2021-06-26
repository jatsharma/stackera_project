# Imprt MYSQL connector
import mysql.connector
import os
from dotenv import load_dotenv

# Get .env variables
DOTENV_PATH = os.path.join(os.path.dirname(__file__), '../.env')

USER = os.environ.get('DB_USER')
HOST = os.environ.get('DB_HOST')
PORT = os.environ.get('DB_PORT')
DATABASE = os.environ.get('DB_NAME')

CONNECTION = mysql.connector.connect(user = USER, host = HOST, database = DATABASE, port = PORT)

def create_table():
    # Function to create table
    # Create table query
    tokens_info_create_table = '''
        CREATE TABLE IF NOT EXISTS tokens_info (
            token_id VARCHAR(255) NOT NULL,
            token_name TEXT NOT NULL,
            token_symbol VARCHAR(50) NOT NULL,
            token_totalLiquidity DECIMAL(65, 30) NOT NULL,
            token_totalSupply INT NOT NULL,
            token_tradeVolume DECIMAL(65, 30) NOT NULL,
            token_tradeVolumeUSD DECIMAL(65, 30) NOT NULL,
            token_txCount INT NOT NULL,
            token_untrackedVolumeUSD DECIMAL(65, 30) NOT NULL,
            PRIMARY KEY (token_id)
        );
        '''
    cursor = CONNECTION.cursor()
    # Execute query
    cursor.execute(tokens_info_create_table)
    cursor.close()

if __name__ == '__main__':
    create_table()
    CONNECTION.close()
