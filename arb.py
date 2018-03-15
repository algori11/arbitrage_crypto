# -*- coding: utf-8 -*-
import time
import json
import numpy as np
from pandas import DataFrame as df
import requests
import sys
import configparser
import exchanges.ex_hitbtc
import exchanges.ex_binance
import tools

inifile = configparser.ConfigParser()
inifile.read('./config.ini', 'UTF-8')

CRYPTO_BASE = inifile.get('settings', "BASE")
CRYPTO_ALT = inifile.get('settings', "ALT")
BINA_APIKEY = inifile.get('BINANCE', "APIKEY")
BINA_SECKEY = inifile.get('BINANCE', "SECRET")
BINA_BNBBUY = int(inifile.get('BINANCE', "BNBBUY"))

HITB_APIKEY = inifile.get('HitBTC', "APIKEY")
HITB_SECKEY = inifile.get('HitBTC', "SECRET")
threshold_up = float(inifile.get('settings', "threshold_up"))
threshold_down = float(inifile.get('settings', "threshold_down"))
SLACK_FLAG = int(inifile.get('SLACK', "FLAG"))
SLACK_URL = inifile.get('SLACK', "URL")

print(CRYPTO_BASE + "/" + CRYPTO_ALT)

# 取引所1, 取引所2のclass
t1 = exchanges.ex_hitbtc.client(HITB_APIKEY, HITB_SECKEY, CRYPTO_BASE, CRYPTO_ALT)
t2 = exchanges.ex_binance.client(BINA_APIKEY, BINA_SECKEY, CRYPTO_BASE, CRYPTO_ALT)

# まとめたclass
# インスタンス作成時にticksizeを出力
ex = tools.exchange(t1, t2, SLACK_FLAG, SLACK_URL, BINA_BNBBUY)

# API が正常に働いてるかチェック
ex.check_api_state()

# 閾値の設定
thrd_up = threshold_up
thrd_down = threshold_down
chrate_up = thrd_up-1.001
chrate_down = thrd_down-1.001

# パラメータの初期化
reportflag = 1
trade_val = 0.
cnt = 0
tradeflag, tradable_value, t1_ask, t2_ask = ex.rate_c(thrd_up, thrd_down)

# アービトラージ
while True:
    
    # 取引の直後のbalanceの更新とログの出力
    if reportflag == 1:
        t1_base, t1_alt, t2_base, t2_alt = np.array(ex.balances())
        ex.status(t1_base, t1_alt, t2_base, t2_alt, trade_val, tradeflag)
        reportflag = 0
    
    # 板監視
    tradeflag, tradable_value, t1_ask, t2_ask = ex.rate_c(thrd_up, thrd_down)
    
    # up(t1で売ってt2で買う, t1のほうが高い場合)に使える量
    val_up = min(t1_alt, t2_base/t2_ask)

    # down(t2で売ってt1で買う, t2のほうが高い場合)に使える量
    val_down = min(t2_alt, t1_base/t1_ask)

    # up時の処理
    if tradeflag == 1:
        trade_val = min(val_up*0.95, tradable_value)
        if ex.discr(trade_val) >= ex.dscrsize:
            ex.order_up(trade_val, chrate_up, int(t2_alt < t1_base/t1_ask))
            reportflag = 1
        else:
            reportflag = 0
    
    # down時の処理
    if tradeflag == -1:
        trade_val = min(val_down*0.8, tradable_value)
        if ex.discr(trade_val) >= ex.dscrsize:
            ex.order_down(trade_val, chrate_down, int(t1_alt < t2_base/t2_ask))
            reportflag = 1
        else:
            reportflag = 0
    
    # 休む（アクセス規制回避）
    time.sleep(3)
    
    # 何もないときもたまにbalance更新
    cnt += 1
    if cnt ==10 :
        t1_base, t1_alt, t2_base, t2_alt = np.array(ex.balances()) 
        cnt = 0


