import requests
import json
import numpy as np
import time

class exchange(object):
    
    def __init__(self, exchange1, exchange2, logger, bnbbuy=False):
        self.t1 = exchange1
        self.t2 = exchange2
        self.dscrsize = max(self.t1.tsize(), self.t2.tsize())
        self.bnbbuy = bnbbuy
        self.logger = logger
        
        print("ticksize:"+str(self.dscrsize))
    
    # APIで認証できてるか調べる（認証できてたらbalanceを返す）
    def check_api_state(self):
        try:
            t1_base, t1_alt = self.t1.balance()
        except Exception as e:
            print(self.t1.name, "API login error")
            raise
        try:
            t2_base, t2_alt = self.t2.balance()
        except Exception as e:
            print(self.t2.name, "API login error")
            raise
        print("authentication success")
        return t1_base, t1_alt, t2_base, t2_alt
    
    # 両取引所の残高を取得
    def balances(self):
        sflag = 0
        while sflag == 0:
            try:
                t1_base, t1_alt = self.t1.balance()
                t2_base, t2_alt = self.t2.balance()

                sflag = 1
            except (requests.ConnectTimeout, requests.ReadTimeout, json.JSONDecodeError, KeyError):
                time.sleep(1)
                
            if self.bnbbuy == 1:
                self.bnbcheck()

        return t1_base, t1_alt, t2_base, t2_alt

    # Binance(t2)でペア通貨を買い、HitBTC(t1)で売る
    def order_up(self, ch_val, chrate, bflag):

        order2 = self.t2.order("buy",self.discr(self.discr(ch_val)*(1.+chrate*bflag)))
        self.errormsg(order2)

        order1 = self.t1.order("sell",self.discr(ch_val))
        self.errormsg(order1)

    # Binance(t2)でペア通貨を売り、HitBTC(t1)で買う
    def order_down(self, ch_val, chrate, bflag):

        order2 = self.t2.order("sell",self.discr(ch_val))
        self.errormsg(order2)

        order1 = self.t1.order("buy",self.discr(self.discr(ch_val)*(1.+chrate*bflag)))
        self.errormsg(order1)


    # 注文量の離散化
    def discr(self, amount):
        return int(amount/self.dscrsize) * self.dscrsize


    # 現在の状態を表示
    def status(self, t1_base, t1_alt, t2_base, t2_alt, ch_val, tradeflag):
        self.msgprint("{} [{:.6f}, {}] ch:{}".format(time.asctime()[4:-5], 
                                                                                 t1_base+t2_base, self.discr(t1_alt+t2_alt), self.discr(tradeflag*ch_val)))

    # メッセージの表示（SNSに投稿）
    def msgprint(self, msg):
        self.logger.log(msg)
        
    # 注文が通らなかったときのエラーメッセージを表示（それぞれの取引所のエラー時のレスポンスを利用）
    def errormsg(self, input_order):

        if "msg" in input_order.keys(): # for Binance
            self.msgprint("Binance order error:"+json.dumps(input_order))
            raise

        if "error" in input_order.keys(): # for HitBTC
            self.msgprint("HitBTC order error:"+json.dumps(input_order))
            raise

            
    # 取引可能なバランスのup, downの向きの割合と総量を返す
    def return_ratio(self, val_down, val_up):
        val_total = val_down + val_up
        if val_total < self.dscrsize*12.:
            self.msgprint("total balance is too small")
            raise
        balance_ratio = val_up/(val_up+val_down)
        return balance_ratio, val_down + val_up

    
    # BNB（手数料用）が少なかったら買う
    def bnbcheck(self, bnb_amount=1.):
        b_bnb = self.t2.balancebnb()
        if b_bnb < bnb_amount:
            orderb = self.t2.order("buy", bnb_amount, symbol="BNBBTC")
            self.errormsg(orderb)
            self.msgprint("bought" + str(bnb_amount) + "BNB")
        else:
            pass
        
        
    # 板を監視して、指定した閾値以上での取引の可否と取引可能な量、そのときの通貨のask値を取得
    # tradeflagが1だったらt2で買ってt1で売る取引(order_up)
    # tradeflagが-1だったらt1で買ってt2で売る取引(order_down)
    # がそれぞれ利益を出す
    def rate_c(self, thrd_up, thrd_down):
        sflag = 0
        while sflag == 0:
            try:
                depth1 = self.t1.orderbook()
                depth2 = self.t2.orderbook()

                cum_down1 = np.array([np.cumsum(depth1["ask"][:, 1]), np.zeros(20)])
                cum_down2 = np.array([np.cumsum(depth2["bid"][:, 1]), np.ones(20)])
                cum_down = np.hstack((cum_down1, cum_down2))
                sorder_down = cum_down[1][np.argsort(cum_down[0])][:20]

                cum_up1 = np.array([np.cumsum(depth1["bid"][:, 1]), np.ones(20)])
                cum_up2 = np.array([np.cumsum(depth2["ask"][:, 1]), np.zeros(20)])
                cum_up = np.hstack((cum_up1, cum_up2))
                sorder_up = cum_up[1][np.argsort(cum_up[0])][:20]

                i1, i2 = 0, 0
                ratelist_up = np.zeros((20,2))
                for si in range(20):
                    so = sorder_up[si]
                    if so == 0:
                        ratelist_up[si] = depth1["bid"][i1][0]/depth2["ask"][i2][0], cum_up2[0][i2]
                        i2 +=1
                    if so == 1:
                        ratelist_up[si] = depth1["bid"][i1][0]/depth2["ask"][i2][0], cum_up1[0][i1]
                        i1 +=1

                i1, i2= 0, 0
                ratelist_down = np.zeros((20,2))
                for si in range(20):
                    so = sorder_down[si]
                    if so == 0:
                        ratelist_down[si] = depth2["bid"][i2][0]/depth1["ask"][i1][0], cum_down1[0][i1]
                        i1 +=1
                    if so == 1:
                        ratelist_down[si] = depth2["bid"][i2][0]/depth1["ask"][i1][0], cum_down2[0][i2]
                        i2 +=1
                u_idx = np.sum(ratelist_up[:, 0] >= thrd_up)
                d_idx = np.sum(ratelist_down[:, 0] >= thrd_down)

                tradeflag = np.sign(u_idx) - np.sign(d_idx)

                if tradeflag == 0:
                    tradable_value = 0
                if tradeflag == 1:
                    tradable_value = ratelist_up[u_idx -1][1]
                if tradeflag == -1:
                    tradable_value = ratelist_down[d_idx -1][1]
                sflag = 1
            except (requests.ConnectTimeout, requests.ReadTimeout, json.JSONDecodeError, KeyError):
                time.sleep(1)

        return tradeflag, tradable_value, depth1["ask"][0][0], depth2["ask"][0][0]
        




