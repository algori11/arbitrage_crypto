import configparser

def read(filename):
    global CRYPTO_BASE1 ,CRYPTO_BASE2, CRYPTO_ALT
    global NAME1, APIKEY1, SECKEY1
    global threshold
    global SLACK_FLAG, SLACK_URL    
    global LINE_FLAG, LINE_TOKEN
    global FILE_LOG, FILE_NAME

    inifile = configparser.ConfigParser()
    inifile.read(filename, 'UTF-8')

    CRYPTO_BASE1 = inifile.get('settings', "BASE1")
    CRYPTO_BASE2 = inifile.get('settings', "BASE2")
    CRYPTO_ALT = inifile.get('settings', "ALT")

    NAME1 = inifile.get('EXCHANGE1', "NAME")
    APIKEY1 = inifile.get('EXCHANGE1', "APIKEY")
    SECKEY1 = inifile.get('EXCHANGE1', "SECRET")

    threshold = float(inifile.get('settings', "threshold"))

    SLACK_FLAG = int(inifile.get('SLACK', "FLAG"))
    SLACK_URL = inifile.get('SLACK', "URL")

    LINE_FLAG = int(inifile.get('LINE', "FLAG"))
    LINE_TOKEN = inifile.get('LINE', "TOKEN")

    FILE_LOG = int(inifile.get('FILE_LOGGING', "FLAG"))
    FILE_NAME = inifile.get('FILE_LOGGING', "NAME")