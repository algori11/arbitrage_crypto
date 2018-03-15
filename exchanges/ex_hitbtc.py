# -*- coding: utf-8 -*-
import requests
import json
import numpy as np
from pandas import DataFrame as df

class client(object):
    def __init__(self, apikey, seckey, crypto_base, crypto_alt):
        self.name = "hitbtc"
        self.url = "https://api.hitbtc.com/api/2"
        if crypto_base == "USDT":
            crypto_base = "USD"
        self.crypto_base = crypto_base
        self.crypto_alt = crypto_alt
        self.symbol = crypto_alt + crypto_base
        self.session = requests.session()
        self.session.auth = (apikey, seckey)
    
    # 最小取引量
    def tsize(self):
        sdata = self.session.get("%s/public/symbol/%s" % (self.url, self.symbol), timeout=2).json()
        return float(sdata["quantityIncrement"])
    
    # 板を返す{"ask":売り注文, "bid":買い注文}
    def orderbook(self):
        depth = self.session.get("%s/public/orderbook/%s" % (self.url, self.symbol), timeout=2).json()
        asks = np.array(df(depth["ask"])).astype(float)[:20]
        bids = np.array(df(depth["bid"])).astype(float)[:20]
        return {"ask":asks, "bid":bids}
    
    # 残高[基軸, ペア通貨]
    def balance(self):
        balances = df(self.session.get("%s/trading/balance" % self.url, timeout=2).json())
        bal_base = float((balances[balances["currency"]==self.crypto_base])["available"])
        bal_alt = float((balances[balances["currency"]==self.crypto_alt])["available"])
        return [bal_base, bal_alt]
    
    # 注文
    def order(self, side, quantity, symbol=None):
        if symbol==None:
            symbol = self.symbol
        data = {'symbol': symbol, 'side': side, 'quantity': quantity, "type":"market", "timeInForce":"IOC"}

        return self.session.post("%s/order" % self.url, data=data).json()
