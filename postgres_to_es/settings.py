from dotenv import load_dotenv
from os import environ as env

load_dotenv()
db_host = env["db_host"]
db_port = env["db_port"]
db_name = env["db_name"]
db_user = env["db_user"]
db_password = env["db_password"]
db_scheme = env["db_scheme"]
sleep_time = 5
# base_es_url = "http://127.0.0.1:9200/"
base_es_url = "http://elasticsearch:9200/"
