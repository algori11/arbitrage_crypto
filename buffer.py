"""
取引所ごとに発生する問題を解決するためのモジュール
取引所のインスタンスを生成した直後にbuffer.buffer()の中に放り込んで適当な修飾を加える
"""

# スイッチ
def buffer(ts, passwords):
    if ts.name == "binance":
        return buff_binance(ts)
    if ts.name == "hitbtc2":
        return buff_hitbtc2(ts)
    if ts.name == "bitz":
        return buff_bitz(ts, passwords)
    if ts.name == "yobit":
        return buff_yobit(ts)
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

def buff_bitz(ts, passwords):
    # 取引パスワードを追加
    try:
        ts.password = passwords["bitz"]
        return ts
    except:
        print("Please fill PASS in config.ini")
        raise

def buff_yobit(ts):
    # nonceを1秒よりはやい頻度で更新するよう再定義（未検証）
    ts.nonce = lambda :ccxt.Exchange.milliseconds()%1000000000
    return ts




