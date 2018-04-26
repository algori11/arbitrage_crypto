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
print('Demo mode' if demoflag else 'Trade mode')

# ロガーのセットアップ
l = loggers.aggregator(loggers.console_logger())
if config.SLACK_FLAG == 1:
    l.append(loggers.slack_logger(config.SLACK_URL))
if config.LINE_FLAG == 1:
    l.append(loggers.line_logger(config.LINE_TOKEN))
if config.FILE_LOG == 1:
    l.append(loggers.file_logger(config.FILE_NAME))

try:
    print(config.CRYPTO_BASE + "/" + config.CRYPTO_ALT)

    # 取引所1, 取引所2のclass
    exec("t1 = ccxt.{}({{'apiKey': '{}', 'secret': '{}'}})".format(config.NAME1, config.APIKEY1, config.SECKEY1))
    exec("t2 = ccxt.{}({{'apiKey': '{}', 'secret': '{}'}})".format(config.NAME2, config.APIKEY2, config.SECKEY2))
    t1.name = config.NAME1
    t2.name = config.NAME2
    
    # 取引所インスタンスの修飾
    t1 = buffer.buffer(t1, config.PASSWORDS)
    t2 = buffer.buffer(t2, config.PASSWORDS)
    
    # timeoutの時間を2秒に変更
    t1.timeout = 2000
    t2.timeout = 2000
    
    # まとめたclassを作成
    # インスタンス作成時にticksizeを出力
    ex = tools.exchange(t1, t2, config.CRYPTO_BASE, config.CRYPTO_ALT, l, config.BNBBUY, config.BIXBUY)

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

                ex.logger.log(time.asctime()[4:-5], 1, tradable_value, "{:.8f}".format(tradable_value*chrate_up*t1_ask))
            
            # down時の処理(t2のほうが高い場合)
            if tradeflag == -1:
                ex.logger.log(time.asctime()[4:-5], -1, tradable_value, "{:.8f}".format(tradable_value*chrate_down*t2_ask))
            
            # 休む（アクセス規制回避）
            time.sleep(3)
    else:
        # アービトラージ
        
        while True:
            
            # 取引の直後のbalanceの更新とログの出力
            if reportflag == 1:
                t1_base, t1_alt, t2_base, t2_alt = np.array(ex.balances())
                ex.status(t1_base, t1_alt, t2_base, t2_alt, trade_val, tradeflag)
                # detailの出力（取引したときのbest bid/arbを表示（取引所のサイトの約定価格と比較して、うまく稼働してるかをチェックできます））
                # ex.status_detail(t1_base, t1_alt, t2_base, t2_alt, trade_val, tradeflag, amp*t1_ask, amp*t2_ask, amp*t1_bid, amp*t2_bid)
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
                else:
                    reportflag = 0
            
            # down時の処理
            if tradeflag == -1:
                trade_val = min(val_down*0.8, tradable_value)
                if trade_val >= ex.minsize:
                    ex.order_down(trade_val, chrate_down, int(t1_alt < t2_base/t2_ask), t2_bid*0.99, t1_ask*1.01)
                    reportflag = 1
                else:
                    reportflag = 0
            
            # 休む（アクセス規制回避）
            time.sleep(3)
            
            # 何もないときもたまにbalance更新
            cnt += 1
            if cnt%10 == 0:
                new_t1_base, new_t1_alt, new_t2_base, new_t2_alt = np.array(ex.balances())
                if new_t1_base != t1_base or new_t2_base != t2_base or new_t1_alt != t1_alt or new_t2_alt != t2_alt:
                    reportflag = 1
                else:
                    reportflag = 0



finally:
    l.shutdown()
