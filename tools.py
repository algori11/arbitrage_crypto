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

class information(object):
    def __init__(self, base, alt, passwords, bnbbuy=False, bixbuy=False):

        self.base = base
        self.alt = alt
        self.symbol = alt + "/"  + base
        self.bnbbuy = bnbbuy
        self.bixbuy = bixbuy
        self.passwords = passwords
    

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
        
        self.minsize = max(self.minq(self.t1), self.minq(self.t2))
        if self.minsize == 0:
            print("error: No info about minimum order quantity")
            raise
        else:
            self.digits = max(int(-np.log10(self.minsize)), 0) + 1
            
        # market_buy/sellが可能なリスト（暫定, 可能ならここにccxtコードを追記）
        self.market_order = ["binance", "hitbtc2"]
        
        # amountの量子化サイズを粗いほうで上書き
        try:
            amount_precision = min(self.t1.markets[self.symbol]["precision"]["amount"], self.t2.markets[self.symbol]["precision"]["amount"])
            self.t1.markets[self.symbol]["precision"]["amount"] = amount_precision
            self.t2.markets[self.symbol]["precision"]["amount"] = amount_precision
        except:
            print("Caution: amount precision is not defined")
        
        # 表示する桁数を決定
        self.display = "{} [{:.6f}, {:."+str(self.digits)+"f}] ch:{:."+str(self.digits)+"f}"

        self.logger = logger
        
        print(self.symbol)
        print(self.t1.name + "/" + self.t2.name)
        print("minsize:"+str(self.minsize))

        self.check_api_state()
        self.t1.timeout=2000
        self.t2.timeout=2000

        # BNB/BIX自動購入フラグがオンのとき、どの取引所がbinance/biboxか判断（self.tbinance/tbiboxをbinance/biboxの方に対応させる）
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

    
    # APIで認証できてるか調べる（認証できてたらbalanceを返す）
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
    def minq(self, ts):
        try:
            minsize = ts.markets[self.symbol]["limits"]["amount"]["min"]
        except KeyError:
            try:
                minsize = ccxt_extrainfo.info().minqty()[ts.name][self.symbol]
            except:
                print("Caution: No information about minimum order quantity limit in " + ts.name)
                print("→ check ccxt_extrainfo or currency pair")
                minsize = 0

        return np.float(minsize)
    
    # 残高取得のwrapper
    def balance(self, ts):
        bal = ts.fetch_balance()
        return np.float(bal["free"][self.base]), np.float(bal["free"][self.alt])

    # 両取引所の残高を取得
    def balances(self):
        sflag = 0
        while sflag == 0:
            try:
                t1_base, t1_alt = self.balance(self.t1)
                t2_base, t2_alt = self.balance(self.t2)

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
    
    # 注文時だけtimeoutを長めにとる ＆ market_buy/sellできるか取引所かどうかで使う関数をスイッチ
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
        response = [[],[]]

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
        if response[0] == False or response[1] == False:
            print("Order Error:", response)
            self.logger.log(str(sys.exc_info()[0]))
            raise

        order1, order2 = response
        return order1, order2



    
    # t2でペア通貨を売り、t1で買う
    def order_down(self, ch_val, chrate, bflag, price_sell, price_buy):
        response = [[],[]]

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
        if response[0] == False or response[1] == False:
            print("Order Error:", response)
            self.logger.log(str(sys.exc_info()[0]))
            raise

        order1, order2 = response
        return order1, order2


    # 現在の状態を表示
    def status(self, t1_base, t1_alt, t2_base, t2_alt, ch_val, tradeflag):
        msg = self.display.format(time.asctime()[4:-5],
                                  t1_base+t2_base, t1_alt+t2_alt,
                                  tradeflag*ch_val)
        self.msgprint(msg)
    
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
    
     
    # 板を監視して、指定した閾値以上での取引の可否と取引可能な量、そのときの通貨のask値を取得
    # 出力のtradeflagが1だったらt2で買ってt1で売る取引(order_up)
    # 出力のtradeflagが-1だったらt1で買ってt2で売る取引(order_down) がそれぞれ利益を出す
    def rate_c(self, thrd_up, thrd_down):
        sflag = 0
        while sflag == 0:
            try:
                response = {}

                def query_worker(query_queue):
                    query = query_queue.get()
                    try:
                        response[query.name]=self.orderbook(query)
                    except (ccxt.NetworkError, RequestTimeout) as e:
                        response[query.name]=0
                    except Exception as e:
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

                if response[self.t1.name] == 0 or response[self.t2.name] == 0:
                    time.sleep(1)
                    continue


                depth1 = response[self.t1.name]
                depth2 = response[self.t2.name]

#                depth1 = self.orderbook(self.t1)
#                depth2 = self.orderbook(self.t2)

                n_depth = min(len(depth1["asks"]), len(depth2["asks"]), len(depth1["bids"]), len(depth2["bids"]))
                cum_down1 = np.vstack([np.cumsum(depth1["asks"][:, 1][:n_depth]), np.zeros(n_depth)])
                cum_down2 = np.vstack([np.cumsum(depth2["bids"][:, 1][:n_depth]), np.ones(n_depth)])
                cum_down = np.hstack((cum_down1, cum_down2))
                sorder_down = cum_down[1][np.argsort(cum_down[0])][:n_depth]

                cum_up1 = np.vstack([np.cumsum(depth1["bids"][:, 1][:n_depth]), np.ones(n_depth)])
                cum_up2 = np.vstack([np.cumsum(depth2["asks"][:, 1][:n_depth]), np.zeros(n_depth)])
                cum_up = np.hstack((cum_up1, cum_up2))
                sorder_up = cum_up[1][np.argsort(cum_up[0])][:n_depth]

                i1, i2 = 0, 0
                ratelist_up = np.zeros((n_depth,2))
                for si in range(n_depth):
                    so = sorder_up[si]
                    if so == 0:
                        ratelist_up[si] = depth1["bids"][i1][0]/depth2["asks"][i2][0], cum_up2[0][i2]
                        i2 +=1
                    if so == 1:
                        ratelist_up[si] = depth1["bids"][i1][0]/depth2["asks"][i2][0], cum_up1[0][i1]
                        i1 +=1

                i1, i2= 0, 0
                ratelist_down = np.zeros((n_depth,2))
                for si in range(n_depth):
                    so = sorder_down[si]
                    if so == 0:
                        ratelist_down[si] = depth2["bids"][i2][0]/depth1["asks"][i1][0], cum_down1[0][i1]
                        i1 +=1
                    if so == 1:
                        ratelist_down[si] = depth2["bids"][i2][0]/depth1["asks"][i1][0], cum_down2[0][i2]
                        i2 +=1
                u_idx = np.sum(ratelist_up[:, 0] >= thrd_up)
                d_idx = np.sum(ratelist_down[:, 0] >= thrd_down)

                tradeflag = np.sign(u_idx) - np.sign(d_idx)
                
                if (depth1["asks"][0][0] < depth1["bids"][0][0]) or (depth2["asks"][0][0] < depth2["bids"][0][0]):
                    tradeflag = 0

                if tradeflag == 0:
                    tradable_value = 0
                if tradeflag == 1:
                    tradable_value = ratelist_up[u_idx -1][1]
                if tradeflag == -1:
                    tradable_value = ratelist_down[d_idx -1][1]
                sflag = 1
            except (ccxt.NetworkError, RequestTimeout) as e:
                print(time.asctime()[4:-5], "d1", e)
                time.sleep(1)

            except:
                self.logger.log(str(time.asctime()[4:-5]) + str(sys.exc_info()[0]))
                time.sleep(3)

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

