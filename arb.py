# -*- coding: utf-8 -*-
__doc__ = """
Usage:
  {f}
  {f} [-h | --help]
  {f} [-c | --config <FILE>]
  {f} demo [-c | --config <FILE>]

Options:
  -h --help             : Show this message.
  -c --config <FILE>    : Specify configration file.
""".format(f = __file__)

import time
import json
import numpy as np
from pandas import DataFrame as df
import requests
import sys
import exchanges.ex_hitbtc
import exchanges.ex_binance
import tools
import loggers
import config
from docopt import docopt

args = docopt(__doc__)

if (args['--config'] is not None):
    config.read(args['--config'][0])
else:
    config.read('./config.ini')

# 動作モードの設定
demoflag = args['demo']
print('Demo mode' if demoflag else 'Trade mode.')

# ロガーのセットアップ
l = loggers.aggregator(loggers.console_logger())
if config.SLACK_FLAG == 1:
    l.append(loggers.slack_logger(config.SLACK_URL))
if config.FILE_LOG == 1:
    l.append(loggers.file_logger(config.FILE_NAME))

try:
    print(config.CRYPTO_BASE + "/" + config.CRYPTO_ALT)

    # 取引所1, 取引所2のclass
    t1 = exchanges.ex_hitbtc.client(config.HITB_APIKEY, config.HITB_SECKEY, config.CRYPTO_BASE, config.CRYPTO_ALT)
    t2 = exchanges.ex_binance.client(config.BINA_APIKEY, config.BINA_SECKEY, config.CRYPTO_BASE, config.CRYPTO_ALT)

    # まとめたclass
    # インスタンス作成時にticksizeを出力
    ex = tools.exchange(t1, t2, l, config.BINA_BNBBUY)

    # API が正常に働いてるかチェック
    ex.check_api_state()

    # 閾値の設定
    thrd_up = config.threshold_up
    thrd_down = config.threshold_down
    chrate_up = thrd_up-1.001
    chrate_down = thrd_down-1.001

    # パラメータの初期化
    reportflag = 1
    trade_val = 0.
    cnt = 0
    tradeflag, tradable_value, t1_ask, t2_ask = ex.rate_c(thrd_up, thrd_down)

    if (demoflag):
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
    else:
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
finally:
    l.shutdown()
