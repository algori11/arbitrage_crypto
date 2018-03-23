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
import loggers

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
FILE_LOG = int(inifile.get('FILE_LOGGING', "FLAG"))
FILE_NAME = inifile.get('FILE_LOGGING', "NAME")

# ロガーのセットアップ
l = [loggers.console_logger]
if SLACK_FLAG == 1:
    l.append(loggers.slack_logger(SLACK_URL))
if FILE_LOG == 1:
    l.append(loggers.file_logger(FILE_NAME))

print(CRYPTO_BASE + "/" + CRYPTO_ALT)

# 取引所1, 取引所2のclass
t1 = exchanges.ex_hitbtc.client(HITB_APIKEY, HITB_SECKEY, CRYPTO_BASE, CRYPTO_ALT)
t2 = exchanges.ex_binance.client(BINA_APIKEY, BINA_SECKEY, CRYPTO_BASE, CRYPTO_ALT)

# まとめたclass
# インスタンス作成時にticksizeを出力
ex = tools.exchange(t1, t2, l, BINA_BNBBUY)

# API が正常に働いてるかチェック
ex.check_api_state()

thrd_up = threshold_up
thrd_down = threshold_down
reportflag = 1
trade_val = 0.
chrate_up = thrd_up-1.001
chrate_down = thrd_down-1.001
cnt = 0

tradeflag, tradable_value, t1_ask, t2_ask = ex.rate_c(thrd_up, thrd_down)

while True:

    # 板監視
    tradeflag, tradable_value, t1_ask, t2_ask = ex.rate_c(thrd_up, thrd_down)

    # up時の処理(t1のほうが高い場合)
    if tradeflag == 1:
        print(1, time.asctime()[4:-5], tradable_value, "{:.8f}".format(tradable_value*chrate_up*t1_ask))
    
    # down時の処理(t2のほうが高い場合)
    if tradeflag == -1:
        print(-1, time.asctime()[4:-5], tradable_value, "{:.8f}".format(tradable_value*chrate_down*t2_ask))
    
    # 休む（アクセス規制回避）
    time.sleep(3)