from micropython import const
from machine import SPI, Pin
from pyb import Timer, freq
import pyb

from time import sleep_ms, sleep_us, ticks_us

LOW = const(0)
HIGH = const(1)
ENDIANNES = const('big') # most significant byte first
L6474_instructions = {
    'SPI_FREQ'          : 4_000_000,    # 5_000_000 Hz is maximum according to L6474 datasheet
    'RESPONSE_DELAY_us' : 1,             # should be at least t_disCS, see Ch 8 in datasheet L6474
    'NOP'               : 0x00,
    'GET_STATUS'        : 0xd0,
    'ENABLE'            : 0xb8,
    'DISABLE'           : 0xa8,
    'GET_PARAM'         : 0x20,
    'SET_PARAM'         : 0x00,
    'ABS_POS_SIGN_BIT_MASK': 0x200000,  # =2**21
    }

# L6474 registers
L6474_registers = {
    'ABS_POS'   : {'addr': 0x01, 'signed': True, 'num_bits': 22, 'num_bytes': 3, 'reset': 0x0, 'default': 0x0},
    'EL_POS'    : {'addr': 0x02, 'signed': False,  'num_bits': 9, 'num_bytes': 2, 'reset': 0x0, 'default': 0x0},
    'MARK'      : {'addr': 0x03, 'signed': True,  'num_bits': 22, 'num_bytes': 3, 'reset': 0x0, 'default': 0x0},
    'TVAL'      : {'addr': 0x09, 'signed': False, 'num_bits': 7, 'num_bytes': 1, 'reset': 0x29, 'default': 0x18}, #0x18 = 0.78125 A
    'T_FAST'    : {'addr': 0x0E, 'signed': False, 'num_bits': 8, 'num_bytes': 1, 'reset': 0x19, 'default': 0x19},
    'TON_MIN'   : {'addr': 0x0F, 'signed': False, 'num_bits': 7, 'num_bytes': 1, 'reset': 0x29, 'default': 0x29},
    'TOFF_MIN'  : {'addr': 0x10, 'signed': False, 'num_bits': 7, 'num_bytes': 1, 'reset': 0x29, 'default': 0x29},
    'ADC_OUT'   : {'addr': 0x12, 'signed': False, 'num_bits': 5, 'num_bytes': 1, 'reset': '', 'default': ''},
    'OCD_TH'    : {'addr': 0x13, 'signed': False, 'num_bits': 4, 'num_bytes': 1, 'reset': 0x8, 'default': 0x2}, #0x2 = 1.125 A
    'STEP_MODE' : {'addr': 0x16, 'signed': False, 'num_bits': 8, 'num_bytes': 1, 'reset': 0x7, 'default': 0xF}, #x0f = 0b00001111, 16 bit microstepping
    'ALARM_EN'  : {'addr': 0x17, 'signed': False, 'num_bits': 8, 'num_bytes': 1, 'reset': 0xFF, 'default': 0xFF},
    'CONFIG'    : {'addr': 0x18, 'signed': False, 'num_bits': 16, 'num_bytes': 2, 'reset': 0x2E88, 'default': 0x2E88},
    'STATUS'    : {'addr': 0x19, 'signed': False, 'num_bits': 16, 'num_bytes': 2, 'reset': '', 'default': ''},
    }

# from ST manuals UM1857 (IHM01A1) and UM1724 (page 32,44,) (Nucleo-64) documentations
IHM01A1_pins = {
    'STBY_RESET_pin' : 'D8',  # pin 1 on CN5 = PA9 STM pin, pin 21 on CN10
    'PWM_pin'        : 'D9',  # pin 2 on CN5 = PC7 STM pin, pin 19 on CN10, TIM3_CH2
    'SPI_CS_pin'     : 'D10', # pin 3 on CN5 = PB6 STM pin, pin 17 on CN10, SPI1_CS
    'SPI_MOSI_pin'   : 'D11', # pin 4 on CN5 = PA7 STM pin, pin 15 on CN10, SPI1_MOSI
    'SPI_MISO_pin'   : 'D12', # pin 5 on CN5 = PA6 STM pin, pin 13 on CN10, SPI1_MISO
    'SPI_SCK_pin'    : 'D13', # pin 6 on CN5 = PA5 STM pin, pin 11 on CN10, SPI1_SCK

    'FLAG_pin'       : 'D2',      # pin 3 on CN9 = PA10 STM pin, pin 33 on CN10, -
    'DIR_pin'        : 'D7',      # pin 8 on CN9 = PA8 STM pin, pin 23 on CN10, -
}


# inputs:
flag      = Pin(IHM01A1_pins['FLAG_pin'], Pin.IN, Pin.PULL_UP)

# outputs:
reset     = Pin(IHM01A1_pins['STBY_RESET_pin'], mode=Pin.OUT, value=HIGH)
cs        = Pin(IHM01A1_pins['SPI_CS_pin'], mode=Pin.OUT, value=HIGH)
direction = Pin(IHM01A1_pins['DIR_pin'], mode=Pin.OUT, value=HIGH)     
tim       = pyb.Timer(3,period=200,prescaler=0x1a3) # scales clock to 100 kHz (10 us)
#pwm_tim = Timer(3,period=200,prescaler=41) # scales clock to 1000 kHz (1 us)
                                            # if period = 100, then 1 ustep every 100 * 1e-6 s
                                            # which is 10 usteps / ms
ch = tim.channel(2,pyb.Timer.OC_TOGGLE,pin=pyb.Pin.board.D9)

#spi = SPI(1,polarity=1,phase=0,baudrate=L6474_instructions['SPI_FREQ'],sck=IHM01A1_pins['SPI_SCK_pin'],mosi=IHM01A1_pins['SPI_MOSI_pin'],miso=IHM01A1_pins['SPI_MISO_pin'],firstbit=SPI.MSB)
#spi = SPI(1,polarity=1,phase=1,baudrate=L6474_instructions['SPI_FREQ'],firstbit=SPI.MSB)

#spi = SPI(id=1,polarity=1,phase=1,baudrate=L6474_instructions['SPI_FREQ'],firstbit=SPI.MSB)

#spi = SoftSPI(polarity=1,phase=1,baudrate=L6474_instructions['SPI_FREQ'],sck=IHM01A1_pins['SPI_SCK_pin'],mosi=IHM01A1_pins['SPI_MOSI_pin'],miso=IHM01A1_pins['SPI_MISO_pin'],firstbit=SoftSPI.MSB)

spi = SPI(1)
spi.init(polarity=1,phase=1,baudrate=L6474_instructions['SPI_FREQ'],firstbit=SPI.MSB)


def binformat(int_value):
    if 0 << int_value & int_value < 2**8:
        return f'{int_value:08b}'
    elif 0<< int_value & int_value < 2**16:
        return f'{int_value:016b}'
    elif -L6474_instructions['ABS_POS_SIGN_BIT_MASK'] <= int_value < L6474_instructions['ABS_POS_SIGN_BIT_MASK']:
        return f'{int_value:024b}'
    else:
        return f'{int_value:b}'

def bytes2int(bytes_,signed=False):
    val = int.from_bytes(bytes_,ENDIANNES,False)
    if signed and (val & L6474_instructions['ABS_POS_SIGN_BIT_MASK']):
        return val-2*L6474_instructions['ABS_POS_SIGN_BIT_MASK']
    else:
        return val            

def int2bytes(value,number_of_bytes,signed=False):
    if signed and (value < 0):
        value += 2*L6474_instructions['ABS_POS_SIGN_BIT_MASK']
    return value.to_bytes(number_of_bytes,ENDIANNES,False)        


def spi_send_receive(txdata):
    rxdata = bytearray(len(txdata))
    tx_ = memoryview(txdata)
    rx_ = memoryview(rxdata)
    for i in range(len(txdata)):
        cs.value(LOW)
        #rx = bytearray(1)
        #tx = txdata[i:i+1]
        spi.write_readinto(tx_[i:i+1],rx_[i:i+1]) # seems to work
        cs.value(HIGH)
        sleep_us(L6474_instructions['RESPONSE_DELAY_us'])
        #rxdata[i:i+1] = rx
    return rxdata[1:]


def get_status():
    txdata = int2bytes(L6474_instructions['GET_STATUS'],1)
    txdata += int2bytes(L6474_instructions['NOP'],1) * L6474_registers['STATUS']['num_bytes']
    #txdata = int2bytes(0xd,1)
    #txdata += b'\x00\x00'
    rxdata = spi_send_receive(txdata)
    return bytes2int(rxdata)

def enable():
    cs.value(LOW)
    spi.write(int2bytes(L6474_instructions['ENABLE'],1))
    cs.value(HIGH)
    sleep_us(L6474_instructions['RESPONSE_DELAY_us'])

def disable():
    cs.value(LOW)
    spi.write(int2bytes(L6474_instructions['DISABLE'],1))
    cs.value(HIGH)
    sleep_us(L6474_instructions['RESPONSE_DELAY_us'])


def get_param(param='ABS_POS'):
    #param = param.upper()
    txdata = bytes([L6474_instructions['GET_PARAM'] | L6474_registers[param]['addr']]) + int2bytes(L6474_instructions['NOP'],1)*L6474_registers[param]['num_bytes']
    rxdata = spi_send_receive(txdata)
    return bytes2int(rxdata,signed=L6474_registers[param]['signed'])


ABS_POS_SIGN_BIT_MASK = const(0x200000)
ABS_POS_SIGN_TERM     = const(0x400000)
spi_txdata_abs_pos = const(b'\x21\x00\x00\x00') # immutable
spi_rxdata_abs_pos = bytearray(4)               # mutable
tx = memoryview(spi_txdata_abs_pos)
rx = memoryview(spi_rxdata_abs_pos)

def get_abs_pos_efficient():
    # for i in range(4): # consider loop unrolling
    #     cs.value(LOW)
    #     spi.write_readinto(tx[i:i+1],rx[i:i+1]) # seems to work
    #     cs.value(HIGH)
    #     sleep_us(1)

    cs.value(LOW)
    spi.write_readinto(tx[0:1],rx[0:1]) # seems to work
    cs.value(HIGH)
    sleep_us(1)
    cs.value(LOW)
    spi.write_readinto(tx[1:2],rx[1:2]) # seems to work
    cs.value(HIGH)
    sleep_us(1)
    cs.value(LOW)
    spi.write_readinto(tx[2:3],rx[2:3]) # seems to work
    cs.value(HIGH)
    sleep_us(1)
    cs.value(LOW)
    spi.write_readinto(tx[3:],rx[3:]) # seems to work
    cs.value(HIGH)
    sleep_us(1)
        
    val = int.from_bytes(spi_rxdata_abs_pos[1:],ENDIANNES,False)
    if val & ABS_POS_SIGN_BIT_MASK:
        return val - ABS_POS_SIGN_TERM
    else:
        return val


    
def set_param(param,value):
    param = param.upper()
    byte_values = int2bytes(value,L6474_registers[param]['num_bytes'],signed=L6474_registers[param]['signed'])
    check_value = bytes2int(byte_values,signed=L6474_registers[param]['signed'])
    if check_value != value:
        raise ValueError(f'value ({value}) cannot be properly converted to binary data.')
    txdata = bytes([L6474_instructions['SET_PARAM'] | L6474_registers[param]['addr']]) + byte_values
    rxdata = spi_send_receive(txdata)
    return bytes2int(rxdata,signed=L6474_registers[param]['signed'])
    
def set_default():
    ret = 0
    for reg in L6474_registers:
        value = L6474_registers[reg]['default']
        if isinstance(value,int):
            res = set_param(reg,value)
            #print(f'register {reg} set to {value}, response is {res}')
            ret += res
    return ret

def pulse(number=1):
    # speed is about 1 pulse in 38.039 us
    flag = False
    if number<0:
        direction.value(not direction.value()) # toggle direction
        flag = True;
        
    for i in range(abs(number)):
        pwm.value(1)
       
    if flag:
        direction.value(not direction.value()) # toggle direction back


#def set_speed(usteps_per_second):
#    number,rest = divmod(

def measure_uticks(N=1000):
    t0 = ticks_us()
    for i in range(1):
        pulse(N)
    t1 = ticks_us()
    return (t1-t0)/N


