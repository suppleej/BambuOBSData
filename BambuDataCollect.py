import paho.mqtt.client as mqtt
import json
import os
import math
import datetime
import time
import http.client
import sys
import ssl
from dotenv import load_dotenv

load_dotenv()

bambuIP = str(os.getenv("printerIP"))
bambuSerial = os.getenv("printerSerial")
scenePath = os.getenv("scenePath").replace("\\","/")
printerName = os.getenv("printerName")
printerUser = os.getenv("printerUser")
printerPass = os.getenv("printerPass")
sbConn = os.getenv("SBhost") + ':' + os.getenv("SBPort")
mainScene = os.getenv("mainScene")
brbScene = os.getenv("brbScene")
esai = os.getenv("endStreamActionID")
esan = os.getenv("endStreamActionName")
gsai = os.getenv("getSceneActionID")
gsan = os.getenv("getSceneActionName")
msai = os.getenv("mainSceneActionID")
msan = os.getenv("mainSceneActionName")
bsai = os.getenv("brbSceneActionID")
bsan = os.getenv("brbSceneActionName")
esTimeout = int(os.getenv("endStreamTimeout"))
#dPoints = ['layer_num','total_layer_num','bed_target_temper','bed_temper','chamber_temper','nozzle_target_temper','nozzle_temper','gcode_start_time','mc_percent','mc_remaining_time','spd_lvl','spd_mag','big_fan1_speed','big_fan2_speed','cooling_fan_speed']
dPoints = ['nozzle_temper','mc_percent', 'layer_num']

if scenePath.endswith("/"):
    scenePath = scenePath[:-1]

# setup connection to streamer.bot to control stream
# this requires that the HTTP Server is running in streamer.bot
# for more information on streamer.bot and the server go to
# https://wiki.streamer.bot/en/Servers-Clients/HTTP-Server

headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}



def sbDoAction(id, name):
    payload = {
        "action": {
            "id": id,
            "name": name
        }
    }
#
#    conn = http.client.HTTPConnection(sbConn)
#    conn.request("POST", "/DoAction", json.dumps(payload), headers)
#    res = conn.getresponse()
    # According to the documentation /DoAction only responds with a 204 status code.
    # We will check for a 204 and if anything else is returned we will call it an error
#    if res.status == 204:
#        return "Success: Got a 204 response"
#    else:
#        return f"Error: Got {res.status} response"

def obsGetScene():
    sbDoAction(gsai, gsan)
    time.sleep(0.5)
    with open(scenePath + '/currentScene.txt') as f:
        curScene = f.read()
    os.remove(scenePath + '/currentScene.txt')
    return curScene

def wtfs(dpt, tdata):
    dpath = scenePath + '/' + dpt + '.txt'
    try:
        with open(dpath, "w+") as f:
            f.write(tdata)
    except:
        print("Didn't even get to write")
    return 0
    
def wtfs_log(dpt, tdata):
    dpath = scenePath + '/' + dpt + '.txt'
    try:
        with open(dpath, "a") as f:
            f.write(tdata + ';')
    except:
        print("Didn't even get to write")
    return 0

def rtnt(n):
    rounded = math.floor(n / 10) * 10
    if n - rounded >= 5:
        return rounded + 10
    else:
        return rounded

def on_connect(client, userdata, flags, rc):
    print("Connected to " + printerName + " on IP " + bambuIP + " with result code "+str(rc))
    print("Sending data to " + os.path.abspath(scenePath))
    client.subscribe("device/" + bambuSerial + "/report")

def convert_minutes_to_hr_min(minutes):
    hours = minutes // 60
    minutes = minutes % 60
    return f"Time Remaining: {hours}hr {minutes:02d}min"

def on_message(client, userdata, msg):
    data = json.loads(msg.payload.decode("utf-8").replace("'","\""))
    print(data)    
    
    if "t_utc" not in data:
        wtfs_log("BambuJsonDump", json.dumps(data))
    
    if "print" in data:
            if "nozzle_temper" in data['print']:
                tcdata = str(int(data['print']['nozzle_temper']))
                wtfs('nozzle_temper', 'Nozzle temp: ' + tcdata + 'c')

            elif "mc_percent" in data['print']:
                tdata = str(data['print']['mc_percent']) + '%'
                wtfs('mc_percent', tdata + ' Complete')
                    
            elif "layer_num" in data['print']:
                wtfs('layer_num', 'Layer: ' + str(data['print']['layer_num']))
            
            elif "mc_remaining_time" in data['print']:
                wtfs('mc_remaining_time', convert_minutes_to_hr_min(data['print']['mc_remaining_time']))




client = mqtt.Client(userdata={"data": None})
client.tls_set(tls_version=ssl.PROTOCOL_TLS, ciphers=None, cert_reqs=ssl.CERT_NONE)
client.tls_insecure_set(True)
client.auto_reconnect = True
client.username_pw_set(printerUser, printerPass)
client.on_connect = on_connect
client.on_message = on_message
client.connect(bambuIP, port=8883, keepalive=60)
try:
    client.loop_forever()
except KeyboardInterrupt:
    print("Exiting due to keyboard interrupt.")
    client.disconnect()
