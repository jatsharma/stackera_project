# Flask RESTful API Project
## Flask backend connecting to Uniswap API

### Prerequisite
##### Requirements for the project to run
- Python 3.x
- MySQL
- Redis
- Other requirements can be installed by following command
 ```sh
pip install -r requrements.txt
```
##### Steps to start the project after everything is installed
- Initiate a MySQL DB and Store the required variables in .env file.
- Initiare a Redis DB and Store the required variables in .env file.
- When running the project for first time, run './single_run_scripts/create_tables.py' once to create required table.
---
## API ENDPOINTS
```sh
/tokens
```
- '/tokens' Endpoint returns available tokens on UNISWAP
- This endpoint can have 'sortBy', 'limit' and 'page' as Query strings.
```sh
/recentSwaps
```
- '/recentSwaps' Endpoint retuns swaps for the last 4 hours for which amountUSD is greater than 10000.
```sh
/ETHPrice
```
- 'ETHPrice' Endpoint gives latest Price of ETH.

Note: Other than these endpoints the app also saves details of all tokens available on UNISWAP in database table and updates it every 30 minutes.