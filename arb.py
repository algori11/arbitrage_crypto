# -*- coding: utf-8 -*-
import time
import json
import numpy as np
from pandas import DataFrame as df
import requests
import hashlib, hmac
import sys
import configparser
from urllib.parse import urlencode

inifile = configparser.ConfigParser()
inifile.read('./config.ini', 'UTF-8')

CRYPTO_BASE = inifile.get('settings', "BASE")
CRYPTO_ALT = inifile.get('settings', "ALT")
BINA_APIKEY = inifile.get('BINANCE', "APIKEY")
BINA_SECKEY = inifile.get('BINANCE', "SECRET")
HITB_APIKEY = inifile.get('HitBTC', "APIKEY")
HITB_SECKEY = inifile.get('HitBTC', "SECRET")

threshold0 = float(inifile.get('settings', "threshold0"))
threshold1 = float(inifile.get('settings', "threshold1"))
SLACK_FLAG = int(inifile.get('SLACK', "FLAG"))
SLACK_URL = inifile.get('SLACK', "URL")

# HitBTC の板監視・残高確認・注文
class hitbtc(object):
    def __init__(self, apikey, seckey, crypto_base, crypto_alt):
        self.url = "https://api.hitbtc.com/api/2"
        self.crypto_base = crypto_base
        self.crypto_alt = crypto_alt
        self.symbol = crypto_alt + crypto_base
        self.session = requests.session()
        self.session.auth = (apikey, seckey)
    
    # 最小取引量
    def tsize(self):
        sdata = self.session.get("%s/public/symbol/%s" % (self.url, self.symbol), timeout=2).json()
        return float(sdata["quantityIncrement"])
    
    # 最小取引量(2)
    def ticksize(self):
        sdata = self.session.get("%s/public/symbol/%s" % (self.url, self.symbol), timeout=2).json()
        return float(sdata["tickSize"])
    
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

# Binance の板監視・残高確認・注文
    
class binance(object):
    def __init__(self, apikey, seckey, crypto_base, crypto_alt):
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


# HitBTCではUSDTの内部コードがUSDなので適応
if CRYPTO_BASE == "USDT":
    CRYPTO_BASE_H = "USD"
else:
    CRYPTO_BASE_H = CRYPTO_BASE
# BNB（手数料用）が少なくなったら買う
def bnbcheck(b_bnb, bnb_amount=1.):
    if b_bnb < bnb_amount:
        orderb = t2class.order("buy", bnb_amount, symbol="BNBBTC")
        errormsg(orderb)
        slack_post("bought" + str(bnb_amount) + "BNB")
    else:
        pass

# 両取引所の残高を取得
def balances():
    sflag = 0
    while sflag == 0:
        try:
            b_bnb = t2class.balancebnb()
            bnbcheck(b_bnb)
            # balanceを取得
            t1_base, t1_alt = t1class.balance()
            t2_base, t2_alt = t2class.balance()
            
            sflag = 1
        except (requests.ConnectTimeout, requests.ReadTimeout, json.JSONDecodeError, KeyError):
            time.sleep(1)

    return t1_base, t1_alt, t2_base, t2_alt

# 注文量の離散化
def discr(amount):
    return int(amount/dscrsize) * dscrsize

# Binanceでペア通貨を買い、HitBTCで売る
def state_up(ch_val, bflag):
    
    order2 = t2class.order("buy",discr(discr(ch_val)*(1.+chrate*bflag)))
    errormsg(order2)
    
    order1 = t1class.order("sell",discr(ch_val))
    errormsg(order1)
    return 1

# Binanceでペア通貨を売り、HitBTCで買う
def state_down(ch_val, bflag):
    
    order2 = t2class.order("sell",discr(ch_val))
    errormsg(order2)
    
    order1 = t1class.order("buy",discr(discr(ch_val)*(1.+chrate*bflag)))
    errormsg(order1)
    return 1

# 現在の状態を表示
def status(state, t1_base, t1_alt, t2_base, t2_alt, ch_val, tradeflag):
    slack_post("{} [{:.6f}, {}] ch:{} s:{}".format(time.asctime()[4:-5], 
                                                                             t1_base+t2_base, discr(t1_alt+t2_alt), discr(tradeflag*ch_val), state))

    
# 注文が通らなかったときのエラーメッセージを表示（それぞれの取引所のエラー時のレスポンスを利用）
def errormsg(input_order):
    
    if "msg" in input_order.keys(): # for Binance
        slack_post("Binance error:"+input_order["msg"])
        sys.exit()
        
    if "error" in input_order.keys(): # for HitBTC
        slack_post("HitBTC error:"+input_order["error"])
        sys.exit()
            
# メッセージの表示（Slackに投稿）
def slack_post(msg):
    print(msg)
    if SLACK_FLAG == 1:
        sflag = 0
        while sflag == 0:
            try:
                requests.post(SLACK_URL, data=json.dumps({'text': msg}), timeout=2)
                sflag = 1
            except Exception as e:
                print(e, 'error occurred')
                time.sleep(1)
    else:
        pass
    
# state検出(9割以上片方の通貨に偏っていたら2or-2, 7割以上だと1or-1を返す（正負は偏りの方向）)
def state_check(val_down, val_up):
    if val_down + val_up < dscrsize*12.:
        slack_post("total balance is too small")
        sys.exit()
    balance_ratio = val_up/(val_up+val_down)
    cflag = int(balance_ratio < 0.1) + int(balance_ratio < 0.3) - int(balance_ratio > 0.7) - int(balance_ratio > 0.9)
    return cflag, balance_ratio, 1.-balance_ratio #down, up

def rate_c(thrd_up, thrd_down):
    sflag = 0
    while sflag == 0:
        try:
            h_depth = t1class.orderbook()
            b_depth = t2class.orderbook()

            cumb_down = np.array([np.cumsum(b_depth["bid"][:, 1]), np.ones(20)])
            cumh_down = np.array([np.cumsum(h_depth["ask"][:, 1]), np.zeros(20)])
            cum_down = np.hstack((cumh_down, cumb_down))
            sorder_down = cum_down[1][np.argsort(cum_down[0])][:20]

            cumb_up = np.array([np.cumsum(b_depth["ask"][:, 1]), np.zeros(20)])
            cumh_up = np.array([np.cumsum(h_depth["bid"][:, 1]), np.ones(20)])
            cum_up = np.hstack((cumh_up, cumb_up))
            sorder_up = cum_up[1][np.argsort(cum_up[0])][:20]

            bi, hi = 0, 0
            ratelist_up = np.zeros((20,2))
            for si in range(20):
                so = sorder_up[si]
                if so == 0:
                    ratelist_up[si] = h_depth["bid"][hi][0]/b_depth["ask"][bi][0], cumb_up[0][bi]
                    bi +=1
                if so == 1:
                    ratelist_up[si] = h_depth["bid"][hi][0]/b_depth["ask"][bi][0], cumh_up[0][hi]
                    hi +=1

            bi, hi= 0, 0
            ratelist_down = np.zeros((20,2))
            for si in range(20):
                so = sorder_down[si]
                if so == 0:
                    ratelist_down[si] = b_depth["bid"][bi][0]/h_depth["ask"][hi][0], cumh_down[0][hi]
                    hi +=1
                if so == 1:
                    ratelist_down[si] = b_depth["bid"][bi][0]/h_depth["ask"][hi][0], cumb_down[0][bi]
                    bi +=1
            u_idx = np.sum(ratelist_up[:, 0] >= thrd_up)
            d_idx = np.sum(ratelist_down[:, 0] >= thrd_down)

            idc = np.sign(u_idx) - np.sign(d_idx)

            if idc == 0:
                tradable = 0
            if idc == 1:
                tradable = ratelist_up[u_idx -1][1]
            if idc == -1:
                tradable = ratelist_down[d_idx -1][1]
            sflag = 1
        except (requests.ConnectTimeout, requests.ReadTimeout, json.JSONDecodeError):
            time.sleep(1)
    
    return idc, tradable, h_depth["ask"][0][0], b_depth["ask"][0][0]

# それぞれの取引所のclass
t1class = hitbtc(HITB_APIKEY, HITB_SECKEY, CRYPTO_BASE_H, CRYPTO_ALT)
t2class = binance(BINA_APIKEY, BINA_SECKEY, CRYPTO_BASE, CRYPTO_ALT)

# 取引できる量の離散間隔
dscrsize = max(t1class.tsize(), t2class.tsize())
print("ticksize:"+str(dscrsize))

reportflag = 1
trade_val = 0.
chrate = threshold0 - 1.001
cnt = 0
t1_base, t1_alt, t2_base, t2_alt = np.array(balances())
tradeflag, tradable_value, t1_ask, t2_ask = rate_c(threshold0, threshold0)
h_state = 0
state = 0
thrd_up = threshold0
thrd_down = threshold0

while True:
    
    if reportflag == 1:
        t1_base, t1_alt, t2_base, t2_alt = np.array(balances())
    
    val_down = min(t2_alt, t1_base/t1_ask)
    val_up = min(t1_alt, t2_base/t2_ask)
    val_total = val_down + val_up
    
    c_state, b_ratio_up, b_ratio_down = state_check(val_down, val_up)
    
    if abs(c_state) ==2:
        h_state = c_state
    
    if h_state == 2:
        if c_state >=0:
            thrd_down = threshold1
            state = 1
        else:
            thrd_down = threshold0
            state = 0
        
    if h_state == -2:
        if c_state <=0:
            thrd_up = threshold1
            state = -1
        else:
            thrd_up = threshold0
            state = 0
            
    if reportflag == 1:
        status(state, t1_base, t1_alt, t2_base, t2_alt, trade_val, tradeflag)
        reportflag = 0
    
    tradeflag, tradable_value, t1_ask, t2_ask = rate_c(thrd_up, thrd_down)
    
    if state == 0:
        if tradeflag == -1:
            trade_val = min(val_down*0.8, tradable_value)
            reportflag = state_down(trade_val, int(t1_alt < t2_base/t2_ask))
            if val_down*0.8 < tradable_value:
                if (discr(val_down*0.15) != 0)*(val_down*0.95 < tradable_value)==1:
                    state_down(val_down*0.15, 0)
        if tradeflag == 1:
            trade_val = min(val_up*0.95, tradable_value)
            reportflag = state_up(trade_val, int(t2_alt < t1_base/t1_ask))
            
    #バランスが片側に寄りすぎた場合の処理(1)
    if state == 1:
        if tradeflag == -1:
            trade_val = min(val_total*(0.8-b_ratio_up), tradable_value)
            reportflag = state_down(trade_val, 0)
        if tradeflag == 1:
            trade_val = min(val_up*0.95, tradable_value)
            if trade_val > dscrsize:
                reportflag = state_up(trade_val, int(t2_alt < t1_base/t1_ask))
            
    #バランスが片側に寄りすぎた場合の処理(-1)
    if state == -1:
        if tradeflag == 1:
            trade_val = min(val_total*(0.8-b_ratio_down), tradable_value)
            reportflag = state_up(trade_val, 0)
        if tradeflag == -1:
            trade_val = min(val_down*0.8, tradable_value)
            if trade_val > dscrsize:
                reportflag = state_down(trade_val, int(t1_alt < t2_base/t2_ask))
                if val_down*0.8 < tradable_value:
                    if (discr(val_down*0.15) != 0)*(val_down*0.95 < tradable_value)==1:
                        state_down(val_down*0.15, 0)

                        
    time.sleep(3)
    cnt += 1
    if cnt ==10 :
    
        t1_base, t1_alt, t2_base, t2_alt = np.array(balances()) 
        cnt = 0