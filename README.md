
# PyJRD100

A Python wrapper for JRD100 UHF RFID module.




## Intro

* A python script for interfacing JRD100 module in python.
* Constructs and sends commands  
* Reads the transmitted data and processes the frames to extract relevant information.
* A surface level arduino sketch allows for communication between user and module.


## Usage
* connect ESP32 DEVKITV1(any mcu can be used) with JRD100 as follow
    * VCC-3V3 (VCC of MCU)
    * GND-GND
    * RX - GPIO 17 
    * TX - GPIO 16
    * NOTE: The RX and TX pins of the module can be connected to any TX and RX pin of  secondary serial bus of the MCU respectively.
* Upload sketch to the MCU
* Run the python script and use it as needed.


