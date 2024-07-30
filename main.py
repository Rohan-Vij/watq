import time
from machine import Pin, ADC
import network
import socket
import json
from temp_sensor import DS18X20
from onewire import OneWire

import config

# --- NETWORKING SETUP ---

wifi_SSID = config.SSID
wifi_pass = config.PASS

sta_if = network.WLAN(network.STA_IF)
ap_if = network.WLAN(network.AP_IF)

print(f"Access point available?: {ap_if.active()}")
print(f"Station (WiFi connectivity) available?: {sta_if.active()}\n")

if (not sta_if.active()):
    print("Turning on WiFi station connectivity... ", end="")
    sta_if.active(True)
    print("successfully turned on\n")

print("Connecting to WiFi network with:")
print("\tSSID:", wifi_SSID)

if wifi_pass != "":
    print("\tPassword:", wifi_pass)
else:
    print("\tPassword: passwordless network")
print()

i = 1
while not sta_if.isconnected():
    try:
        if wifi_pass != "":
            sta_if.connect(wifi_SSID, wifi_pass)
        else:
            sta_if.connect(wifi_SSID, "")
    except OSError as e:
        print("OSError/Wifi conn error, trying again...")

    print(f"Connecting to network... (Attempt {i})")
    time.sleep(3)
    i += 1

def http_get(url):
    _, _, host, path = url.split('/', 3)
    addr = socket.getaddrinfo(host, 80)[0][-1]
    s = socket.socket()
    s.connect(addr)
    s.send(bytes('GET /%s HTTP/1.0\r\nHost: %s\r\n\r\n' % (path, host), 'utf8'))

    response = b"" # opening buffer and reading until empty
    while True:
        chunk = s.recv(4096)
        if len(chunk) == 0:
            break
        response = response + chunk;
    s.close()

    return response.decode('ascii').split("\r\n\r\n")[-1]

# print(http_get("https://api.ipify.org/?format=json"))
print("Public IP:", json.loads(http_get("https://api.ipify.org/?format=json"))['ip'])

for i in range(10):
    print(f"Starting sensor reading in {10-i} seconds")
    time.sleep(1)

# --- SENSOR DATA ---

#DS18B20 data line connected to pin P10
temp_ow = OneWire(Pin(23))
temp = DS18X20(temp_ow)
roms = temp.scan()

# Turbidity
turb = ADC(Pin(36)) # max (clear) 4095
#turb.atten(ADC.ATTN_11DB)

temp.convert_temp()
while True:
    time.sleep(1)
    for rom in roms:
        print(f"Temperature (*F): {temp.read_temp(rom) * (9/5) + 32}")

    print(f"Turbidity: {turb.read()}")

    print()
    temp.convert_temp()