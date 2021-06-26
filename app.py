# Import required modules
from flask import Flask
from flask_restful import Api, Resource, request
from flask_mysqldb import MySQL
from dotenv import load_dotenv
import os, requests
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import redis

# LOAD .env file for required variables
DOTENV_PATH = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(DOTENV_PATH)

# Initiate Flask APP
APP = Flask(__name__)
# Add DB config
APP.config['MYSQL_HOST'] = os.environ.get('DB_HOST')
APP.config['MYSQL_PORT'] = os.environ.get('DB_PORT')
APP.config['MYSQL_USER'] = os.environ.get('DB_USER')
APP.config['MYSQL_DB'] = os.environ.get('DB_NAME')
APP.config['MYSQL_CHARSET'] = os.environ.get('DB_CHARSET')
# Create API instance
API = Api(APP)
# Create DB Instance
MYSQL = MySQL(APP)

# Get API URL
API_URL = os.environ.get("UNISWAP_API_URL")

# Connect to REDIS
REDIS = redis.Redis(host = os.environ.get('REDIS_HOST'), port = os.environ.get('REDIS_PORT'), db = os.environ.get('REDIS_DB'),
                    charset = os.environ.get('REDIS_CHARSET'), decode_responses = True)

###############################################################################################
def update_tokens_details():
    """
    This function helps us to keep our databse updated with latest tokens data available on the Exchange.
    We use this function every 30 minutes to update the database.
    """
    APP.logger.info("Updating tokens info from UNISWAP!")
    try:
        restructured_data = list()
        # We need to call the API multiple times to get all the data as it is not possible to get all rows in one call.
        for skip in range(0, 5001, 1000):
            # GraphQL query to get all available tokens.
            graphql_query = """
                {
                    tokens (orderBy: totalSupply, skip: %s, first: 1000) {
                        id
                        name
                        symbol
                        totalLiquidity
                        totalSupply
                        tradeVolume
                        tradeVolumeUSD
                        txCount
                        untrackedVolumeUSD
                    }
                }
                """ % skip
            # Call the API endpoint
            resp = requests.post(API_URL, json={"query": graphql_query})
            if resp.status_code == 200:
                pairs_data = resp.json()
                # Restructure the data to insert/update to database
                temp_restructured_data = [[row['id'], row['name'], row['symbol'], row['totalLiquidity'], row['totalSupply'],
                                            row['tradeVolume'], row['tradeVolumeUSD'], row['txCount'], row['untrackedVolumeUSD']] for row in pairs_data['data']['tokens']]
                # Add data to main data list
                restructured_data.extend(temp_restructured_data)

        if restructured_data:
            APP.logger.info("Extracted data for {} tokens".format(len(restructured_data)))
            with open('test.txt', 'w+', encoding='utf-8') as f:
                f.write(str(restructured_data))
            # Update DB if data was extracted.
            query = """
                    INSERT INTO tokens_info (token_id, token_name, token_symbol, token_totalLiquidity, token_totalSupply,
                        token_tradeVolume, token_tradeVolumeUSD, token_txCount, token_untrackedVolumeUSD)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE token_name = VALUES(token_name), token_symbol = VALUES(token_symbol), token_totalLiquidity = VALUES(token_totalLiquidity),
                        token_totalSupply = VALUES(token_totalSupply), token_tradeVolume = VALUES(token_tradeVolume), token_tradeVolumeUSD = VALUES(token_tradeVolumeUSD),
                        token_txCount = VALUES(token_txCount), token_untrackedVolumeUSD = VALUES(token_untrackedVolumeUSD);
                    """
            APP.logger.info("Updating database for all tokens!")
            # We need to create flask app context because we need to use DB outisde of Flask app.
            with APP.app_context():
                cursor = MYSQL.connection.cursor()
                cursor.executemany(query, restructured_data)
                MYSQL.connection.commit()
                cursor.close()
    except Exception as e:
        APP.logger.info("Error occured while calling UNISWAP API!: {}".format(e))
###################################################################################################
# API Classes


class GetTokens(Resource):
    """
    This API endpoint calls UNISWAP API with sorting param as per user input
    Also this API handles logic is as below:
    We decide the number of items from limit keyword, if limit is not present
    we default to 100 items per page.
    So we decide skip and limit param to pass to API accordingly.
    """
    def get(self):
        APP.logger.info("API call to Get tokens info!")
        # Set param availabe for sorting
        available_sort_params = ['tradeVolumeUSD', 'totalLiquidity', 'untrackedVolumeUSD']
        # Get request args
        args = request.args
        sortBy = args.get('sortBy')
        # If limit is not given we set it default to 100 same as UNISWAP API
        limit = args.get('limit', 100)
        page = args.get('page')
        optional_query = ""
        if limit:
            limit = int(limit)
        if page:
            page = int(page)
        # CASE sortBy
        if sortBy and sortBy in available_sort_params:
            optional_query += "orderBy: {}, orderDirection: desc, ".format(sortBy)
        elif sortBy and sortBy not in available_sort_params:
            # Return error if sortBy by is not available param for sorting
            return_message = {"message": "Please enter sortBy values from these only: {}".format(available_sort_params)}
            return return_message, 400
        elif not sortBy and page:
            return {"message": "Please provide key to sort by so that pagination data can be consistent."}, 400
        # CASE Limit
        if limit > 1000:
            return {"message": "Please provide limit less than 1000."}, 400
        optional_query += "first: {}, ".format(limit)
        # CASE Page
        if page:
            skip = int((page - 1) * limit)
            if skip > 5000:
                return {"message": "Page number out of range, please provide page no. less than {} for the same limit.".format((5000//limit) + 2)}, 400
            optional_query += "skip: {}".format(skip)

        if optional_query:
            # We only need to edit the optional_query string if any condition is available in it.
            optional_query = "({})".format(optional_query)

        # GraphQL query to get tokens data.
        graphql_query = """
            {
                tokens %s {
                    id
                    name
                    symbol
                    totalLiquidity
                    totalSupply
                    tradeVolume
                    tradeVolumeUSD
                    txCount
                    untrackedVolumeUSD
                }
            }
            """ % optional_query
        resp = requests.post(API_URL, json={"query": graphql_query})
        if resp.status_code == 200:
            return resp.json()
        else:
            return {"message": "Error occured while getting data from Uniswap, Please try again later."}, 400


class RecentSwaps(Resource):
    """
    This API endpoint get Swaps data from Uniswap for the last 4 hours,
    and only swaps with amountUSD > 10000.
    """
    def get(self):
        APP.logger.info("API call to get recent swaps details!")
        # Get Epoch time for now - 4 hour
        req_time = int((datetime.now() - timedelta(hours=4)).timestamp())
        graphql_query = """
            {
                swaps(orderBy:timestamp, orderDirection:desc, where: {timestamp_gte: %s, amountUSD_gt: 10000}) {
                    id
                    timestamp
                    amount0In
                    amount1In
                    amount0Out
                    amount1Out
                    amountUSD
                    pair{
                        id
                        token0{
                            symbol
                            decimals
                        }
                        token1{
                            symbol
                            decimals
                        }
                    }
                }
            }
            """ % req_time
        resp = requests.post(API_URL, json={"query": graphql_query})
        if resp.status_code == 200:
            return resp.json()
        else:
            return {"message": "Error occured while getting data from Uniswap, Please try again later."}, 400


class BundleETHPrice(Resource):
    """
    This API endpoint gets ETH price and caches it for 30 seconds,
    incase user calls the api again in 30 seconds.
    """
    def get(self):
        APP.logger.info("API call to get ETH Price!")
        # Check if cached price is available
        saved_price = REDIS.get("ETHPRICE")
        if saved_price:
            return {"ETHPRICE": REDIS.get("ETHPRICE")}
        APP.logger.info("Getting ETH price from UNISWAP!")
        graphql_query = """
            {
                bundle(id: "1" ) {
                ethPrice
                }
            }
            """
        # Call API to get data
        resp = requests.post(API_URL, json={"query": graphql_query})
        if resp.status_code == 200:
            resp_data = resp.json()
            if 'data' in resp_data and 'bundle' in resp_data['data'] and 'ethPrice' in resp_data['data']['bundle']:
                # Get ETH price
                eth_price = resp_data['data']['bundle']['ethPrice']
                # Store price to redis
                REDIS.setex(
                    "ETHPRICE",
                    timedelta(seconds = 30),
                    value = eth_price
                )
                return {"ETHPRICE": eth_price}
            return {"message": "Something went wrong, please try again after sometime"}, 400


###################################################################################################
# Create scheduler instance to schedule update_token_pairs job
scheduler = BackgroundScheduler()
# Add job to update token info every 30 minutes.
scheduler.add_job(func=update_tokens_details, trigger='interval', minutes=30)

# Add routes to API
API.add_resource(GetTokens, '/tokens')
API.add_resource(RecentSwaps, '/recentSwaps')
API.add_resource(BundleETHPrice, '/ETHPrice')

if __name__ == '__main__':
    # Start the scheduler
    scheduler.start()
    APP.run(debug=True)