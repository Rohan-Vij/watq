# Water Quality IoT

### AWS
Make an `/auth` folder with the IoT thing's private key (`pem.key`) and device certificate (`pem.crt`).

### Sensors
1. DS18x20 Temperature Sensor - [Driver](https://github.com/robert-hh/Onewire_DS18X20)
2. KS0414 Keyestudio Turbidity Sensor - [Driver](https://wiki.keyestudio.com/KS0414_Keyestudio_Turbidity_Sensor_V1.0)

### Notes
1. Make sure MicroPython is flashed on the ESP32
2. Install ampy and esptools (pip libs)
3. Run `ampy --port COM6 put main.py` when pushing a file for the first time or `ampy --port COM6 -d 5 put main.py` when reflashing the same file

