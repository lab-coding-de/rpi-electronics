# -*- coding: utf-8 -*-
#!/usr/bin/python3

from spidev import SpiDev
import time

class MCP3201():
    def __init__(self):
        self.bus = SpiDev()
        self.bus.open(0, 0)
        self._average = 50

    def close(self):
        self.bus.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    @property
    def average(self):
        return self._average

    @average.setter
    def average(self, value):
        self._average = value

    def get_analog_value(self):
        result = []
        for i in range(self._average):
            adc = self.bus.xfer2([0, 0])
            adc = ((adc[0] & 0x1F) << 7) | (adc[1] >> 1)
            result.append(adc)
        return sum(result) / self._average

    def get_voltage(self, aref):
        return (self.get_analog_value() * aref / 4096)
