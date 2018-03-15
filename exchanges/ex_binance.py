# -*- coding: utf-8 -*-
import requests
import json
import numpy as np
import time
import hashlib, hmac
from pandas import DataFrame as df
from urllib.parse import urlencode

class client(object):
    def __init__(self, apikey, seckey, crypto_base, crypto_alt):
        self.name = "binance"
        self.url = "https://api.binance.com/api"
        self.seckey = seckey
        self.crypto_base = crypto_base
        self.crypto_alt = crypto_alt
        self.symbol = crypto_alt + crypto_base
        self.session = requests.session()
        self.session.headers.update({'Accept': 'application/json', 'User-Agent': 'binance/python', 'X-MBX-APIKEY': apikey})
    
    def btime(self):
        return self.session.get("%s/v1/time" % self.url, timeout=2).json()["serverTime"]
    
    # 暗号化
    def encrypt(self, query):
#         query['timestamp'] = int(time.time() * 1000)
        query['timestamp'] = int(self.btime())

        query_string = urlencode(query)
        query['signature'] = hmac.new(self.seckey.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
        plist = [(key, query[key]) for key in query]
        return plist
    
    # 最小取引量
    def tsize(self):
        sdata = self.session.get("%s/v1/exchangeInfo" % self.url, timeout=2).json()
        dd = df(sdata["symbols"])
        return float(dd[dd["symbol"]==self.symbol]["filters"][dd[dd["symbol"]==self.symbol].index[0]][1]["minQty"])
    
    # 板を返す{"ask":売り注文, "bid":買い注文}
    def orderbook(self):
        depth = self.session.get("%s/v1/depth" % self.url, params={"symbol":self.symbol, "limit":20}, timeout=2).json()
        asks = np.array([item[:2] for item in depth["asks"]]).astype(float)
        bids = np.array([item[:2] for item in depth["bids"]]).astype(float)
        return {"ask":asks, "bid":bids}
    
    # 残高[基軸, ペア通貨]
    def balance(self):
        plist = self.encrypt({})        
        balances = df(self.session.get("%s/v3/account" % self.url, params=plist, timeout=2).json()['balances'])
        bal_base = float((balances[balances["asset"]==self.crypto_base])["free"])
        bal_alt = float((balances[balances["asset"]==self.crypto_alt])["free"])
        return [bal_base, bal_alt]
    
    # BNB（手数料用）の残高確認
    def balancebnb(self):
        plist = self.encrypt({})        
        balances = df(self.session.get("%s/v3/account" % self.url, params=plist, timeout=2).json()['balances'])
        bal_bnb = float((balances[balances["asset"]=="BNB"])["free"])
        return bal_bnb
    
    # 注文
    def order(self, side, quantity, symbol=None):
        if symbol==None:
            symbol = self.symbol
        raw_data = {'symbol': symbol, 'side': side, 'quantity': quantity, "type":"market"}
        c_data = self.encrypt(raw_data)

        return self.session.post("%s/v3/order" % self.url, data=c_data).json()