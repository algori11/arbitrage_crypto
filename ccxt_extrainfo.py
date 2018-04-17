# -*- coding: utf-8 -*-
# ccxtにない/API叩いても取得できない情報を直に書いて補完するためのファイル. たとえばBit-zではDASH/BTC取引の最小量が0.005であるが, この情報はAPIを叩いても入手できない. そういうのをここに書いておいて引いてくる予定
class info:
    def minqty(self):
        minqdict = {}
        minqdict["bitz"] = {"DASH/BTC": 0.005}
        minqdict["bitz"] = {"EOS/BTC": 1.0}
        minqdict["bitz"] = {"TRX/BTC": 2050}
        minqdict["bitz"] = {"ETH/BTC": 0.05}
        minqdict["bitz"] = {"LTC/BTC": 0.1}
        minqdict["bitz"] = {"EKT/BTC": 100}
        minqdict["bitz"] = {"ETC/BTC": 0.5}
        minqdict["bitz"] = {"LSK/BTC": 0.2}
        minqdict["bitz"] = {"NULS/BTC": 10}
        minqdict["bitz"] = {"ZEC/BTC": 0.05}
        minqdict["bitz"] = {"MCO/BTC": 0.05}
        minqdict["bitz"] = {"QTUM/BTC": 0.01}
        minqdict["bitz"] = {"TRX/BTC": 2050}
        
        return minqdict
