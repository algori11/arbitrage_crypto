import time
import json
import numpy as np
import requests
import queue
import threading
import loggers_tri
import config_tri
import ccxt

from pandas import DataFrame as df

config_tri.read('config_tri.ini')
exec("t1 = ccxt.{}({{'apiKey': '{}', 'secret': '{}'}})".format(config_tri.NAME1, config_tri.APIKEY1, config_tri.SECKEY1))
t1.name = config_tri.NAME1

# ロガーのセットアップ
l = loggers_tri.aggregator(loggers_tri.console_logger())
if config_tri.SLACK_FLAG == 1:
    l.append(loggers_tri.slack_logger(config_tri.SLACK_URL))
if config_tri.LINE_FLAG == 1:
    l.append(loggers_tri.line_logger(config_tri.LINE_TOKEN))
if config_tri.FILE_LOG == 1:
    l.append(loggers_tri.file_logger(config_tri.FILE_NAME))

BASE1 = config_tri.CRYPTO_BASE1
BASE2 = config_tri.CRYPTO_BASE2
ALT = config_tri.CRYPTO_ALT
PAIR1 = BASE2 + "/" + BASE1
PAIR2 = ALT + "/" + BASE2
PAIR3 = ALT + "/" + BASE1
threshold = config_tri.threshold
print("exchange: {}".format(t1.name))
print("crypto: {} {} {}".format(BASE1, BASE2, ALT))
print("threshold: {}".format(threshold))

query_list = [PAIR1, PAIR2, PAIR3]


# 取引最小値（limit1のみBASE2換算, limit2とlimit3はALT換算）を取得
info = df(t1.fetch_markets())
limit1 = info[info["symbol"]==PAIR1]["limits"][info[info["symbol"]==PAIR1].index[0]]["amount"]["min"]
limit2 = info[info["symbol"]==PAIR2]["limits"][info[info["symbol"]==PAIR2].index[0]]["amount"]["min"]
limit3 = info[info["symbol"]==PAIR3]["limits"][info[info["symbol"]==PAIR3].index[0]]["amount"]["min"]


# 板を取得
# 取得にmaxtime以上の時間がかかったらやり直し（maxtimeには取引所にあわせた時間を指定してください.）
def get_orderbooks(maxtime):
    sflag = 0
    while sflag == 0:
        try:
            start = time.time()
            
            response = {}
            
            def query_worker(query_queue):
                query = query_queue.get()
                response[query]=t1.fetch_order_book(query, limit=10)
                query_queue.task_done()

            # queueを設定
            query_queue = queue.Queue()
            for q in query_list:
                query_queue.put(q)

            # Thread start
            while not query_queue.empty():
                w_thread = threading.Thread(target=query_worker, args=(query_queue,))
                w_thread.start()
            query_queue.join()
            
            book1 = response[PAIR1]
            book2 = response[PAIR2]
            book3 = response[PAIR3]
            interval = time.time()-start
            if interval < maxtime:
                sflag = 1
            else:
                time.sleep(1)
        except Exception as e:
            l.logger(str(time.asctime()[4:-5]) + str(e))
            time.sleep(1)
        
    return book1, book2, book3

# BASE1→BASE2→ALT→BASE1 のルート
# 期待収益率が閾値を超えてたら(期待利益率, 量（ALT単位）)を、超えてなかったら(0, 0)を返す
def root_u(ask1, ask2, bid3, threshold): 
    idx = np.zeros(3).astype(int)

    amount1 = np.cumsum(ask1[:, 1] * ask2[-1][0])
    amount2 = np.cumsum(ask2[:, 1])
    amount3 = np.cumsum(bid3[:, 1])

    ratio = bid3[:, 0][idx[2]]/(ask1[:, 0][idx[0]]* ask2[:, 0][idx[1]])
    if ratio < threshold:
        return 0, 0
    value = np.min([amount1[idx[0]], amount2[idx[1]], amount3[idx[2]]])

    for i in range(10):
        idx[np.argmin([amount1[idx[0]], amount2[idx[1]], amount3[idx[2]]])] += 1
        new_ratio = bid3[:, 0][idx[2]]/(ask1[:, 0][idx[0]]* ask2[:, 0][idx[1]])
        if new_ratio < threshold:
            break
        ratio = new_ratio
        value = np.min([amount1[idx[0]], amount2[idx[1]], amount3[idx[2]]])
    return ratio, value

# BASE1→ALT→BASE2→BASE1 のルート
# 期待収益率が閾値を超えてたら(期待利益率, 量（ALT単位）)を、超えてなかったら(0, 0)を返す
def root_d(bid1, bid2, ask3, threshold): 
    idx = np.zeros(3).astype(int)

    amount1 = np.cumsum(bid1[:, 1] * bid2[-1][0])
    amount2 = np.cumsum(bid2[:, 1])
    amount3 = np.cumsum(ask3[:, 1])

    ratio = bid1[:, 0][idx[0]] * bid2[:, 0][idx[1]]/ask3[:, 0][idx[2]]
    if ratio < threshold:
        return 0, 0
    value = np.min([amount1[idx[0]], amount2[idx[1]], amount3[idx[2]]])

    for i in range(10):
        idx[np.argmin([amount1[idx[0]], amount2[idx[1]], amount3[idx[2]]])] += 1
        new_ratio = bid1[:, 0][idx[0]] * bid2[:, 0][idx[1]]/ask3[:, 0][idx[2]]
        if new_ratio < threshold:
            break
        ratio = new_ratio
        value = np.min([amount1[idx[0]], amount2[idx[1]], amount3[idx[2]]])
    return ratio, value

# 初期化
count = 0

# サーバの許容待ち時間(秒)
maxtime = 0.2

# 市場の歪み検出
while True:
    # 板を取得
    book1, book2, book3 = get_orderbooks(maxtime)
    ask1, bid1 = np.array(book1["asks"]).astype(np.float), np.array(book1["asks"]).astype(np.float)
    ask2, bid2 = np.array(book2["asks"]).astype(np.float), np.array(book2["bids"]).astype(np.float)
    ask3, bid3 = np.array(book3["asks"]).astype(np.float), np.array(book3["bids"]).astype(np.float)
    
    # 歪みを計算
    ratio_u, value_u = root_u(ask1, ask2, bid3, threshold)
    ratio_d, value_d = root_d(bid1, bid2, ask3, threshold)
    
    # （取引できる最小量(ALT単位)を計算）
    limit0 = max(limit1*ask2[0][0]*1.1, limit2, limit3)
    
    # ルートuで回せばプラスが出る場合
    if ratio_u > 0 and value_u > limit0:
        count += 1
        print(-1)
        root = "u"
        ratio, value = ratio_u, value_u
        time.sleep(maxtime) # ここにかわりに注文のコードを書いて取引
    
    # ルートdで回せばプラスが出る場合
    elif ratio_d > 0 and value_d > limit0:
        count += 1
        print(1)
        root = "d"
        ratio, value = ratio_d, value_d
        time.sleep(maxtime) # ここにかわりに注文のコードを書いて取引

    # 
    else:
        if count != 0:
            # 歪みが解消されたとき, どんな歪みだったかを表示
            # (利益を出せたルート(u/d), 歪みの長さ（連続して板に歪みがあった回数）, 期待利益率, 量(ALT単位))
            l.log("{} {} {} {}".format(root, count, ratio, value))
        count = 0
        time.sleep(1)
