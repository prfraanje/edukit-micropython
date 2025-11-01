from builtins import int
from micropython import const
from machine import SPI, Pin, freq
from pyb import Timer # this Timer class is more complete than the one in machine
from time import sleep_ms, sleep_us, ticks_us


def binformat(int_value):
    """Convert number to a string with binary value for binary representation of bytes."""
    if 0 <= int_value & int_value < 2**8:
        return f'{int_value:08b}'
    elif 0<= int_value & int_value < 2**16:
        return f'{int_value:016b}'
    elif -ABS_POS_SIGN_BIT_MASK <= int_value < ABS_POS_SIGN_BIT_MASK:
        return f'{int_value:024b}'
    else:
        return f'{int_value:b}'

# # L6474 registers
# L6474_registers = {
#     'ABS_POS'   : {'addr': 0x01, 'signed': True, 'num_bits': 22, 'num_bytes': 3, 'reset': 0x0, 'default': 0x0},
#     'EL_POS'    : {'addr': 0x02, 'signed': False,  'num_bits': 9, 'num_bytes': 2, 'reset': 0x0, 'default': 0x0},
#     'MARK'      : {'addr': 0x03, 'signed': True,  'num_bits': 22, 'num_bytes': 3, 'reset': 0x0, 'default': 0x0},
#     'TVAL'      : {'addr': 0x09, 'signed': False, 'num_bits': 7, 'num_bytes': 1, 'reset': 0x29, 'default': 0x18}, #0x18 = 0.78125 A (0.8 A, 12 V is maximum according to UM2717 guide of STM)
#     'T_FAST'    : {'addr': 0x0E, 'signed': False, 'num_bits': 8, 'num_bytes': 1, 'reset': 0x19, 'default': 0x19},
#     'TON_MIN'   : {'addr': 0x0F, 'signed': False, 'num_bits': 7, 'num_bytes': 1, 'reset': 0x29, 'default': 0x29},
#     'TOFF_MIN'  : {'addr': 0x10, 'signed': False, 'num_bits': 7, 'num_bytes': 1, 'reset': 0x29, 'default': 0x29},
#     'ADC_OUT'   : {'addr': 0x12, 'signed': False, 'num_bits': 5, 'num_bytes': 1, 'reset': '', 'default': ''},
#     'OCD_TH'    : {'addr': 0x13, 'signed': False, 'num_bits': 4, 'num_bytes': 1, 'reset': 0x8, 'default': 0x2}, #0x2 = 1.125 A
#     'STEP_MODE' : {'addr': 0x16, 'signed': False, 'num_bits': 8, 'num_bytes': 1, 'reset': 0x7, 'default': 0xF}, #x0f = 0b00001111, 16 bit microstepping
#     'ALARM_EN'  : {'addr': 0x17, 'signed': False, 'num_bits': 8, 'num_bytes': 1, 'reset': 0xFF, 'default': 0xFF},
#     'CONFIG'    : {'addr': 0x18, 'signed': False, 'num_bits': 16, 'num_bytes': 2, 'reset': 0x2E88, 'default': 0x2E88},
#     'STATUS'    : {'addr': 0x19, 'signed': False, 'num_bits': 16, 'num_bytes': 2, 'reset': '', 'default': ''},
#     }



class L6474():
    """Class for L6474 stepper motor controller."""
    SPI_FREQ          = const(4_000_000)    # 5_000_000 Hz is maximum according to L6474 datasheet
    RESPONSE_DELAY_us = const(1)             # should be at least t_disCS, see Ch 8 in datasheet L6474
    NOP               = const(b'\x00')
    GET_STATUS        = const(b'\xd0')
    ENABLE            = const(b'\xb8')
    DISABLE           = const(b'\xa8')
    GET_PARAM         = const(b'\x20')
    GET_PARAM_int     = const(0x20)
    SET_PARAM         = const(b'\x00')
    SET_PARAM_int     = const(0x00)
    ABS_POS_SIGN_BIT_MASK = const(0x200000)  # =2**21
    ABS_POS_SIGN_TERM     = const(0x400000)

    STATUS = const(b'\x19')

    # from ST manuals UM1857 (IHM01A1) and UM1724 (page 32,44,) (Nucleo-64) documentations
    STBY_RESET_pin = const('D8')  # pin 1 on CN5 = PA9 STM pin, pin 21 on CN10
    PWM_pin        = const('D9')  # pin 2 on CN5 = PC7 STM pin, pin 19 on CN10, TIM3_CH2
    SPI_CS_pin     = const('D10') # pin 3 on CN5 = PB6 STM pin, pin 17 on CN10, SPI1_CS
    SPI_MOSI_pin   = const('D11') # pin 4 on CN5 = PA7 STM pin, pin 15 on CN10, SPI1_MOSI
    SPI_MISO_pin   = const('D12') # pin 5 on CN5 = PA6 STM pin, pin 13 on CN10, SPI1_MISO
    SPI_SCK_pin    = const('D13') # pin 6 on CN5 = PA5 STM pin, pin 11 on CN10, SPI1_SCK
    FLAG_pin       = const('D2')  # pin 3 on CN9 = PA10 STM pin, pin 33 on CN10, -
    DIR_pin        = const('D7')  # pin 8 on CN9 = PA8 STM pin, pin 23 on CN10, -


    def __init__(self):
        self.spi_txdata_abs_pos = const(b'\x21\x00\x00\x00') # immutable
        self.spi_rxdata_abs_pos = bytearray(4)               # mutable
        self.tx = memoryview(self.spi_txdata_abs_pos)
        self.rx = memoryview(self.spi_rxdata_abs_pos)

        # inputs:
        self.flag      = Pin(self.FLAG_pin, Pin.IN, Pin.PULL_UP)

        # outputs:
        self.reset     = Pin(self.STBY_RESET_pin, mode=Pin.OUT, value=1)
        self.cs        = Pin(self.SPI_CS_pin, mode=Pin.OUT, value=1)
        self.direction = Pin(self.DIR_pin, mode=Pin.OUT, value=1)     
        self.tim       = Timer(3,period=200,prescaler=0x1a3) # scales clock to 100 kHz (10 us)
        #pwm_tim = Timer(3,period=200,prescaler=41) # scales clock to 1000 kHz (1 us)
        # if period = 100, then 1 ustep every 100 * 1e-6 s
        # which is 10 usteps / ms
        self.ch = self.tim.channel(2,Timer.OC_TOGGLE,pin=Pin.board.D9)

        self.spi = SPI(1)
        self.spi.init(polarity=1,phase=1,baudrate=self.SPI_FREQ,firstbit=SPI.MSB)

    @micropython.native
    def bytes2int(self,bytes_,signed=False):
        """Convert bytes to integer.""" 
        val = int.from_bytes(bytes_,'big',False)
        if signed and (val & self.ABS_POS_SIGN_BIT_MASK):
            return val-2*self.ABS_POS_SIGN_BIT_MASK
        else:
            return val            

    @micropython.native    
    def int2bytes(self,value,number_of_bytes,signed=False):
        """Convert integer to bytes.""" 
        if signed and (value < 0):
            value += 2*self.ABS_POS_SIGN_BIT_MASK
        return value.to_bytes(number_of_bytes,'big',False)        

    @micropython.native
    def spi_send_receive(self,txdata):
        rxdata = bytearray(len(txdata))
        tx_ = memoryview(txdata)
        rx_ = memoryview(rxdata)
        for i in range(len(txdata)):
            self.cs.value(0)
            self.spi.write_readinto(tx_[i:i+1],rx_[i:i+1]) # seems to work
            self.cs.value(1)
            sleep_us(self.RESPONSE_DELAY_us)
        return rxdata[1:]


    def get_status(self):
        txdata = self.GET_STATUS + b'\x00\x00'
        rxdata = self.spi_send_receive(txdata)
        return self.bytes2int(rxdata)

    def enable(self):
        self.cs.value(0)
        self.spi.write(self.ENABLE)
        self.cs.value(1)
        sleep_us(self.RESPONSE_DELAY_us)

    def disable(self):
        self.cs.value(0)
        self.spi.write(self.DISABLE)
        self.cs.value(1)
        sleep_us(self.RESPONSE_DELAY_us)

    def get_param_address_spec(self,param):
        param = param.upper()
        if param == 'ABS_POS':
            addr_int = 0x01
            num_bytes = 3
            signed = True
        elif param == 'EL_POS':
            addr_int = 0x02
            num_bytes = 2
            signed = False
        elif param == 'MARK':
            addr_int = 0x03
            num_bytes = 3
            signed = True
        elif param == 'TVAL':
            addr_int = 0x09
            num_bytes = 1
            signed = False
        elif param == 'T_FAST':
            addr_int = 0x0E
            num_bytes = 1
            signed = False
        elif param == 'TON_MIN':
            addr_int = 0x0F
            num_bytes = 1
            signed = False
        elif param == 'TOFF_MIN':
            addr_int = 0x10
            num_bytes = 1
            signed = False
        elif param == 'ADC_OUT':
            addr_int = 0x12
            num_bytes = 1
            signed = False
        elif param == 'OCD_TH':
            addr_int = 0x13
            num_bytes = 1
            signed = False
        elif param == 'STEP_MODE':
            addr_int = 0x16
            num_bytes = 1
            signed = False
        elif param == 'ALARM_EN':
            addr_int = 0x17
            num_bytes = 1
            signed = False
        elif param == 'ALARM_EN':
            addr_int = 0x17
            num_bytes = 1
            signed = False
        elif param == 'CONFIG':
            addr_int = 0x18
            num_bytes = 2
            signed = False
        else: # param == 'STATUS':
            addr_int = 0x17
            num_bytes = 2
            signed = False

        return addr_int, num_bytes, signed
    


    def get_param(self,param='ABS_POS'):
        addr_int, num_bytes, signed = self.get_param_address_spec(param)
        txdata = self.int2bytes(self.GET_PARAM_int | addr_int,1) + self.NOP*num_bytes
        rxdata = self.spi_send_receive(txdata)
        return self.bytes2int(rxdata,signed=signed)


    @micropython.native
    def get_abs_pos_efficient(self):
        tx = self.tx
        rx = self.rx
        cs = self.cs
        spi = self.spi
        cs.value(0)
        spi.write_readinto(tx[0:1],rx[0:1])
        cs.value(1)
        sleep_us(1)
        cs.value(0)
        spi.write_readinto(tx[1:2],rx[1:2])
        cs.value(1)
        sleep_us(1)
        cs.value(0)
        spi.write_readinto(tx[2:3],rx[2:3])        
        cs.value(1)
        sleep_us(1)
        cs.value(0)
        spi.write_readinto(tx[3:],rx[3:]) 
        cs.value(1)
        sleep_us(1)

        val = int.from_bytes(self.spi_rxdata_abs_pos[1:],'big',False)
        if val & self.ABS_POS_SIGN_BIT_MASK:
            return val - self.ABS_POS_SIGN_TERM
        else:
            return val

    def set_param(self,param,value):
        addr_int, num_bytes, signed = self.get_param_address_spec(param)
        byte_values = self.int2bytes(value,num_bytes,signed=signed)
        check_value = self.bytes2int(byte_values,signed=signed)
        if check_value != value:
            raise ValueError(f'value ({value}) cannot be properly converted to binary data.')
        txdata = self.int2bytes(self.SET_PARAM_int | addr_int,1) + byte_values
        rxdata = self.spi_send_receive(txdata)
        return self.bytes2int(rxdata,signed=signed)
    

    def set_default(self):
        ret = 0
        ret += self.set_param('ABS_POS',0x0)
        ret += self.set_param('EL_POS',0x0)
        ret += self.set_param('MARK',0x0)
        ret += self.set_param('TVAL',0x18)    
        ret += self.set_param('T_FAST',0x17) # was 0x18
        ret += self.set_param('TON_MIN',0x29)
        ret += self.set_param('TOFF_MIN',0x29)
        #ret += self.set_param('ADC_OUT','')
        ret += self.set_param('OCD_TH',0x2)
        ret += self.set_param('STEP_MODE',0xF)
        ret += self.set_param('ALARM_EN',0xFF)
        ret += self.set_param('CONFIG',0x2E88)
        #ret += self.set_param('ALARM_EN','')    
        return ret


    
    @micropython.native
    def set_period_direction(self,control):
        tim = self.tim
        direction = self.direction
        if control == 0.:
            tim.period(100000)        
            if direction.value() == 0:
                direction.value(1)
            else:
                direction.value(0)
        else:
            if abs(control)<1:
                tim.period(10000)
                if control<0:
                    period = -10000
                else:
                    period = 10000
            else:
                period = round(10000./(control))
                if abs(period) < 1:
                    tim.period(1)
                elif abs(period) < 10000:
                    tim.period(abs(period))
                else:
                    tim.period(10000)
            if period<0:
                direction.value(0)
            else:
                direction.value(1)

#@micropython.native
# def set_default():
#     ret = 0
#     for reg in L6474_registers:
#         value = L6474_registers[reg]['default']
#         if isinstance(value,int):
#             res = set_param(reg,value)
#             #print(f'register {reg} set to {value}, response is {res}')
#             ret += res
#     return ret


                
# L6474_registers = {
#     'ABS_POS'   : {'addr': 0x01, 'signed': True, 'num_bits': 22, 'num_bytes': 3, 'reset': 0x0, 'default': 0x0},
#     'EL_POS'    : {'addr': 0x02, 'signed': False,  'num_bits': 9, 'num_bytes': 2, 'reset': 0x0, 'default': 0x0},
#     'MARK'      : {'addr': 0x03, 'signed': True,  'num_bits': 22, 'num_bytes': 3, 'reset': 0x0, 'default': 0x0},
#     'TVAL'      : {'addr': 0x09, 'signed': False, 'num_bits': 7, 'num_bytes': 1, 'reset': 0x29, 'default': 0x18}, #0x18 = 0.78125 A (0.8 A, 12 V is maximum according to UM2717 guide of STM)
#     'T_FAST'    : {'addr': 0x0E, 'signed': False, 'num_bits': 8, 'num_bytes': 1, 'reset': 0x19, 'default': 0x19},
#     'TON_MIN'   : {'addr': 0x0F, 'signed': False, 'num_bits': 7, 'num_bytes': 1, 'reset': 0x29, 'default': 0x29},
#     'TOFF_MIN'  : {'addr': 0x10, 'signed': False, 'num_bits': 7, 'num_bytes': 1, 'reset': 0x29, 'default': 0x29},
#     'ADC_OUT'   : {'addr': 0x12, 'signed': False, 'num_bits': 5, 'num_bytes': 1, 'reset': '', 'default': ''},
#     'OCD_TH'    : {'addr': 0x13, 'signed': False, 'num_bits': 4, 'num_bytes': 1, 'reset': 0x8, 'default': 0x2}, #0x2 = 1.125 A
#     'STEP_MODE' : {'addr': 0x16, 'signed': False, 'num_bits': 8, 'num_bytes': 1, 'reset': 0x7, 'default': 0xF}, #x0f = 0b00001111, 16 bit microstepping
#     'ALARM_EN'  : {'addr': 0x17, 'signed': False, 'num_bits': 8, 'num_bytes': 1, 'reset': 0xFF, 'default': 0xFF},
#     'CONFIG'    : {'addr': 0x18, 'signed': False, 'num_bits': 16, 'num_bytes': 2, 'reset': 0x2E88, 'default': 0x2E88},
#     'STATUS'    : {'addr': 0x19, 'signed': False, 'num_bits': 16, 'num_bytes': 2, 'reset': '', 'default': ''},
#     }


# #@micropython.native
# def pulse(number=1):
#     # speed is about 1 pulse in 38.039 us
#     flag = False
#     if number<0:
#         direction.value(not direction.value()) # toggle direction
#         flag = True;

#     for i in range(abs(number)):
#         pwm.value(1)

#     if flag:
#         direction.value(not direction.value()) # toggle direction back


#def set_speed(usteps_per_second):
#    number,rest = divmod(

# def measure_uticks(N=1000):
#     t0 = ticks_us()
#     for i in range(1):
#         pulse(N)
#     t1 = ticks_us()
#     return (t1-t0)/N

