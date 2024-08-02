import time
import os
import ujson
import network
from machine import Pin, ADC
import array
import socket
import json
from temp_sensor import DS18X20
from onewire import OneWire
import config
from umqttsimple import MQTTClient

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

class Sensor:
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
            temp_f = self.temp_sensor.read_temp(rom) * (9/5) + 32
            temperatures.append(temp_f)
        return temperatures

class TurbiditySensor(Sensor):
    def __init__(self, pin):
        self.turbidity_sensor = ADC(Pin(pin))
        # self.turbidity_sensor.atten(ADC.ATTN_11DB)  # Uncomment if needed

    def read(self):
        return self.turbidity_sensor.read()

class PhSensor(Sensor):
    def __init__(self, pin):
        self.ph_sensor = ADC(Pin(pin))

    def read(self):
        voltage = self.ph_sensor.read() * (5 / 1023)  # scaling factor
        return self.ph_sensor.read()

class TDSSensor(Sensor):
    def __init__(self, pin):
        self.tds_sensor = ADC(Pin(pin))
    
    def read(self):
        voltage = self.tds_sensor.read()
        return voltage


# class TDSSensor(Sensor):
#     VREF = 3.3  # Reference voltage of the ADC
#     SCOUNT = 30  # Number of samples

#     def __init__(self, pin):
#         self.tds_sensor = ADC(Pin(pin))
#         self.analog_buffer = array.array('i', [0] * self.SCOUNT)
#         self.analog_buffer_index = 0
#         self.temperature = 25  # Default temperature in Celsius

#     def read(self):
#         analog_sample_timepoint = time.ticks_ms()
#         if time.ticks_diff(time.ticks_ms(), analog_sample_timepoint) > 40:  # Every 40 milliseconds
#             analog_sample_timepoint = time.ticks_ms()
#             self.analog_buffer[self.analog_buffer_index] = self.tds_sensor.read()
#             self.analog_buffer_index += 1
#             if self.analog_buffer_index == self.SCOUNT:
#                 self.analog_buffer_index = 0

#         print_timepoint = time.ticks_ms()
#         if time.ticks_diff(time.ticks_ms(), print_timepoint) > 800:  # Every 800 milliseconds
#             print_timepoint = time.ticks_ms()
#             analog_buffer_temp = array.array('i', self.analog_buffer)
#             average_voltage = self.get_median_num(analog_buffer_temp, self.SCOUNT) * (self.VREF / 4095.0)
#             compensation_coefficient = 1.0 + 0.02 * (self.temperature - 25.0)
#             compensation_voltage = average_voltage / compensation_coefficient
#             tds_value = (133.42 * compensation_voltage**3 - 255.86 * compensation_voltage**2 + 857.39 * compensation_voltage) * 0.5
#             # print("TDS Value: {:.0f} ppm".format(tds_value))
#             return tds_value

#     def get_median_num(self, buffer, count):
#         sorted_buffer = sorted(buffer)
#         if count % 2 == 0:
#             median = (sorted_buffer[count // 2 - 1] + sorted_buffer[count // 2]) / 2
#         else:
#             median = sorted_buffer[count // 2]
#         return median
        

class MQTTHandler:
    def __init__(self, client_id, endpoint, key_path, cert_path, thing_name, temp_sensor, turbidity_sensor, ph_sensor, led_pin=2):
        self.client_id = client_id
        self.endpoint = endpoint

        self.key_path = key_path
        self.cert_path = cert_path

        self.thing_name = thing_name
        self.topic_pub = f"$aws/things/{thing_name}/shadow/update"
        self.topic_sub = f"$aws/things/{thing_name}/shadow/update/delta"

        self.led = Pin(led_pin, Pin.OUT)
        self.temp_sensor = temp_sensor
        self.turbidity_sensor = turbidity_sensor
        self.ph_sensor = ph_sensor

        self.info = os.uname()

    def connect(self):
        ssl_params = {
            'key': self.key_path,
            'cert': self.cert_path,
        }
        self.mqtt = MQTTClient(self.client_id, self.endpoint, port=8883, ssl=True, ssl_params=ssl_params)
        print("Connecting to AWS IoT...")
        self.mqtt.connect()
        print("Connected")
        self.mqtt.set_callback(self.mqtt_subscribe)
        self.mqtt.subscribe(self.topic_sub)

    def mqtt_publish(self, message=''):
        print("Publishing message...")
        self.mqtt.publish(self.topic_pub, message)
        print(message)

    def mqtt_subscribe(self, topic, msg):
        print("Message received...")
        message = ujson.loads(msg)
        print(topic, message)
        if 'state' in message and 'led' in message['state']:
            self.led_state(message)
        print("Done")

    def led_state(self, message):
        self.led.value(message['state']['led']['onboard'])

    def run(self):
        while True:
            try:
                self.mqtt.check_msg()
            except:
                print("Unable to check for messages.")

            temperatures = self.temp_sensor.read()
            turbidity = self.turbidity_sensor.read()
            ph = self.ph_sensor.read()
            tds = self.tds_sensor.read()

            mesg = ujson.dumps({
                "state": {
                    "reported": {
                        "device": {
                            "client": self.client_id,
                            "uptime": time.ticks_ms(),
                            "hardware": self.info[0],
                            "firmware": self.info[2]
                        },
                        "sensors": {
                            "temperature": temperatures[0],
                            "turbidity": turbidity,
                            "tds": tds,
                            "ph": ph
                        },
                        "led": {
                            "onboard": self.led.value()
                        }
                    }
                }
            })

            try:
                self.mqtt_publish(message=mesg)
            except:
                print("Unable to publish message.")

            print("Sleep for 10 seconds")
            time.sleep(10)

def main():
    wifi = WiFiConnection(config.SSID, config.PASS)
    wifi.connect()
    wifi.get_public_ip()

    temp_sensor = TemperatureSensor(pin=23)
    turbidity_sensor = TurbiditySensor(pin=36)
    ph_sensor = PhSensor(pin=33)
    tds_sensor = TDSSensor(pin=34)

    while True:
        # print(temp_sensor.read(), turbidity_sensor.read(), ph_sensor.read(), tds_sensor.read())
        print("Temp:", temp_sensor.read()[0])
        print("Turbidity:", turbidity_sensor.read())
        print("PH:", ph_sensor.read())
        print("TDS:", tds_sensor.read())
        print()
        time.sleep(1)

    # mqtt_handler = MQTTHandler(
    #     client_id="WatqClient",
    #     endpoint=config.AWS_ENDPOINT,
    #     key_path="/auth/private.pem.key",
    #     cert_path="/auth/cert.pem.crt",
    #     thing_name="WatqThing",
    #     temp_sensor=temp_sensor,
    #     turbidity_sensor=turbidity_sensor,
    #     ph_sensor=ph_sensor
    # )

    # mqtt_handler.connect()
    # mqtt_handler.run()

if __name__ == "__main__":
    main()
