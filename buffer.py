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
        return ts
    except:
        print("Please fill PASS in config.ini")
        raise

def buff_yobit(ts):
    # nonceを1秒よりはやい頻度で更新するよう再定義（未検証）
    ts.nonce = lambda :ccxt.Exchange.milliseconds()%1000000000
    return ts

def buff_bitflyer(ts, info):
    #今のところ特になし
    pass
    return ts



