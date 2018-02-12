#!/usr/bin/python3
"""
Library for Raspberry Pi interfacing with the Serial EEPROM 24xx08x
from Microchip Technology.
"""

__all__ = ["E24xx08x"]

import time
import smbus
from collections import Iterable

class E24xx08x:
    """
    Class for the 24AA08A / 24LC08B chips.
    """
    MAX_BYTES = 16

    def __init__(self, bus, address):
        self.address = address
        self._bus = smbus.SMBus(bus)

    def __str__(self):
        return '<Device class {0} with address {1}>'.format(self.__class__, self.address)

    def _set_current_address(self, addr):
        """
        Sets the address counter to the value of address.
        """
        if not addr in range(0, E24xx08x.MAX_BYTES):
            raise ValueError
        hi, lo = divmod(addr, 1 << 8)
        self._bus.write_byte_data(self.address, hi, lo)

    def write_byte_data(self, addr, value):
        """
        Writes a byte or an array of bytes starting at address into the EEPROM.
        """
        data = []
        if not isinstance(value, Iterable):
            data.append(value)
        else:
            data += value
        hi, lo = divmod(addr, 1 << 8)
        data.insert(0, lo)
        self._bus.write_i2c_block_data(self.address, hi, data)
        time.sleep(0.005)

    def read_byte_data(self, addr):
        """
        Reads a byte at the memory location specified by addr.
        """
        if not addr in range(E24xx08x.MAX_BYTES):
            raise ValueError('Invalid address!')
        self._set_current_address(addr)
        return self._bus.read_byte(self.address)

    value = property(read_byte_data, write_byte_data)

