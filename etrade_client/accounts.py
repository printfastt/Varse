import logging
from logging.handlers import RotatingFileHandler
import json

logger = logging.getLogger('my_logger')
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler("python_client.log", maxBytes=5*1024*1024, backupCount=3)
FORMAT = "%(asctime)-15s %(message)s"
fmt = logging.Formatter(FORMAT, datefmt='%m/%d/%Y %I:%M:%S %p')
handler.setFormatter(fmt)
logger.addHandler(handler)


class Accounts:
    def __init__(self, session, base_url):
        self.session = session
        self.base_url = base_url
        self.accounts = {}


    def account_list(self):
        url = self.base_url + "/v1/accounts/list.json"

        #call api
        response = self.session.get(url)
        logger.debug("Request Header: %s", response.request.headers)

        #if no error
        if response is not None and response.status_code == 200:
            parsed = json.loads(response.text)  #convert json data into python objects
            logger.debug("Response Body: %s", json.dumps(parsed, indent=4, sort_keys=True)) #converts back into json, puts in logger

            data = response.json()
            if data is not None and "AccountListResponse" in data and "AccountList" in data["AccountListResponse"] and "Account" in data["AccountListResponse"]["Account"]:
                accounts = data["AccountListResponse"]["Account"]["Account"]
