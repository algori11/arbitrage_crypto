import configparser

def read(filename):
    global CRYPTO_BASE, CRYPTO_ALT
    global NAME1, APIKEY1, SECKEY1
    global NAME2, APIKEY2, SECKEY2
    global PASSWORDS
    global threshold_up, threshold_down
    global SLACK_FLAG, SLACK_URL    
    global LINE_FLAG, LINE_TOKEN
    global FILE_LOG, FILE_NAME
    global BNBBUY, BIXBUY

    inifile = configparser.ConfigParser()
    inifile.read(filename, 'UTF-8')

    CRYPTO_BASE = inifile.get('settings', "BASE")
    CRYPTO_ALT = inifile.get('settings', "ALT")

    NAME1 = inifile.get('EXCHANGE1', "NAME")
    APIKEY1 = inifile.get('EXCHANGE1', "APIKEY")
    SECKEY1 = inifile.get('EXCHANGE1', "SECRET")
    PASSWORDS = {}
    try:
        PASSWORDS[NAME1] = inifile.get('EXCHANGE1', "PASS")
    except:
        pass

    NAME2 = inifile.get('EXCHANGE2', "NAME")
    APIKEY2 = inifile.get('EXCHANGE2', "APIKEY")
    SECKEY2 = inifile.get('EXCHANGE2', "SECRET")
    try:
        PASSWORDS[NAME2] = inifile.get('EXCHANGE2', "PASS")
    except Exception as e:
        print(e)
        pass

    threshold_up = float(inifile.get('settings', "threshold_up"))
    threshold_down = float(inifile.get('settings', "threshold_down"))
    BNBBUY = int(inifile.get('TOKENS', "BNBBUY"))
    BIXBUY = int(inifile.get('TOKENS', "BIXBUY"))

    SLACK_FLAG = int(inifile.get('SLACK', "FLAG"))
    SLACK_URL = inifile.get('SLACK', "URL")

    LINE_FLAG = int(inifile.get('LINE', "FLAG"))
    LINE_TOKEN = inifile.get('LINE', "TOKEN")

    FILE_LOG = int(inifile.get('FILE_LOGGING', "FLAG"))
    FILE_NAME = inifile.get('FILE_LOGGING', "NAME")
