from subprocess import check_output
from requests import Session
from json import loads
from time import time as ttime, sleep
from hashlib import md5

USER = ""
PSW  = ""

BASE_URL = "https://api.staticnetcontent.com"
WG_PORT  = 443
reqSess  = Session()
#reqSess.verify = False
reqSess.headers.update({"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "okhttp/4.9.3"})

def genWireKey():
    privKey = check_output("wg genkey").decode().strip()
    pubKey  = check_output("wg pubkey", input=privKey.encode()).decode().strip()
    return privKey, pubKey

def genClAuth():
    time = int(ttime())
    hash = md5("952b4412f002315aa50751032fcaab03{}".format(time).encode()).hexdigest()
    return time, hash

def Login(user, psw):
    time, hash = genClAuth()
    data = {
        "platform": "android",
        "app_version": "3.1.887",
        "client_auth_hash": hash,
        "session_type_id": "4",
        "time": time,
        "username": user,
        "password": psw
    }
    reqLogin  = reqSess.post("{}/Session".format(BASE_URL), data=data)
    LoginData = loads(reqLogin.text)['data']
    return LoginData['session_auth_hash'], LoginData['is_premium']

def getServers(isPremium):
    Servers = []
    time, hash = genClAuth()
    reqServers = reqSess.get("https://assets.staticnetcontent.com/serverlist/mob-v2/{}/{}".format(isPremium, hash))
    jsonServers = loads(reqServers.text)['data']
    for server in jsonServers:
        country = {'name': server['short_name'], 'city': []}
        for loc in server['groups']:
            hosts = []
            try:
                nodes = loc['nodes']
            except KeyError:
                continue
            for node in nodes:
                hosts.append(node['hostname'])
            country['city'].append({'name': '{}-{}'.format(loc['city'], loc['nick']), "pubkey": loc['wg_pubkey'], 'host': hosts})
        if not country['city'] == []:
            Servers.append(country)
    return Servers

def getPSK(accHash, pubKey):
    time, hash = genClAuth()
    data = {
        "platform": "android",
        "app_version": "3.1.887",
        "client_auth_hash": hash,
        "session_auth_hash": accHash,
        "session_type_id": "4",
        "time": time,
        "wg_pubkey": pubKey
    }
    reqPSK = reqSess.post("{}/WgConfigs/init".format(BASE_URL), data=data)
    PSKData = loads(reqPSK.text)['data']
    return PSKData['config']['PresharedKey']

def getWireIP(accHash, pubKey, HostName):
    time, hash = genClAuth()
    data = {
        "platform": "android",
        "app_version": "3.1.887",
        "client_auth_hash": hash,
        "session_auth_hash": accHash,
        "session_type_id": "4",
        "time": time,
        "wg_pubkey": pubKey,
        "hostname": HostName
    }
    reqIP = reqSess.post("{}/WgConfigs/connect".format(BASE_URL), data=data)
    IPData = loads(reqIP.text)['data']['config']
    return IPData['Address'], IPData['DNS']


accHash, isPremium = Login(USER, PSW)

servers = getServers(isPremium)


i = 0
num = len(servers)
privKey, pubKey = genWireKey()
psk = getPSK(accHash, pubKey)
for server in servers:
    for city in server['city']:
        ip, dns = getWireIP(accHash, pubKey, city['host'][0])
        wgConfig = """[Interface]
PrivateKey = {privkey}
Address = {ip}
DNS = {dns}

[Peer]
PublicKey = {pubkey}
PresharedKey = {psk}
AllowedIPs = 0.0.0.0/0
Endpoint = {host}:{port}""".format(privkey=privKey, ip=ip, dns=dns, pubkey=city['pubkey'], psk=psk, host=city['host'][0], port=WG_PORT)

        with open("./config/{}-{}.conf".format(server['name'], city['name']), "w") as conf:
            conf.write(wgConfig)
        sleep(1)
    i += 1
    print(f"\r{i}/{num}", flush=True, end="")
        
