#!/usr/bin/python3

import RPi.GPIO as GPIO
import time

class LCD20x4:

    LINE_OFFSETS = [0x00, 0x40, 0x14, 0x54]
    LINE_WIDTH = 20
    LINE_NUMBER = 4
    CMD_CLEAR_DISPLAY = 0x01
    CMD_DISPLAY_OFF = 0x08
    CMD_DISPLAY_ON = 0x0C
    CMD_SET_CURSOR_POSITION = 0x80

    def __init__(self, pin_rs=22, pin_e=27, pins_data=[25, 24, 23, 18], pin_numbering=GPIO.BCM):
        self.data_length = len(pins_data)
        if self.data_length not in [4, 8]:
            raise ValueError('Invalid number of data bits')

        self.pin_mapping = {'RS':pin_rs, 'E':pin_e, 'DATA':pins_data[-1::-1]}
        self.function_set = (1 << 5) | (self.data_length == 8 << 4) | (1 << 3)

        GPIO.setmode(pin_numbering)
        GPIO.setup([self.pin_mapping['RS'], self.pin_mapping['E']] + self.pin_mapping['DATA'], GPIO.OUT)

        if self.data_length == 4:
            self._cmd(0x33, delay = 0.0041)
            self._cmd(0x32, delay = 0.00001)
            self._cmd(self.function_set, delay = 0.015)
        else:
            for _ in range(3):
                self._cmd(self.function_set, delay = 0.015)

        self.display_off()
        self.clear_display()
        self.display_on()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        GPIO.cleanup([self.pin_mapping['RS'], self.pin_mapping['E']] + self.pin_mapping['DATA'])

    def _cmd(self, data, char_mode=False, delay=0):
        GPIO.output((self.pin_mapping['RS'], self.pin_mapping['E']), (char_mode, GPIO.LOW))
        for n in range(8 // self.data_length):
            i = 0
            pin_data = []
            while i < self.data_length:
                bit_shift = (7 - (i + (self.data_length * n)))
                pin_data.append(GPIO.HIGH if (data & (1 << bit_shift)) else GPIO.LOW)
                i += 1
            GPIO.output(self.pin_mapping['DATA'], pin_data)
            for _ in range(2):
                GPIO.output(self.pin_mapping['E'], not GPIO.input(self.pin_mapping['E']))
            time.sleep(delay)

    def clear_display(self):
        self._cmd(LCD20x4.CMD_CLEAR_DISPLAY, delay = 0.015)
        self.set_cursor_position(1, 1)

    def display_off(self):
        self._cmd(LCD20x4.CMD_DISPLAY_OFF)

    def display_on(self):
        self._cmd(LCD20x4.CMD_DISPLAY_ON)

    def set_cursor_position(self, line, column):
        if 0 <= line < LCD20x4.LINE_NUMBER and 0 <= column < LCD20x4.LINE_WIDTH:
            self._cursor_position = [line, column]
            self._cmd(LCD20x4.CMD_SET_CURSOR_POSITION + LCD20x4.LINE_OFFSETS[line] + column)
        else:
            raise ValueError('Invalid line or column position')

    def get_cursor_position(self):
        return tuple(self._cursor_position)

    def write_line(self, line, column, text):
        self.set_cursor_position(line, column)
        for char in text[:(LCD20x4.LINE_WIDTH - column)]:
            self.write_char(char)

    def clear_line(self, line, column=1):
        if 0 <= line < LCD20x4.LINE_NUMBER and 0 <= column < LCD20x4.LINE_WIDTH:
            self.write_line(line, column, ' ' * (LCD20x4.LINE_WIDTH - column))

    def write_char(self, char):
        self._cmd(ord(char), True)
