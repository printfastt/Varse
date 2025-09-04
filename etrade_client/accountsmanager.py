import logging
from logging.handlers import RotatingFileHandler
import json
import pandas as pd
from pygments.lexers import q
import config

logger = logging.getLogger('my_logger')
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler("python_client.log", maxBytes=5*1024*1024, backupCount=3)
FORMAT = "%(asctime)-15s %(message)s"
fmt = logging.Formatter(FORMAT, datefmt='%m/%d/%Y %I:%M:%S %p')
handler.setFormatter(fmt)
logger.addHandler(handler)


class AccountsManager:
    def __init__(self, session, base_url):
        self.session = session
        self.base_url = base_url
        self.accounts_list = []
        # self.account = None

        self._load_accounts()
        self.num_of_accounts = len(self.accounts_list)


    def _load_accounts(self):
        url = self.base_url + "/v1/accounts/list.json"

        #call api
        response = self.session.get(url)
        logger.debug("Request Header (_load_accounts): %s", response.request.headers)

        #if no error
        if response is not None and response.status_code == 200:
            parsed = json.loads(response.text)  #convert json data into python objects
            logger.debug("Response Body: %s", json.dumps(parsed, indent=4, sort_keys=True)) #converts back into json, puts in logger
            #AccountListResponse -> Accounts -> Account -> 0-4 dict accountId, accountIdkey...
            data = response.json()
            if data is not None and "AccountListResponse" in data and "Accounts" in data["AccountListResponse"] and "Account" in data["AccountListResponse"]["Accounts"]:
                accounts = data["AccountListResponse"]["Accounts"]["Account"]
                self.accounts_list[:] = [Account(d, parent=self) for d in accounts if d.get('accountStatus') != 'CLOSED' and d.get('closedDate') == 0]
            else:
                logger.debug("Response Body: %s", response.text)
                if response is not None and response.headers['Content-Type'] == 'application/json' \
                    and "Error" in response.json() and "message" in response.json()["Error"] \
                    and response.json()["Error"]["message"] is not None:
                    print("Error: " + data["Error"]["message"])
                else:
                    print("AccountList API Service error")
        else:
            logger.debug("Response Body: %s", response.text)
            if response is not None and response.headers['Content-Type'] == 'application/json' \
                    and "Error" in response.json() and "message" in response.json()["Error"] \
                    and response.json()["Error"]["message"] is not None:
                print("Error: " + response.json()["Error"]["message"])
            else:
                print("Error: AccountList API service error")

    #need to add error handling to if's
    def fetch_portfolio(self, accountIdKey:str):
        """
        response layout:
        PortfolioResponse:
            AccountPortfolio:
                Position:
                    Product:
                        symbol:
                        securityType:
                    Quick:
                        change: float
                        changePct: float
                        lastTrade: float
                        volume: integer
                    daysGain: float
                    daysGainPct: float
                    pricePaid:float
                    quantity: float
                    totalCost:
                    totalGain:
                    totalGainPct:
            accountId:
            totalPages:

        """
        url = f"{self.base_url}/v1/accounts/{accountIdKey}/portfolio.json"
        params = {"totalsRequired": True}
        # headers = {"consumerkey": config["DEFAULT"]["CONSUMER_KEY"]}

        response = self.session.get(url, params=params)
        logger.debug("Request Header (_fetch_portfolio): %s", response.request.headers)
        positions = {}
        accountTotals = {}


        #need to add more thorough error checking
        if response is not None and response.status_code == 200:
            parsed = json.loads(response.text)
            logger.debug("Response Body: %s", json.dumps(parsed, indent=4, sort_keys=True))

            data = response.json()
            if data is not None and "PortfolioResponse" in data:
                try:
                    if "Totals" in data["PortfolioResponse"]:
                        accountTotals = data["PortfolioResponse"]["Totals"]

                    if "AccountPortfolio" in data["PortfolioResponse"]:
                        for acctPortfolio in data["PortfolioResponse"]["AccountPortfolio"]:
                            if acctPortfolio is not None and "Position" in acctPortfolio:
                                for index, position in enumerate(acctPortfolio["Position"]):
                                    positions[index] = position
                except Exception as e:
                    logger.error("failed to parse response: %s",e)
            else:
                logger.error("Portfolio API error: %s %s", response.status_code if response else None,
                             response.text if response else None)
        return positions, accountTotals



    def fetch_balances(self, accountIdKey:str, institutionType:str):
        url = self.base_url + "/v1/accounts/" + accountIdKey + "/balance.json"
        params = {'instType': institutionType, 'realTimeNAV': 'true'}
        headers = {"consumerkey": config.CONSUMER_KEY}

        response = self.session.get(url, params=params, headers=headers)
        logger.debug("Request url: %s", url)
        logger.debug("Request headers: %s", response.request.headers)
        
        balances = {}
        
        # Error handling and response parsing
        if response is not None and response.status_code == 200:
            parsed = json.loads(response.text)
            logger.debug("Response Body: %s", json.dumps(parsed, indent=4, sort_keys=True))
            
            data = response.json()
            if data is not None and "BalanceResponse" in data:
                try:
                    # Extract ComputedBalance data as requested
                    if "Computed" in data["BalanceResponse"]:
                        balances = data["BalanceResponse"]["Computed"]
                    elif "ComputedBalance" in data["BalanceResponse"]:
                        balances = data["BalanceResponse"]["ComputedBalance"]
                except Exception as e:
                    logger.error("Failed to parse balance response: %s", e)
            else:
                logger.error("Balance API error: %s %s", response.status_code if response else None,
                           response.text if response else None)
        else:
            logger.debug("Response Body: %s", response.text)
            if response is not None and response.headers['Content-Type'] == 'application/json' \
                    and "Error" in response.json() and "message" in response.json()["Error"] \
                    and response.json()["Error"]["message"] is not None:
                print("Error: " + response.json()["Error"]["message"])
            else:
                print("Error: Balance API service error")
        
        return balances




class Account:
    def __init__(self, account, parent=None):
        self.parent = parent
        self.account_info = account
        self.accountIdKey = account.get('accountIdKey')

        self.positionsRaw, self.accounttotalsRaw = parent.fetch_portfolio(self.accountIdKey)
        self.positions = None
        self.accounttotals = None
        self._build_positions_df()
        self._build_accounttotals_df()


        self.balancesRaw = parent.fetch_balances(self.accountIdKey, self.account_info.get('institutionType'))
        self.balances = None
        self._build_balances_df()



    def get_positions_raw(self):
        if self.positionsRaw is not None:
            return self.positionsRaw
        else:
            print(f"Account {self.accountIdKey} has no positions")
            return None

    def get_positions(self):
        if self.positions is None:
            self._build_positions_df()
            return self.positions
        else:
            return self.positions

    def _build_positions_df(self):
        if self.positionsRaw is not None:
            data = []
            for pos in self.positionsRaw.values():
                data.append({
                    'symbol': pos['Product']['symbol'],
                    'typeCode': pos['Product']['productId']['typeCode'],
                    'securityType': pos['Product']['securityType'],
                    'strikePrice': pos['Product']['strikePrice'],
                    'expiryDay': pos['Product']['expiryDay'],
                    'expiryMonth': pos['Product']['expiryMonth'],
                    'expiryYear': pos['Product']['expiryYear'],

                    'change': pos['Quick']['change'],
                    'changePct': pos['Quick']['changePct'],
                    'lastTrade': pos['Quick']['lastTrade'],
                    'lastTradeTime': pos['Quick']['lastTradeTime'],
                    'quoteStatus': pos['Quick']['quoteStatus'],
                    'volume': pos['Quick']['volume'],

                    'adjPrevClose': pos['adjPrevClose'],
                    'commissions': pos['commissions'],
                    'costPerShare': pos['costPerShare'],
                    'dateAcquired': pos['dateAcquired'],
                    'daysGain': pos['daysGain'],
                    'daysGainPct': pos['daysGainPct'],
                    'lotsDetails': pos['lotsDetails'],
                    'marketValue': pos['marketValue'],
                    'otherFees': pos['otherFees'],
                    'pctOfPortfolio': pos['pctOfPortfolio'],
                    'positionId': pos['positionId'],
                    'positionIndicator': pos['positionIndicator'],
                    'positionType': pos['positionType'],
                    'pricePaid': pos['pricePaid'],
                    'quantity': pos['quantity'],
                    'quoteDetails': pos['quoteDetails'],
                    'symbolDescription': pos['symbolDescription'],
                    'todayCommissions': pos['todayCommissions'],
                    'todayFees': pos['todayFees'],
                    'todayPricePaid': pos['todayPricePaid'],
                    'todayQuantity': pos['todayQuantity'],
                    'totalCost': pos['totalCost'],
                    'totalGain': pos['totalGain'],
                    'totalGainPct': pos['totalGainPct']
                })
                positions = pd.DataFrame(data)
                positions.index.name = "#"
                self.positions = positions
        else:
            self.positions = None
            print(f"Account {self.accountIdKey} has no positions")

    def get_accounttotals_raw(self):
        if self.accounttotalsRaw is not None:
            return self.accounttotalsRaw
        else:
            print(f"Account {self.accountIdKey} has no positions")
            return None

    def get_accounttotals(self):
        if self.accounttotals is None:
            self._build_accounttotals_df()
            return self.accounttotals
        else:
            return self.accounttotals

    def _build_accounttotals_df(self):
        if self.accounttotalsRaw:
            if isinstance(self.accounttotalsRaw, dict):
                df = pd.Series(self.accounttotalsRaw)
                print("hello")
            else:
                raise TypeError(f"Unexpected type for accounttotalsRaw: {type(self.accounttotalsRaw)}")
            self.accounttotals = df
            print("hello")
        else:
            self.accounttotals = None
            print(f"Account {self.accountIdKey} has no positions")

    def get_balances_raw(self):
        if self.balancesRaw is not None:
            return self.balancesRaw
        else:
            print(f"Account {self.accountIdKey} has no balance data")
            return None

    def get_balances(self):
        if self.balances is None:
            self._build_balances_df()
            return self.balances
        else:
            return self.balances

    def _build_balances_df(self):
        if self.balancesRaw:
            if isinstance(self.balancesRaw, dict):
                df = pd.Series(self.balancesRaw)
                # df.name = "Balance"
            else:
                logger.error(f"Unexpected type for balancesRaw: {type(self.balancesRaw)}")
                df = None
            self.balances = df
            print("hello")
        else:
            self.balances = None
            print(f"Account {self.accountIdKey} has no balance data")







