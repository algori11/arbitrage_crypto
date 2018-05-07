"""
取引所ごとに発生する問題を解決するためのモジュール
取引所のインスタンスを生成した直後にbuffer.buffer()の中に放り込んで適当な修飾を加える
"""

# スイッチ
def buffer(ts, info):
    ts.load_markets()
    
    if ts.name == "binance":
        return buff_binance(ts)
    if ts.name == "hitbtc2":
        return buff_hitbtc2(ts)
    if ts.name == "bitz":
        return buff_bitz(ts, info)
    if ts.name == "yobit":
        return buff_yobit(ts)
    if ts.name == "bitflyer":
        return buff_bitflyer(ts, info)
    else:
        return ts

def buff_binance(ts):
    # PC時計とBinanceのサーバー時計のズレが原因でおきるエラーを回避
    ts.options["adjustForTimeDifference"] = True
    return ts

def buff_hitbtc2(ts):
    #今のところ特になし
    pass
    return ts

def buff_bitz(ts, info):
    # 取引パスワードを追加
    try:
        ts.password = info.passwords["bitz"]
    except:
        print("Please fill PASS in config.ini")
        raise
    # 取引通貨ペアの最小取引量の情報（APIで取得できない）を.marketsに追加
    min_dict = {"DASH/BTC": 0.01, "EOS/BTC": 1.0, "TRX/BTC": 1000, "ETH/BTC": 0.05,
        "LTC/BTC": 0.1, "EKT/BTC": 100, "ETC/BTC": 0.5, "LSK/BTC": 0.2, "NULS/BTC": 1.0,
        "ZEC/BTC": 0.05, "MCO/BTC": 0.05, "QTUM/BTC": 0.5, "BCH/BTC": 0.005}
    ts.markets[info.symbol]["limits"] = {"amount":{"min": min_dict[info.symbol]}}
    return ts

def buff_yobit(ts):
    # nonceを1秒よりはやい頻度で更新するよう再定義（未検証）
    ts.nonce = lambda :ccxt.Exchange.milliseconds()%1000000000
    return ts

def buff_bitflyer(ts, info):
    #今のところ特になし
    pass
    return ts



