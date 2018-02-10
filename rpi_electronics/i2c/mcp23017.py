# -*- coding: utf-8 -*-
#!/usr/bin/python3

import time
from collections import Iterable

class MCP23017:
    """
    Class for the MCP23017 I/O port expander.
    """
    REG_BASE_ADDR = {'IODIR': 0x00, 'IPOL': 0x02, 'GPINTEN': 0x04, 'DEFVAL': 0x06, 'INTCON': 0x08, 'IOCON': 0x0A,
                        'GPPU': 0x0C, 'INTF': 0x0E, 'INTCAP': 0x10, 'GPIO':0x12, 'OLAT': 0x14}

    OUT = 0
    IN = 1
    LOW = 0
    HIGH = 1
    PUD_DOWN = 0
    PUD_UP = 1

    class RegisterValueError(ValueError):
        def __init__(self, value=''):
            self._message = value
        @property
        def message(self):
            return self._message

        @message.setter
        def message(self, value):
            self._message = value

        def __str__(self):
            return self.message


    def __init__(self, bus, address):
        self.bus = bus
        self.address = address
        self._register_values = dict()

        # Leave ICON.BANK = 0 but set ICON.SEQOP = 1
        self.bus.write_byte_data(self.address, MCP23017.REG_BASE_ADDR['IOCON'], 1 << 5)
        # Read all register values
        for key in MCP23017.REG_BASE_ADDR.keys():
            self._register_values[key] = self.bus.read_word_data(self.address, MCP23017.REG_BASE_ADDR[key])

    def __enter__(self):
        return self

    def __exit__(self, *pargs, **kwargs):
        pass

    def setmode(self, *pargs, **kwargs):
        pass

    def setwarnings(self, value):
        pass

    @staticmethod
    def set_bit_in_word(word, bit, value):
        """
        Static helper method to set a bit in a word.
        """
        if 0 <= bit <= 15 and value in (0, 1):
            if value:
                word |= (1 << bit)
            else:
                word &= ~(1 << bit)
            return word
        else:
            raise MCP23017.RegisterValueError

    def _write_register_word(self, key, bits, values):
        """
        Helper method to manipulate the instance register values.
        Works for both for a single bit as well as for a list of bits.
        """
        word = self._register_values[key]

        if not isinstance(bits, Iterable):
            word = MCP23017.set_bit_in_word(word, bits, values)
        else:
            number_of_bits = len(bits)
            if not isinstance(values, Iterable):
                # if value is a single value we have to create a list a corresponding value list.
                values = [values] * number_of_bits
            else:
                if len(values) != number_of_bits:
                    raise MCP23017.RegisterValueError

            for bit, value in zip(bits, values):
                word = MCP23017.set_bit_in_word(word, bit, value)

        # check if we have a the word differs to the previous one
        high_byte_diff, low_byte_diff = divmod(word ^ self._register_values[key], 256)

        if high_byte_diff and low_byte_diff:
            # both bytes changed so send the complete word
            self.bus.write_word_data(self.address, MCP23017.REG_BASE_ADDR[key], word)
        elif high_byte_diff ^ low_byte_diff:
            # only one byte differs so we have to send only this one
            value_msb, value_lsb = divmod(word, 256)
            offset, value = (0, value_lsb) if low_byte_diff else (1, value_msb)
            self.bus.write_byte_data(self.address, MCP23017.REG_BASE_ADDR[key] + offset, value)
        else:
            # no change so we do not need to set the hardware register value
            pass
        self._register_values[key] = word

    def setup(self, pins, directions, initial=None, pull_up_down=None):
        """
        Configures a pin or a list of pins either as output or as input.
        """
        try:
            self._write_register_word('IODIR', pins, directions)
            if pull_up_down is not None:
                raise NotImplementedError
            if initial is not None:
                raise NotImplementedError
        except MCP23017.RegisterValueError as e:
            e.message = 'Invalid pin(s) or direction value(s)...'
            raise

    def output(self, pins, states):
        """
        Sets the logic output level of the pin or a list of pins.
        Valid values for the output state are MCP23017.LOW / 0 / False or MCP23017.HIGH / 1 / True.
        """
        try:
            self._write_register_word('GPIO', pins, states)
        except MCP23017.RegisterValueError as e:
            e.message = 'Invalid pin(s) or state value(s)...'
            raise

    def input(self, pin):
        """
        Reads the logic level of the pin.
        """
        self._register_values['GPIO'] = self.bus.read_word_data(self.address, MCP23017.REG_BASE_ADDR['GPIO'])
        return MCP23017.HIGH if ((self._register_values['GPIO'] >> pin)) & 1 else MCP23017.LOW

    def gpio_function(self, pin):
        """
        Returns whether the pin is configured as input or as output.
        """
        self._register_values['IODIR'] = self.bus.read_word_data(self.address, MCP23017.REG_BASE_ADDR['IODIR'])
        return MCP23017.IN if ((self._register_values['IODIR'] >> pin)) & 1 else MCP23017.OUT

    def cleanup(self):
        pass


class LCD20x4:
    """
    Simple class for a character lcd connected via the MCP23017 I/O Expander.
    """

    LINE_OFFSETS = [0x00, 0x40, 0x14, 0x54]
    LINE_WIDTH = 20
    LINE_NUMBER = 4

    CMD_CLEAR_DISPLAY = 0x01
    CMD_RETURN_HOME = 0x02

    CMD_SET_ENTRY_MODE = 0x04
    ENTRY_LEFT = 0x02

    CMD_DISPLAY_CONTROL = 0x08
    CURSOR_ON = 0x02
    CURSOR_OFF = 0x00
    DISPLAY_ON = 0x04
    DISPLAY_OFF = 0x00

    # Flags for the function set instruction
    CMD_FUNCTION_SET = 0x20
    EIGHT_BIT_MODE = 0x10
    FOUR_BIT_MODE = 0x00
    ONE_LINE = 0x00
    TWO_LINES = 0x08

    CMD_SET_DDRAM_ADDRESS = 0x80

    def __init__(self, bus, address, rs, en, data, rw=None):
        self._pins = {}
        self._pins['RS'] = rs
        self._pins['E'] = en
        self._bit_mode = len(data)
        if self._bit_mode not in (4, 8):
            raise ValueError('Invalid number of data pins...')
        self._pins['DATA']= data
        self._pins['RW'] = rw

        # Initialize the GPIO expander
        self.mcp23017 = MCP23017(bus, address)
        # Setup all pins as outputs
        for pin in (rs, en, *data):
            self.mcp23017.setup(pin, MCP23017.OUT)
            self.mcp23017.output(pin, MCP23017.LOW)
        if rw is not None:
            self.mcp23017.setup(rw, MCP23017.OUT)
            # for now we use the pin only for write actions!
            self.mcp23017.output(rw, MCP23017.LOW)

        function_set = LCD20x4.CMD_FUNCTION_SET |\
                                   (LCD20x4.FOUR_BIT_MODE if self._bit_mode == 4 else LCD20x4.EIGHT_BIT_MODE) |\
                                   LCD20x4.TWO_LINES
        entry_mode = LCD20x4.CMD_SET_ENTRY_MODE | LCD20x4.ENTRY_LEFT

        if self._bit_mode == 4:
            self._write(0x33, delay_ms = 4.1)
            self._write(0x32, delay_ms = 0.1)
        else:
            for _ in range(3):
                self._write(function_set, delay_ms = 4.1)
        self._write(function_set)
        self._write(entry_mode)

        self.display_off()
        self.clear_display()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        self.mcp23017.cleanup()

    def _write(self, data, char_mode=False, delay_ms=0):
        """
        Writes the 8-bit value either in character or in command mode.
        """
        self.mcp23017.output([self._pins['RS'], self._pins['E']], [char_mode, MCP23017.LOW])
        data = divmod(data, 16) if self._bit_mode == 4 else (data,)
        for number in data:
            output = []
            i = 0
            while i < self._bit_mode:
                output.append(MCP23017.HIGH if ((number >> i) & 1) else MCP23017.LOW)
                i += 1
            self.mcp23017.output(self._pins['DATA'], output)
            self.mcp23017.output(self._pins['E'], MCP23017.HIGH)
            self.mcp23017.output(self._pins['E'], MCP23017.LOW)
            if delay_ms > 0: time.sleep(delay_ms / 1000.0)


    def clear_display(self):
        """
        Clears the character display.
        """
        self._write(LCD20x4.CMD_CLEAR_DISPLAY)
        self.set_cursor_position(0, 0)

    def display_off(self):
        self._write(LCD20x4.CMD_DISPLAY_CONTROL | LCD20x4.DISPLAY_OFF, delay_ms=0.037)

    def display_on(self):
        self._write(LCD20x4.CMD_DISPLAY_CONTROL | LCD20x4.DISPLAY_ON, delay_ms=0.037)

    def set_cursor_position(self, line, column):
        """
        Sets the cursor to the desired position defined by the line and column number.
        """
        if 0 <= line < LCD20x4.LINE_NUMBER and 0 <= column < LCD20x4.LINE_WIDTH:
            self._write((LCD20x4.CMD_SET_DDRAM_ADDRESS | (LCD20x4.LINE_OFFSETS[line]) + column), delay_ms=0.037)
        else:
            raise ValueError('Invalid line or column position')

    def write_line(self, line, column, text):
        """
        Writes a text to the specified line and starting at the specified column.
        """
        self.set_cursor_position(line, column)
        for char in text[:(LCD20x4.LINE_WIDTH - column)]:
            self.write_char(char)

    def clear_line(self, line, column=0):
        """
        Clears the line beginning from column.
        """
        if 0 <= line < LCD20x4.LINE_NUMBER and 0 <= column < LCD20x4.LINE_WIDTH:
            self.write_line(line, column, ' ' * (LCD20x4.LINE_WIDTH - column))

    def write_char(self, char):
        """
        Writes a character to the current cursor position.
        """
        self._write(ord(char), True)


if __name__ == '__main__':

    import smbus, random

    ADDR = 0x20
    PINS = [13, 14, 15]

    bus = smbus.SMBus(1)
    try:
        mcp23017 = MCP23017(bus, ADDR)
        while True:
            mcp23017.setup(PINS, MCP23017.OUT)
            for n in range(5):
                for i in range(2 ** len(PINS)):
                    data = [MCP23017.HIGH if ((i >> n) & 1) else MCP23017.LOW for n in range(len(PINS))]
                    mcp23017.output(PINS, data)
                    time.sleep(0.1)
            lcd20x4 = LCD20x4(bus, ADDR, rs=10, en=8, data=range(8), rw=9)
            lcd20x4.display_on()
            lcd20x4.write_line(0, 0, 'Lab-Coding.de')
            lcd20x4.write_line(1, 0, '-' * 20)
            lcd20x4.write_line(3, 0, 'dt = ')
            for i in range(0, 1000):
                t0 = time.time()
                lcd20x4.write_line(2, 0, 'Test... {0}'.format(i))
                dt = time.time() - t0
                lcd20x4.write_line(3, 5, '{0:.3f}s'.format(dt))
            lcd20x4.clear_display()
            lcd20x4.display_off()
            time.sleep(2)

    finally:
        bus.close()

