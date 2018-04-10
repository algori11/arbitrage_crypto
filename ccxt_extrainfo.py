# -*- coding: utf-8 -*-
# ccxtにない/API叩いても取得できない情報を直に書いて補完するためのファイル. たとえばBit-zではDASH/BTC取引の最小量が0.005であるが, この情報はAPIを叩いても入手できない. そういうのをここに書いておいて引いてくる予定
class info:
    def minqty(self):
        minqdict = {}
        minqdict["bitz"] = {"DASH/BTC": 0.005}
        return minqdict
