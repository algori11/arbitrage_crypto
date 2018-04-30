# -*- coding: utf-8 -*-
__doc__ = """
Usage:
  {f}
  {f} [-h | --help]
  {f} [-c | --config <FILE>]
  {f} demo [-c | --config <FILE>]
  {f} time [-c | --config <FILE>]

Options:
  -h --help             : Show this message.
  -c --config <FILE>    : Specify configration file.
""".format(f = __file__)

import time
import json
import numpy as np
import requests
import sys
import tools
import loggers
import config
import ccxt
import buffer
from docopt import docopt

args = docopt(__doc__)

if (args['--config']):
    config.read(args['--config'][0])
else:
    config.read('./config.ini')

# 動作モードの設定
demoflag = args['demo']
timeflag = args['time']

if demoflag: print('Demo mode')
elif timeflag: print('Time mode')
else: print('Trade mode')

# ロガーのセットアップ
l = loggers.aggregator(loggers.console_logger())
if config.SLACK_FLAG == 1:
    l.append(loggers.slack_logger(config.SLACK_URL))
if config.LINE_FLAG == 1:
    l.append(loggers.line_logger(config.LINE_TOKEN))
if config.FILE_LOG == 1:
    l.append(loggers.file_logger(config.FILE_NAME))

try:

    # 取引所1, 取引所2のclass
    exec("t1 = ccxt.{}({{'apiKey': '{}', 'secret': '{}'}})".format(config.NAME1, config.APIKEY1, config.SECKEY1))
    exec("t2 = ccxt.{}({{'apiKey': '{}', 'secret': '{}'}})".format(config.NAME2, config.APIKEY2, config.SECKEY2))
    t1.name = config.NAME1
    t2.name = config.NAME2
    
    # 取引通貨などの情報をまとめたclass
    info_set = tools.information(config.CRYPTO_BASE, config.CRYPTO_ALT, config.PASSWORDS, config.BNBBUY, config.BIXBUY)
    
    # 取引所インスタンスの修飾
    t1 = buffer.buffer(t1, info_set)
    t2 = buffer.buffer(t2, info_set)
    
    # まとめたclassを作成
    # インスタンス作成時にticksizeを出力
    ex = tools.exchange(t1, t2, info_set, l)

    # API が正常に働いてるかチェック（authentication success）
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
    tradeflag, tradable_value, t1_ask, t2_ask, t1_bid, t2_bid = ex.rate_c(thrd_up, thrd_down)
    
    #桁合わせ(detail出力, デバッグ用)
    amp = 10**(-np.floor(np.log10(t1_ask)))

    if (demoflag):

        while True:

            # 板監視
            tradeflag, tradable_value, t1_ask, t2_ask, t1_bid, t2_bid = ex.rate_c(thrd_up, thrd_down)

            # up時の処理(t1のほうが高い場合)
            if tradeflag == 1:
                msg = "{}, {}, tradable: {:.8f}, estimated profit (BTC): {:.8f}".format(time.asctime()[4:-5], 1, tradable_value, tradable_value*chrate_up*t1_ask)
                ex.logger.log(msg)
                
            
            # down時の処理(t2のほうが高い場合)
            if tradeflag == -1:
                msg = "{}, {}, tradable: {:.8f}, estimated profit (BTC): {:.8f}".format(time.asctime()[4:-5], -1, tradable_value, tradable_value*chrate_down*t2_ask)
                ex.logger.log(msg)
            
            # 休む（アクセス規制回避）
            time.sleep(3)
            
    if (timeflag):
        t1times = np.zeros(10)
        t2times = np.zeros(10)
        i = 0
        
        while i < 10:
            sflag = 0
            while sflag == 0:
                try:
                    start_time = time.time()
                    ex.orderbook(ex.t1)
                    t1time = time.time()
                    ex.orderbook(ex.t2)
                    t2time = time.time()
                    
                    t1times[i] = t1time - start_time
                    t2times[i] = t2time - start_time

                    print("{}/10: {}: {:.4f}s, {}: {:.4f}s".format(i+1, t1.name, t1times[i], t2.name, t2times[i]))
                    sflag = 1
                    i += 1
                except Exception as e:
                    print(e)
                    time.sleep(1)
            time.sleep(3)
        print("median: {}: {:.4f}s, {}: {:.4f}s".format(t1.name, np.median(t1times), t2.name, np.median(t2times)))
        print("max: {}: {:.4f}s, {}: {:.4f}s".format(t1.name, np.max(t1times), t2.name, np.max(t2times)))
        print("min: {}: {:.4f}s, {}: {:.4f}s".format(t1.name, np.min(t1times), t2.name, np.min(t2times)))

    else:
        # アービトラージ
        
        while True:
            
            # 取引の直後のbalanceの更新とログの出力
            if reportflag == 1:
                t1_base, t1_alt, t2_base, t2_alt = np.array(ex.balances())
                ex.status(t1_base, t1_alt, t2_base, t2_alt, trade_val, tradeflag)
                reportflag = 0
            
            # 板監視
            tradeflag, tradable_value, t1_ask, t2_ask, t1_bid, t2_bid = ex.rate_c(thrd_up, thrd_down)
            
            # up(t1で売ってt2で買う, t1のほうが高い場合)に使える量
            val_up = min(t1_alt, t2_base/t2_ask)

            # down(t2で売ってt1で買う, t2のほうが高い場合)に使える量
            val_down = min(t2_alt, t1_base/t1_ask)

            # up時の処理
            if tradeflag == 1:
                trade_val = min(val_up*0.8, tradable_value)
                if trade_val >= ex.minsize:
                    ex.order_up(trade_val, chrate_up, int(t2_alt < t1_base/t1_ask), t1_bid*0.99, t2_ask*1.01)
                    reportflag = 1
            
            # down時の処理
            if tradeflag == -1:
                trade_val = min(val_down*0.8, tradable_value)
                if trade_val >= ex.minsize:
                    ex.order_down(trade_val, chrate_down, int(t1_alt < t2_base/t2_ask), t2_bid*0.99, t1_ask*1.01)
                    reportflag = 1

            
            # 休む（アクセス規制回避）
            time.sleep(3)
            
            # 何もないときもたまにbalance更新
            cnt += 1
            if cnt%10 == 0:
                new_t1_base, new_t1_alt, new_t2_base, new_t2_alt = np.array(ex.balances())
                if new_t1_base != t1_base or new_t2_base != t2_base or new_t1_alt != t1_alt or new_t2_alt != t2_alt:
                    reportflag = 1


finally:
    l.shutdown()
