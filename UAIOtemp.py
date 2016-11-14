'''
### Python2 file (The author is still unwilling to convert to python3.)
Class to communicate to Analog IO temperature controller via serial.
Author: Adrian Utama 
Modified from similar serial communication class by Nick (CQT Devices)
Last updated: 11 Nov 2016
'''

# Simple analog IO unit.

# Usage: Send plaintext commands, separated by newline/cr or semicolon.
#        An eventual reply comes terminated with cr+lf.

# Important commands:

# *IDN?     Returns device identifier
# *RST      Resets device, outputs are 0V.
# OUT  <channel> <value>
#           Sets <channel> (ranging from 0 to 7) to
#           the voltage <value>. Use 2.5 as value, not 2.5E0
# IN?  <channel>
#           Returns voltage of input <channel>.
# TEMP?     Returns the temperature in the ADC.
# ALLIN?    Returns all 8 input voltages and temperature.
# HELP      Print this help text.

# ATTENTION:
# There are still offsets and gain errors which are not compensated for.
# Likewise, the temperatue reported uses a calibration offset that
# seemed resonable but deviates from the data sheet significantly.
# Therefore, do use absolute values with care.

import serial

class UAIOtemp_comm(object):
# Module for communicating with the power meter    
    baudrate = 115200
    
    def __init__(self, port):
        self.serial = self._open_port(port)
        self._serial_write('*IDN?')# flush io buffer
        print self._serial_read() #will read unknown command
        
    def _open_port(self, port):
        ser = serial.Serial(port, timeout=1)
        return ser
    
    def _serial_write(self, string):
        self.serial.write(string + '\n')
    
    def _serial_read(self):
        msg_string = self.serial.readline()
        # Remove any linefeeds etc
        msg_string = msg_string.rstrip()
        return msg_string
    
    def reset(self):
        self._serial_write('*RST')
        return self._serial_read()
        
    def set_output_volt(self, channel, value):
        self._serial_write('OUT ' + str(channel) + ' '+ str(value))
        return 
     
    def get_input_volt(self,channel):
        self._serial_write('IN? ' + str(channel))
        out = self._serial_read()
        return out
    
    def get_temp(self):
        self._serial_write('TEMP?')
        out = self._serial_read()
        return out 

    def get_allin(self):
        self._serial_write('ALLIN?')
        out = self._serial_read()
        return out

    def close(self):
        self.serial.close()
    

if __name__ == '__main__':
    import time
    UAIOtemp_addr = '/dev/serial/by-id/usb-Centre_for_Quantum_Technologies_Analog_IO_unit_UAIO-QO09-if00'
    temp_comm = UAIOtemp_comm(UAIOtemp_addr)
    
    start = time.time()

    a = []
    for i in range (1000):
        # To repeat the step if command not understood (probably some problem with the firmware)
        while True:
            value = temp_comm.get_input_volt(1)
            if value == 'Unknown command':
                print 'shit'
                pass
            else:
                a.append(value)
                break

    # print a
    print len(a)

    end = time.time()
    temp_comm.close()

    print "Waktu", end - start
    
    
       
      
    