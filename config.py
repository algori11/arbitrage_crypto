import configparser

def read(filename):
    global CRYPTO_BASE, CRYPTO_ALT
    global BINA_APIKEY, BINA_SECKEY, BINA_BNBBUY
    global HITB_APIKEY, HITB_SECKEY
    global threshold_up, threshold_down
    global SLACK_FLAG, SLACK_URL
    global FILE_LOG, FILE_NAME

    inifile = configparser.ConfigParser()
    inifile.read(filename, 'UTF-8')

    CRYPTO_BASE = inifile.get('settings', "BASE")
    CRYPTO_ALT = inifile.get('settings', "ALT")
    
    BINA_APIKEY = inifile.get('BINANCE', "APIKEY")
    BINA_SECKEY = inifile.get('BINANCE', "SECRET")
    BINA_BNBBUY = int(inifile.get('BINANCE', "BNBBUY"))

    HITB_APIKEY = inifile.get('HitBTC', "APIKEY")
    HITB_SECKEY = inifile.get('HitBTC', "SECRET")

    threshold_up = float(inifile.get('settings', "threshold_up"))
    threshold_down = float(inifile.get('settings', "threshold_down"))

    SLACK_FLAG = int(inifile.get('SLACK', "FLAG"))
    SLACK_URL = inifile.get('SLACK', "URL")

    FILE_LOG = int(inifile.get('FILE_LOGGING', "FLAG"))
    FILE_NAME = inifile.get('FILE_LOGGING', "NAME")