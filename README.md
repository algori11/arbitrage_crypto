# arbitrage_crypto
仮想通貨のアービトラージアルゴリズム

### 概要
こちらに紹介しているものです.<br>
[pythonで仮想通貨の取引所間アービトラージ](http://algorisamurai.hateblo.jp/entry/2018/03/09/172019)<br>
（ブログの記述と食い違う場合、このREADMEが最新版なのでこちらを参照してください.）<br>

仮想通貨取引所を二つ用意して入金し, アルゴリズムを走らせることで, 二つの取引所に価格差が生じた機会を自動的に見つけて取引し, 利益を生み出します. 現物取引のみに対応しています.<br>

python3で開発しています.（たぶんpython2でも動きます）.<br><br>
パッケージとして<br>
* pandas（データ処理）<br>
* numpy（数値処理）<br>
* requests（HTTPライブラリ）<br>
* docopt（コマンドライン引数処理）<br>
* ccxt（仮想通貨取引所のAPIをまとめたライブラリ）<br>

を用いているので, pipでinstallしてください.<br><br>

### コードの実行
後述のconfig.iniを記入して, 各取引所に同額程度の基軸通貨とペアにした通貨を入金し, <br>
> python arb.py

とすることで, 自動的に取引を行います.<br>

また,<br>
> python arb.py demo

とするとデモモードで起動し, 取引は行わずに取引所間の裁定機会を見つけるたびに表示します.<br>

両方のモードともに, コードを実行するとはじめに<br>
> Trade mode # Trade と Demo のどちらのモードか<br>
> BTC/DASH # アービトラージに用いる通貨ペアは何か<br>
> binance/hitbtc2 # アービトラージに用いる取引所はどこか<br>
> minsize:0.001 # 取引の最小値はいくらか<br>

というようなテキストが出力されます.<br><br>

### Trade mode
Trade modeでは,<br>
> authentication success # APIは正しく認証されているか確認<br>

のメッセージが出た後, <br>
> Mar 30 00:20:58 [0.103475, 1.4030] ch:0.000 BNB:1.1487

のように現在の状況を示す出力が表示され, 待機状態に入って裁定の機会を窺います.<br>

裁定機会が来たとき, 裁定取引を行えるBalanceを持っているなら直ちに取引を実行し, 取引後のBalanceを出力します.<br>

平常運転時の出力は次のようなものになります.<br>
> Mar 30 00:28:38 [0.103477, 1.4030] ch:-0.0210 BNB:1.1484<br>
> Mar 30 00:28:43 [0.103477, 1.4030] ch:-0.0040 BNB:1.1483<br>
> Mar 30 00:28:47 [0.103477, 1.4030] ch:-0.0010 BNB:1.1483<br>
> Mar 30 03:45:34 [0.103490, 1.4050] ch:1.3320 BNB:1.1275<br>
> Mar 30 03:46:47 [0.103529, 1.4060] ch:-1.0670 BNB:1.1108<br>

これらの出力は左から<br>
* Mar 30 03:46:47 ：日時<br>
* [0.103529, 1.4060] ：[基軸通貨, ペアにした通貨]の残高（両取引所の合計）<br>
* ch:-1.0670 ：取引した量（取引所1で売って2で買う場合 ＋, 取引所2で売って1で買う場合 -の符号がつく）<br>
* BNB:1.1108 ：取引手数料に使う取引所トークンの残高（optional, 後述のBNBBUYフラグをONにした場合）<br>
を表しています.<br><br>

##### ここまででエラーが出た場合
> authentication success

のテキストが出ず何らかのエラーで止まった場合, config.iniや取引所でのAPIのアクセス許可に問題がある可能性があります. （ccxtがそれぞれの取引所に対して十分整備されていないせいで発生するエラーがも多いため, そうしたエラーが出た場合は報告していただけると助かります）.<br>

特殊なエラーの例としては, Biboxという取引所ではそれぞれの仮想通貨について, balanceを一度0でない状態にして口座をactivateしないと残高が取得できない, といった仕様がありました. (この場合, アービトラージに用いる通貨を事前に手で少しだけ購入しておけばOKです.)<br><br>

### Demo mode
Demo modeでは, <br>
> Demo mode start <br>

のメッセージの後, 裁定機会が観測されるたび, 仮にその機会に取引できたときの利益を表示します.<br>
表示する内容は, 左から, 時間, 取引できる量（取引所1で売って2で買う場合 ＋, 取引所2で売って1で買う場合 -の符号がつく）, 取引を行ったときの倍率, となっています（倍率については, best bid / ask を使っているため, 評価は甘め.）<br>

本番を実行する前にその取引所/通貨ペアにどの程度の鞘があるか見積もるのに使ってください.<br><br>

### config.ini の構成と見方
configファイルに, 取引する通貨の組み合わせや取引所, 取引を行う価格差の条件などを記入します.<br><br>

##### [setting]
> [settings]<br>
> BASE = BTC<br>
> ALT = XRP<br>
> threshold_up = 1.0025<br>
> threshold_down = 1.0025<br>

BASEとALTによってアービトラージを行う通貨のペアを指定します.この例では, Bitcoin(BTC)とRipple(XRP)が指定されています. BASEにはその取引所で基軸通貨と扱われている通貨を, ALTにはその通貨で購入する形になっている通貨を指定してください. 大抵の場合, BASEとしてはBTCやETH, JPY, USDTなどが指定されることになるかと思います. また, この通貨ペアは後で指定する二つの取引所の両方で取り扱われている必要があります.<br>

threshold_upとthreshold_downでは, 取引を行う乖離の条件を設定します. <br>
threshold_up = 1.003 と指定すると「取引所1の方が取引所2より1.003倍以上高くなったら, 取引所1で売って取引所2で売る」ように,<br>
threshold_down = 1.004 と指定すると「取引所2の方が取引所1より1.004倍以上高くなったら, 取引所2で売って取引所1で売る」ように設定したことになります.<br>

ここで, up と down を別々に設定するのは, 取引所ごとに高くなりやすい傾向や安くなりやすい傾向がある場合があるからです.<br>
手数料以下の値を設定しても損するだけなので, 基本的には手数料の倍率より高いものを指定することをおすすめします.<br><br>

##### [TOKENS]
> [TOKENS]<br>
> BNBBUY = 1<br>
> BIXBUY = 0<br>

Binanceという取引所では, BNBという取引所の独自トークンで手数料を支払うと手数料が割引される（半額になる）ため, このトークンを自動的に購入する機能を実装しています.<br>
BNBBUYを1にすると, 所持BNBが1BNB以下になったとき1BNBの自動購入が行われます. Binanceを用いない場合, またBinanceでBNBを自動購入しない場合はBNBBUY=0を指定してください. BiboxでのBIXについても同様にしています.<br>

Binanceを使用しないのにBNBBUY = 1を指定したり, Biboxを使用しないのにBIXBUY = 1を指定するとアルゴリズムが止まるので注意してください.<br><br>

##### [EXCHANGE1]と[EXCHANGE2]
> [EXCHANGE1]<br>
> NAME = binance<br>
> APIKEY = dummy_foobarfoobarfoobarfoobarfoobarfoobarfoobarfoobarfoobar<br>
> SECRET = dummy_abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyz<br>

> [EXCHANGE2]<br>
> NAME = hitbtc2<br>
> APIKEY = dummy_foobarfoobarfoobarfoobarfoo<br>
> SECRET = dummy_abcdefghijklmnopqrstuvwxyz<br>

取引に用いる取引所を指定します. また, このプログラムで取引所にアクセスできるように, APIキーとSECRETキーを各取引所のWebサイトで取得し, ここに記入します. APIキーの取得時, 情報閲覧の許可やTradeの許可を設定するのを忘れないようにしてください. このとき, セキュリティ上, APIからはWithdrawalできないよう設定することをお勧めします.


取引所名はccxtの内部コードの<br>
> _1broker, _1btcxe, acx, allcoin, anxpro, bibox, binance, bit2c, bitbay, bitcoincoid, bitfinex, bitfinex2, bitflyer, bithumb, bitlish, bitmarket, bitmex, bitso, bitstamp, bitstamp1, bittrex, bitz, bl3p, bleutrade, braziliex, btcbox, btcchina, btcexchange, btcmarkets, btctradeim, btctradeua, btcturk, btcx, bxinth, ccex, cex, chbtc, chilebit, cobinhood, coincheck, coinegg, coinexchange, coinfloor, coingi, coinmarketcap, coinmate, coinsecure, coinspot, coolcoin, cryptopia, dsx, exmo, flowbtc, foxbit, fybse, fybsg, gatecoin, gateio, gdax, gemini, getbtc, hitbtc, hitbtc2, huobi, huobicny, huobipro, independentreserve, itbit, jubi, kraken, kucoin, kuna, lakebtc, liqui, livecoin, luno, lykke, mercado, mixcoins, nova, okcoincny, okcoinusd, okex, paymium, poloniex, qryptos, quadrigacx, quoinex, southxchange, surbitcoin, therock, tidex, urdubit, vaultoro, vbtc, virwox, wex, xbtce, yobit, yunbi, zaif, zb<br>

の中にある文字列からを指定してください. 大手の取引所は大抵この中にあるかと思います.<br>

手数料が安い取引所については以下の記事を参考にしてください.<br>
[アービトラージに適した仮想通貨取引所（取引手数料0.1%以下）](http://algorisamurai.hateblo.jp/entry/2018/04/12/151313)<br>
（HitBTCを用いる場合, バージョンアップしたAPIであるhitbtc2を指定するようにしてください.）<br><br>

### ログ機能
configの[SLACK][LINE][FILE_LOGGING]のそれぞれのFLAGを1にしてURLやトークン、ファイル名を入力することで, <br>
* [SLACK] SLACKの Incoming Webhooks に投稿<br>
* [LINE] LINE Notify に投稿<br>
* [FILE_LOGGING] 指定したファイル名のファイルに保存<br>

という形でログを出力することができます.<br><br>

### 各取引所への適応
ccxtは完全には整備されていないところがあり, このアルゴリズムもそれぞれの取引所に完全に適応しているわけではないので, 選んだ取引所に応じて様々なエラーが発生すると予想されます. とりあえずBinanceとHitBTCでは正常動作することを確認しています. また, Bit-zとBibox, Zaifについては残高取得ができるところまでは確認しています.<br>

ほか, こんなエラーが出たよ, という報告や, その対策など投げていただけると嬉しく思います.<br><br>

### Triangular Arbitrage
実験段階ですが, 三点アービトラージ（同じ取引所内で三通貨をぐるぐる交換して利益を出すやつ）の機会を検出するコードを/tri_arb以下に置いています。簡単な解説をブログに書いています.<br>
[pythonで三点アービトラージ](http://algorisamurai.hateblo.jp/entry/2018/04/19/200307)<br>

### アドレス

儲かったら投げ銭していただけると光栄です.<br>

Rippleアドレス：<br>
rNvTpTCNZvaFFoBEj2Ba3PA28Pz22Mzzrv<br>

BTCアドレス：<br>
1P1Y1JTkPWhExsxJbgibEvRsBPj5RN8hqk<br>

