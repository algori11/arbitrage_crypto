# -*- coding: utf-8 -*-
# ccxtにない/API叩いても取得できない情報を直に書いて補完するためのファイル. たとえばBit-zではDASH/BTC取引の最小量が0.005であるが, この情報はAPIを叩いても入手できない. そういうのをここに書いておいて引いてくる予定
class info:
    def minqty(self):
        minqdict = {}
        minqdict["bitz"] = {
        "DASH/BTC": 0.01, "EOS/BTC": 1.0, "TRX/BTC": 2050, "ETH/BTC": 0.05,
        "LTC/BTC": 0.1, "EKT/BTC": 100, "ETC/BTC": 0.5, "LSK/BTC": 0.2, "NULS/BTC": 10,
        "ZEC/BTC": 0.05, "MCO/BTC": 0.05, "QTUM/BTC": 0.01, "TRX/BTC": 2050}
        
        return minqdict
