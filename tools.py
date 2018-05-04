# -*- coding: utf-8 -*-
import requests
import json
import numpy as np
import time
import ccxt
import sys
import queue
import threading
import socket
import traceback
import ccxt_extrainfo
from pandas import DataFrame as df
from ccxt.base.errors import RequestTimeout

"""
通貨ペアや取引パスワード、トークンの使用／不使用などの情報をまとめただけのクラス
"""
class information(object):
    def __init__(self, base, alt, passwords, bnbbuy=False, bixbuy=False):

        self.base = base
        self.alt = alt
        self.symbol = alt + "/"  + base
        self.bnbbuy = bnbbuy
        self.bixbuy = bixbuy
        self.passwords = passwords
    
"""
取引にかかわる関数を詰め込んだクラス
"""
class exchange(object):
    
    def __init__(self, exchange1, exchange2, info, logger):
        self.t1 = exchange1
        self.t2 = exchange2
        self.tquery = [self.t1, self.t2]

        self.base = info.base
        self.alt = info.alt
        self.symbol = info.symbol
        self.bnbbuy = info.bnbbuy
        self.bixbuy = info.bixbuy
        
        # 取引最小値の取得
        self.minsize = max(self.minq(self.t1), self.minq(self.t2))
        
        # 取引最小値の情報がどちらの取引所にもなかった場合、一旦ストップ
        if self.minsize == 0:
            print("error: No info about minimum order quantity")
            raise
        else:
            # 表示桁数を最小取引量から適当に決定
            self.digits = max(int(-np.log10(self.minsize)), 0) + 1
            
        # market_buy/sellが可能なリスト（暫定, 可能ならここにccxtコードを追記）
        # 取引所の売買およびccxtで成行注文（market_buyとsell）が実装されていないところがあるため、
        # そういう場合は「askの1.01倍のbuy」および「bidの0.99倍のsell」を出すことで擬似的に成行注文を成立させています。
        # 使っている取引所が対応している場合はこのリストに追加しておけばより動作が安定します。
        self.market_order = ["binance", "hitbtc2"]
        
        # amountの離散化サイズを粗いほうで上書き
        # 取引の際、基本的にccxtが自動的に取引量の離散化を行うが、離散化サイズが二つの取引所で異なると管理がめんどくさいので、粗いほうで統一する
        try:
            amount_precision = min(self.t1.markets[self.symbol]["precision"]["amount"], self.t2.markets[self.symbol]["precision"]["amount"])
            self.t1.markets[self.symbol]["precision"]["amount"] = amount_precision
            self.t2.markets[self.symbol]["precision"]["amount"] = amount_precision
        except:
            print("Caution: amount precision is not defined")
        
        # 表示のフォーマットを決定
        self.display = "{} [{:.6f}, {:."+str(self.digits)+"f}] ch:{:."+str(self.digits)+"f}"
        
        self.logger = logger
        
        # 取引の基本情報
        # 通貨ペア・取引所ペア・最小取引量を表示する
        print(self.symbol)
        print(self.t1.name + "/" + self.t2.name)
        print("minsize:"+str(self.minsize))
        
        # API経由で残高の取得が可能かチェック
        self.check_api_state()
        
        # timeoutの値を変更
        self.t1.timeout=2000
        self.t2.timeout=2000

        # BNB/BIX自動購入フラグがオンのとき、どの取引所がbinance/biboxか判断（self.tbinance/tbiboxをbinance/biboxの方に対応させる）
        # たぶんもっとスッキリ書ける
        if info.bnbbuy == 1:
            if self.t1.name == "binance":
                self.tbinance = self.t1
            elif self.t2.name == "binance":
                self.tbinance = self.t2
            else:
                print("binance is not selected")
                raise
        if info.bixbuy == 1:
            if self.t1.name == "bibox":
                self.tbibox = self.t1
            elif self.t2.name == "bibox":
                self.tbibox = self.t2
            else:
                print("bibox is not selected")
                raise

    
    # APIで認証できてるか調べる関数（認証できてたらbalanceを返す）
    # return: [取引所1の基軸通貨の残高, 取引所1のペア通貨の残高, 取引所2の基軸通貨の残高, 取引所2のペア通貨の残高]
    def check_api_state(self):
        try:
            t1_base, t1_alt = self.balance(self.t1)
        except Exception as e:
            print(self.t1.name, "API authentication error")
            raise
        try:
            t2_base, t2_alt = self.balance(self.t2)
        except Exception as e:
            print(self.t2.name, "API authentication error")
            raise
        print("authentication success (balance)")
        return t1_base, t1_alt, t2_base, t2_alt

    # 取引最小単位を取得（＆通貨ペアが存在するかチェック）
    # return: 取引最小量(float)
    def minq(self, ts):
        try:
            minsize = ts.markets[self.symbol]["limits"]["amount"]["min"]
        # 取得した取引所情報（ts.markets）が持ってなかったらccxt_extrainfo.py(ユーザーが書く)を参照
        # buffer.pyに統合するかも
        except KeyError:
            try:
                minsize = ccxt_extrainfo.info().minqty()[ts.name][self.symbol]
            except:
                # minsizeが得られなかった場合、警告つきでいちおう動く（この場合、取引時に取引所からエラーが帰ってくる可能性あり）
                # この警告が出たら手動での最小取引量の確認（&ccxt_extrainfo.pyに追記）を推奨
                print("Caution: No information about minimum order quantity limit in " + ts.name)
                print("→ check ccxt_extrainfo or currency pair")
                minsize = 0

        return np.float(minsize)
    
    # 残高取得のwrapper
    def balance(self, ts):
        bal = ts.fetch_balance()
        return np.float(bal["free"][self.base]), np.float(bal["free"][self.alt])

    # 両取引所の残高を取得
    # return: [取引所1の基軸通貨の残高, 取引所1のペア通貨の残高, 取引所2の基軸通貨の残高, 取引所2のペア通貨の残高]
    def balances(self):
        sflag = 0
        while sflag == 0:
            try:
                # 残高を取得
                t1_base, t1_alt = self.balance(self.t1)
                t2_base, t2_alt = self.balance(self.t2)
                
                # TOKEN自動補充フラグがオンのとき、TOKENの残高もチェック
                if self.bnbbuy == 1:
                    self.tbinance_bnb = self.bnbcheck()
                if self.bixbuy == 1:
                    self.tbibox_bix = self.bixcheck()

                sflag = 1
            except (ccxt.NetworkError, RequestTimeout) as e:
                time.sleep(1)
            except:
#                 self.logger.log("{} {}".format(time.asctime()[4:-5], str(sys.exc_info()[0])))
                time.sleep(5)

        return t1_base, t1_alt, t2_base, t2_alt
    
    # 注文時はtimeoutを長めにとる ＆ market_buy/sellできる取引所かどうか（リストmarket_orderを参照）で使うccxtの関数をスイッチ
    # 売り注文
    def sell_order(self, ts, amount, price_sell):
        ts.timeout=10000
        if ts.name in self.market_order:
            order = ts.create_market_sell_order(self.symbol, amount)
        else:
            order = ts.create_limit_sell_order(self.symbol, amount, price_sell)
        ts.timeout=2000
        return order
    
    # 買い注文
    def buy_order(self, ts, amount, price_buy):
        ts.timeout=10000
        if ts.name in self.market_order:
            order = ts.create_market_buy_order(self.symbol, amount)
        else:
            order = ts.create_limit_buy_order(self.symbol, amount, price_buy)
        ts.timeout=2000
        return order
    
    # 売り注文と買い注文をペアにした関数
    # t2でペア通貨を買い、t1で売る
    def order_up(self, ch_val, chrate, bflag, price_sell, price_buy):
        
        # ------ここから並列処理での売買のための記述------
        # orderの情報を格納する配列
        response = [[],[]]
        
        # 並列処理で二つの注文を行うための関数
        def thread_worker(thread_queue):
            thread = thread_queue.get()
            try:
                if thread == 0:
                    response[thread] = self.sell_order(self.t1, ch_val, price_sell)
                if thread == 1:
                    response[thread] = self.buy_order(self.t2, ch_val*(1.+chrate*bflag), price_buy)
            except Exception:
                print("order error: " + str(traceback.format_exc()))
                response[thread]=False

            thread_queue.task_done()

        # queueを設定
        thread_queue = queue.Queue()
        for q in [0, 1]:
            thread_queue.put(q)

        # Thread start
        while not thread_queue.empty():
            w_thread = threading.Thread(target=thread_worker, args=(thread_queue,))
            w_thread.start()
            
        # threadがおわって揃うのを待つ    
        thread_queue.join()
        
        # エラーを吐いたのがないかチェック
        # 売買の場合、エラーが出たら即停止する
        if response[0] == False or response[1] == False:
            print("Order Error:", response)
            self.logger.log(str(sys.exc_info()[0]))
            raise
            
        # ------------ここまで------------
        order1, order2 = response
        return order1, order2



    
    # t2でペア通貨を売り、t1で買う
    def order_down(self, ch_val, chrate, bflag, price_sell, price_buy):
        
        # ------ここから並列処理での売買のための記述------
        # orderの情報を格納する配列
        response = [[],[]]
        
        # 並列処理で二つの注文を行うための関数
        def thread_worker(thread_queue):
            thread = thread_queue.get()
            try:
                if thread == 0:
                    response[thread] = self.buy_order(self.t1, ch_val*(1.+chrate*bflag), price_buy)
                if thread == 1:
                    response[thread] = self.sell_order(self.t2, ch_val, price_sell)
            except Exception:
                print("order error: " + str(traceback.format_exc()))
                response[thread]=False

            thread_queue.task_done()

        # queueを設定
        thread_queue = queue.Queue()
        for q in [0, 1]:
            thread_queue.put(q)

        # Thread start
        while not thread_queue.empty():
            w_thread = threading.Thread(target=thread_worker, args=(thread_queue,))
            w_thread.start()
            
        # threadがおわって揃うのを待つ    
        thread_queue.join()
        
        # エラーを吐いたのがないかチェック
        # 売買の場合、エラーが出たら即停止する
        if response[0] == False or response[1] == False:
            print("Order Error:", response)
            self.logger.log(str(sys.exc_info()[0]))
            raise
            
        # ------------ここまで------------
        order1, order2 = response
        return order1, order2


    # 現在の状態を表示
    # 表示するもの: 時間, 基軸通貨の残高（両取引所の合計）, ペア通貨の残高（両取引所の合計）, 取引した量（符号はup/downの向き）
    def status(self, t1_base, t1_alt, t2_base, t2_alt, ch_val, tradeflag):
        msg = self.display.format(time.asctime()[4:-5],
                                  t1_base+t2_base, t1_alt+t2_alt,
                                  tradeflag*ch_val)
        self.msgprint(msg)
    
    # 状態表示（詳細版）　上に追加で best ask と best bid も出力
    def status_detail(self, t1_base, t1_alt, t2_base, t2_alt, ch_val, tradeflag, t1_ask, t2_ask, t1_bid, t2_bid):
        msg = self.display.format(time.asctime()[4:-5],
                                  t1_base+t2_base, t1_alt+t2_alt,
                                  tradeflag*ch_val)
        if tradeflag == 0:
            ask = t1_ask
            bid = t1_bid
        if tradeflag == 1:
            ask = t2_ask
            bid = t1_bid
        if tradeflag == -1:
            ask = t1_ask
            bid = t2_bid

        msg += " ask:{:.4f} bid:{:.4f}".format(ask, bid)
        
        self.msgprint(msg)
        
    # メッセージの表示（SNSに投稿）
    # TOKEN自動売買フラグがたってるときにTOKEN残高の情報を追加してロガーに投げる
    def msgprint(self, msg):
        if self.bnbbuy == 1:
            msg = msg + " BNB:{:.4f}".format(self.tbinance_bnb)
        if self.bixbuy == 1:
            msg = msg + " BIX:{:.4f}".format(self.tbibox_bix)

        self.logger.log(msg)
     
    # orderbookのwrapper
    def orderbook(self, ts):
        book = ts.fetch_order_book(symbol=self.symbol, limit=20)
        return {"asks": np.array(book["asks"][:20], dtype=np.float), "bids": np.array(book["bids"][:20], dtype=np.float)}
    
    # 裁定機会と量を検出する関数
    """
    input: 取引所Aのask板, 取引所Bのbid板, 取引の可否を判断する閾値
    output: 
        chanceflag: Aで買ってBで売ったら閾値を超えた利益が発生するとき1, そうでないとき0をかえす
        value: chanceflagが1のとき、閾値をこえている通貨の概算量（ペア通貨単位）をかえす
    """
    def chance_detect(self, asks, bids, threshold):
        ai, bi = 0, 0
        asksum, bidsum = np.array(asks), np.array(bids)
        asksum[:, 1],  bidsum[:, 1] = np.cumsum(asks[:,1]), np.cumsum(bids[:,1])

        if bidsum[bi][0]/asksum[ai][0] > threshold:
            for i in range(20):
                if bidsum[bi][0]/asksum[ai][0] > threshold:
                    minflag = np.argmin([asksum[ai][1], bidsum[bi][1]])
                    if minflag == 0: ai += 1
                    else: bi += 1
                else:
                    if minflag == 0: ai -= 1
                    else: bi -= 1
                    break
            chanceflag = 1
            value = np.min([asksum[ai][1], bidsum[bi][1]])
        else:
            chanceflag = 0
            value = 0

        return chanceflag, value
    """
    板を監視して、指定した閾値以上での取引の可否と取引可能な量、そのときの通貨のask値を取得
    出力のtradeflagが1だったらt2で買ってt1で売る取引(order_up)
    出力のtradeflagが-1だったらt1で買ってt2で売る取引(order_down) がそれぞれ利益を出す
    input: upの閾値, downの閾値
    output: 
        tradeflag: 取引所1のほうが高くて閾値超え→1, 取引所2のほうが高くて閾値超え→-1, 閾値をこえない→0 をかえす
        tradable_value: 閾値をこえた量（ペア通貨単位）がいくらかをかえす
        あとはそれぞれの取引所のbest ask, best bid をかえす
    """
    def rate_c(self, thrd_up, thrd_down):
        sflag = 0
        while sflag == 0:
            try:
                # 板の取得
                # ------ここから並列処理での板取得のための記述------
                response = {}

                def query_worker(query_queue):
                    query = query_queue.get()
                    try:
                        # コメントアウトでBinanceの応答が早すぎるのをちょっと調整
                        #if query.name == "binance": time.sleep(0.05)
                        
                        response[query.name]=self.orderbook(query)
                    except (ccxt.NetworkError, RequestTimeout) as e:
                        response[query.name]=0
                    except:
#                         self.logger.log("{} {}".format(time.asctime()[4:-5], str(sys.exc_info()[0])))
                        response[query.name]=0

                    query_queue.task_done()

                # queueを設定
                query_queue = queue.Queue()
                for q in self.tquery:
                    query_queue.put(q)

                # Thread start
                while not query_queue.empty():
                    w_thread = threading.Thread(target=query_worker, args=(query_queue,))
                    w_thread.start()
                query_queue.join()
                
                # 板取得はエラーが出たらやりなおし
                if response[self.t1.name] == 0 or response[self.t2.name] == 0:
                    time.sleep(1)
                    continue
                # ------------ここまで------------
                
                # 取引所1の板, 取引所2の板
                # 辞書型, depth1["asks"]などでそれぞれのaskとbidを取得可能
                depth1 = response[self.t1.name]
                depth2 = response[self.t2.name]
                
                #裁定機会の計算
                u_chance, u_value = self.chance_detect(depth2["asks"], depth1["bids"], thrd_up)
                d_chance, d_value = self.chance_detect(depth1["asks"], depth2["bids"], thrd_down)
                
                # upとdownのどちらが利益を出すか（あるいはどちらもそうでないか）を1,0,-1でかえす
                tradeflag = u_chance - d_chance
                
                # 異常な板（askよりbidのほうが高い）をはじく
                if (depth1["asks"][0][0] < depth1["bids"][0][0]) or (depth2["asks"][0][0] < depth2["bids"][0][0]):
                    tradeflag = 0
                    
                # 利益を出せる量がいくらかを適用
                if tradeflag == 0: tradable_value = 0
                if tradeflag == 1: tradable_value = u_value
                if tradeflag == -1: tradable_value = d_value
                sflag = 1
            
            # ここの例外はおそらく発生しない
            # あとでチェック
            except (ccxt.NetworkError, RequestTimeout):
                time.sleep(1)
            except:
#                 self.logger.log("{} {}".format(time.asctime()[4:-5], str(sys.exc_info()[0])))
                time.sleep(5)

        return tradeflag, tradable_value, depth1["asks"][0][0], depth2["asks"][0][0], depth1["bids"][0][0], depth2["bids"][0][0]
        

    # TOKEN対応
    
    # BNB/BIX残高取得
    def balancebnb(self):
        sflag = 0
        while sflag == 0:
            try:
                bal = self.tbinance.fetch_balance()
                sflag = 1
            except (ccxt.NetworkError, RequestTimeout):
                time.sleep(1)
            except:
#                 self.logger.log("{} {}".format(time.asctime()[4:-5], str(sys.exc_info()[0])))
                time.sleep(5)

        return np.float(bal["free"]["BNB"])

    def balancebix(self):
        sflag = 0
        while sflag == 0:
            try:
                bal = self.tbibox.fetch_balance()
                sflag = 1
            except (ccxt.NetworkError, RequestTimeout):
                time.sleep(1)
            except:
#                 self.logger.log("{} {}".format(time.asctime()[4:-5], str(sys.exc_info()[0])))
                time.sleep(5)

        return np.float(bal["free"]["BIX"])
    
     # BNB/BIX（手数料用）が少なかったら買う
    def bnbcheck(self, bnb_amount=1.):
        b_bnb = self.balancebnb()
        if b_bnb < bnb_amount:
            self.tbinance.timeout=10000
            orderb = self.tbinance.create_market_buy_order("BNB/BTC", bnb_amount)
            self.tbinance.timeout=2000
            self.logger.log("bought {}BNB".format(bnb_amount))
            time.sleep(3)
            b_bnb = self.balancebnb()
        return b_bnb

    def bixcheck(self, bix_amount=10.):
        b_bix = self.balancebix()
        if b_bix < bix_amount:
            bixprice = self.tbibox.fetch_order_book("BIX/BTC")["asks"][10][0]
            self.tbibox.timeout=10000
            orderb = self.tbibox.create_limit_buy_order("BIX/BTC", bix_amount, bixprice)
            self.tbibox.timeout=2000
            self.logger.log("bought {}BIX".format(bix_amount))
            time.sleep(3)
            b_bix = self.balancebix()
        return b_bix


