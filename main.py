import time
from machine import Pin, ADC
import network
import socket
import json
from temp_sensor import DS18X20
from onewire import OneWire
import config

class WiFiConnection:
    def __init__(self, ssid, password):
        self.ssid = ssid
        self.password = password
        self.sta_if = network.WLAN(network.STA_IF)
        self.ap_if = network.WLAN(network.AP_IF)

    def connect(self):
        print(f"Access point available?: {self.ap_if.active()}")
        print(f"Station (WiFi connectivity) available?: {self.sta_if.active()}\n")

        if not self.sta_if.active():
            print("Turning on WiFi station connectivity... ", end="")
            self.sta_if.active(True)
            print("successfully turned on\n")

        print("Connecting to WiFi network with:")
        print("\tSSID:", self.ssid)

        if self.password:
            print("\tPassword:", self.password)
        else:
            print("\tPassword: passwordless network")
        print()

        i = 1
        while not self.sta_if.isconnected():
            try:
                self.sta_if.connect(self.ssid, self.password)
            except OSError as e:
                print("OSError/Wifi connection error, trying again...")

            print(f"Connecting to network... (Attempt {i})")
            time.sleep(3)
            i += 1

        print("Connected to WiFi\n")

    def get_public_ip(self):
        response = self.http_get("https://api.ipify.org/?format=json")
        ip = json.loads(response)['ip']
        print(f"Public IP: {ip}\n")
        return ip

    @staticmethod
    def http_get(url):
        _, _, host, path = url.split('/', 3)
        addr = socket.getaddrinfo(host, 80)[0][-1]
        s = socket.socket()
        s.connect(addr)
        s.send(bytes(f'GET /{path} HTTP/1.0\r\nHost: {host}\r\n\r\n', 'utf8'))

        response = b""
        while True:
            chunk = s.recv(4096)
            if len(chunk) == 0:
                break
            response += chunk
        s.close()

        return response.decode('ascii').split("\r\n\r\n")[-1]

class Sensor():
    def read(self):
        pass

class TemperatureSensor(Sensor):
    def __init__(self, pin):
        self.temp_sensor = DS18X20(OneWire(Pin(pin)))
        self.roms = self.temp_sensor.scan()

    def read(self):
        self.temp_sensor.convert_temp()
        time.sleep(1)
        temperatures = []
        for rom in self.roms:
            temp_f = self.temp_sensor.read_temp(rom) * (9/5) + 32 # C to F
            temperatures.append(temp_f)
        return temperatures

class TurbiditySensor(Sensor):
    def __init__(self, pin):
        self.turbidity_sensor = ADC(Pin(pin))
        # self.turbidity_sensor.atten(ADC.ATTN_11DB)  # Uncomment if needed

    def read(self):
        return self.turbidity_sensor.read()

def main():
    wifi = WiFiConnection(config.SSID, config.PASS)
    wifi.connect()
    wifi.get_public_ip()

    temp_sensor = TemperatureSensor(pin=23)
    turb_sensor = TurbiditySensor(pin=36)

    for i in range(10):
        print(f"Starting sensor reading in {10-i} seconds")
        time.sleep(1)

    while True:
        temperatures = temp_sensor.read()
        turbidity = turb_sensor.read()
        
        for temp in temperatures:
            print(f"Temperature (*F): {temp}")
        print(f"Turbidity: {turbidity}")
        print()
        
        time.sleep(1)

if __name__ == "__main__":
    main()
