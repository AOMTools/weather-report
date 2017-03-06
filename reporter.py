'''
WEATHER REPORT v1.01
This program will report the temperature on 4 different locations, and log them. Complete with the locking algorithm to stabilise the temperature
v 1.01 Added functionality to call telegram for help also for some time reporting

Author: Adrian Nugraha Utama
Nov 2016

Note: The program uses Multithread with Tkinter. See Python Cookbook: Combining Tkinter and Asynchronous I/O with Threads (Jacob Hallen).
'''

import Tkinter
import time
import threading
import Queue
import zmq
import numpy as np
import subprocess as sp
from UAIOtemp import UAIOtemp_comm
import datetime

# For weather reporting
WR_when = [datetime.time(07,00,0,0), datetime.time(12,00,0,0), datetime.time(15,00,0,0), datetime.time(18,00,0,0), datetime.time(22,00,0,0)]
WR_what = ['Good morning everyone, hope you had a nice sleep. Below is the report on the temperature this morning. Today will be a very good day, I believe !!!', 'Lunch time everybody!!! Here is the report of the temperature.','Coffee break everybody!!! While you are having coffee, here is the report on the temperature.', 'It is time to go home. Hope you had a great day. Here is the temperature now', 'Good night, sleep tight, and see you tomorrow!!! Btw, the current temperature is as follows']
WR_pointer = 0

# Telegram Group
USER = 'Cavity'

# SOME PARAMETERS:
GUI_RATE    = 100   # 100 ms
LOG_RATE    = 1000  # 1 s

# LOCKING PARAMETER
MAX_OUTVOLT = 10
MIN_OUTVOLT = 0

# SERIAL ADDRESSES
UAIOtemp_addr = '/dev/serial/by-id/usb-Centre_for_Quantum_Technologies_Analog_IO_unit_UAIO-QO09-if00'

def insanity_check(number, min_value, max_value):
    ''' To check whether the value is out of given range'''
    if number > max_value:
        return max_value
    if number < min_value:
        return min_value
    else:
        return number

class GuiPart:
    def __init__(self, master, queue, endCommand):
        self.master = master
        self.queue = queue

        # Initialise variables
        self.temperature_disp = [0, 0, 0, 0]    # To be attached to temperature
        self.temperature_value = [20, 20, 20, 20] # To hold the values for the temperatures

        self.entry = [0, 0, 0, 0]   # To be attached to the set_value
        self.set_value = [23.2, 10, 100, 10]   # Set value for parameters
        self.rough_step = [0.3, 1, 5, 10]
        self.fine_step = [0.01, 0.1, 0.5, 1]
        self.max_set_value= [30, 1000, 1000, 1000]
        self.min_set_value = [15, 0, 0, 1]
        self.set_value_dict = [u" \u00b0C", " V/K", " mV/Ks", " s"]

        self.outvolt_value = 5

        self.params_label = ["Delta Avg:", "Delta Acc:", "P Adj:", "I Adj:"]
        self.params_disp = [0, 0, 0, 0]     # To be attached to params_value
        self.params_value = [0, 50, 0, 5]
        self.params_units = ["K   ", "Ks   ", "V   ", "V"]

        # Set up the GUI

        # LEFT FRAME
        self.frame1 = Tkinter.Frame(self.master)
        Tkinter.Label(self.frame1, text='Temperature Reading', font=("Helvetica", 16)).grid(row=1, padx=5, pady=5, column=1, columnspan= 10)

        Tkinter.Label(self.frame1, text='Sensor 0:', font=("Helvetica", 16), fg='yellow3').grid(row=2, padx=5, pady=5, column=1, sticky=Tkinter.W)
        Tkinter.Label(self.frame1, text='Sensor 1:', font=("Helvetica", 16), fg='deeppink').grid(row=3, padx=5, pady=5, column=1, sticky=Tkinter.W)
        Tkinter.Label(self.frame1, text='Sensor 2:', font=("Helvetica", 16), fg='green').grid(row=4, padx=5, pady=5, column=1, sticky=Tkinter.W)
        Tkinter.Label(self.frame1, text='Sensor 3:', font=("Helvetica", 16), fg='blue').grid(row=5, padx=5, pady=5, column=1, sticky=Tkinter.W)

        for i in range(4):
            self.temperature_disp[i] = Tkinter.Label(self.frame1, text='%.3f'%round(self.temperature_value[i],3)+ u" \u00b0C", font=("Helvetica", 16))
            self.temperature_disp[i].grid(row=2+i, padx=0, pady=5, column=2, sticky=Tkinter.W)
        self.frame1.pack(side=Tkinter.LEFT, anchor=Tkinter.N)

        # RIGHT FRAME
        self.frame2 = Tkinter.Frame(self.master)
        Tkinter.Label(self.frame2, text='Temperature (Sensor 0) Stabilization Module', font=("Helvetica", 16)).grid(row=1, padx=5, pady=5, column=1, columnspan=20, sticky=Tkinter.W)

        Tkinter.Label(self.frame2, text='Set Temp', font=("Helvetica", 16)).grid(row=2, padx=5, pady=5, column=1, sticky=Tkinter.W)
        Tkinter.Label(self.frame2, text='P Value', font=("Helvetica", 16)).grid(row=3, padx=5, pady=5, column=1, sticky=Tkinter.W)
        Tkinter.Label(self.frame2, text='I Value', font=("Helvetica", 16)).grid(row=4, padx=5, pady=5, column=1, sticky=Tkinter.W)
        Tkinter.Label(self.frame2, text='Rf. Rate', font=("Helvetica", 16)).grid(row=5, padx=5, pady=5, column=1, sticky=Tkinter.W)

        for i in range(4):
            Tkinter.Button(self.frame2, text='<<', font=("Helvetica", 12), command=lambda i=i:self.buttonPressed(i, 1)).grid(row=2+i, column=2)
            Tkinter.Button(self.frame2, text='<', font=("Helvetica", 12), command=lambda i=i:self.buttonPressed(i, 2)).grid(row=2+i, column=3)
            Tkinter.Button(self.frame2, text='>', font=("Helvetica", 12), command=lambda i=i:self.buttonPressed(i, 3)).grid(row=2+i, column=6)
            Tkinter.Button(self.frame2, text='>>', font=("Helvetica", 12), command=lambda i=i:self.buttonPressed(i, 4)).grid(row=2+i, column=7)

            self.entry[i] = Tkinter.Entry(self.frame2, width=15, font=("Helvetica", 16), justify=Tkinter.CENTER)
            self.entry[i].grid(row=2+i, column=4, columnspan=2)
            self.entry[i].insert(0, '%.2f'%round(self.set_value[i],2) + self.set_value_dict[i])

        # Set locking checkbox
        self.set_lock = Tkinter.IntVar()
        self.chk_set = Tkinter.Checkbutton(self.frame2, text='Lock', font=("Helvetica", 16), variable=self.set_lock)
        self.chk_set.grid(row=7, column=1, padx=5, pady=5, sticky=Tkinter.W)

        Tkinter.Label(self.frame2, text='Output Voltage:', font=("Helvetica", 16)).grid(row=7, padx=5, pady=5, column=2, columnspan=3, sticky=Tkinter.W)
        self.outvolt_disp = Tkinter.Label(self.frame2, text='%.3f'%round(self.outvolt_value,3) + " V", font=("Helvetica", 16))
        self.outvolt_disp.grid(row=7, padx=5, pady=5, column=5, columnspan=1, sticky=Tkinter.W)

        # Display other params
        self.frame2param = Tkinter.Frame(self.frame2)
        for i in range(4):
            Tkinter.Label(self.frame2param, text=self.params_label[i], font=("Helvetica", 9)).pack(side=Tkinter.LEFT)
            self.params_disp[i] = Tkinter.Label(self.frame2param, text='%.3f'%round(self.params_value[i],3), font=("Helvetica", 9))
            self.params_disp[i].pack(side=Tkinter.LEFT)
            Tkinter.Label(self.frame2param, text=self.params_units[i], font=("Helvetica", 9)).pack(side=Tkinter.LEFT)
        self.frame2param.grid(row=6, column=1, columnspan=10, padx=5, pady=0, sticky=Tkinter.W)

        self.frame2.pack(side=Tkinter.LEFT, anchor=Tkinter.N)

    def buttonPressed(self, channel, button_type):
        # Performing the stuffs for Channel 1 to 6 (Voltage)
        if button_type == 1:
            self.set_value[channel] -= self.rough_step[channel]
        elif button_type == 2:
            self.set_value[channel] -= self.fine_step[channel]
        elif button_type == 3:
            self.set_value[channel] += self.fine_step[channel]
        elif button_type == 4:
            self.set_value[channel] += self.rough_step[channel]

        # Insanity check the values
        self.set_value[channel] = insanity_check(self.set_value[channel], self.min_set_value[channel], self.max_set_value[channel])

        self.entry[channel].delete(0, Tkinter.END)
        self.entry[channel].insert(0, '%.2f'%round(self.set_value[channel],2) + self.set_value_dict[channel])

    def processIncoming(self):
        """Handle all messages currently in the queue, if any."""
        while self.queue.qsize(  ):
            try:
                msg = self.queue.get(0)
                # Check contents of message and do whatever is needed. As a
                # simple test, print it (in real life, you would
                # suitably update the GUI's display in a richer fashion).
                print msg
            except Queue.Empty:
                # just on general principles, although we don't
                # expect this branch to be taken in this case
                pass

class ThreadedClient:
    """
    Launch the main part of the GUI and the worker thread. periodicCall and
    endApplication could reside in the GUI part, but putting them here
    means that you have all the thread controls in a single place.
    """
    def __init__(self, master):
        """
        Start the GUI and the asynchronous threads. We are in the main
        (original) thread of the application, which will later be used by
        the GUI as well. We spawn a new thread for the worker (I/O).
        """
        self.master = master

        # Create the queue
        self.queue = Queue.Queue(  )

        # Set up the GUI part
        self.gui = GuiPart(master, self.queue, self.endApplication)
        master.protocol("WM_DELETE_WINDOW", self.endApplication)   # About the silly exit button

        # Start the procedure regarding the initialisation of experimental parameters and objects
        self.initialiseParameters()

        # Set up the thread to do asynchronous I/O
        # More threads can also be created and used, if necessary
        self.running = 1
        self.thread1 = threading.Thread(target=self.workerThread1_UAIO)
        self.thread1.start(  )

        # Define the status of the lock
        self.status = 0  # 0 - not started, 1 - started, 2 - dangerous

        # Start the periodic call in the GUI to check if the queue contains
        # anything
        self.periodicCall(  )

    def initialiseParameters(self):
        # Communiate with the analog powermeter
        self.temp_comm = UAIOtemp_comm(UAIOtemp_addr)

        # Create a variable to store the values emitted from the analog powermeter
        self.temperature_value = [20, 20, 20, 20]

        # Create the list to replicate the entry from user
        self.entry = [0, 0, 0, 0]   # Set temp, P value, I value, Refresh rate

        # Create the list of the params values
        self.params_value = [0, 50, 0, 5]

        # Create the variable to store the outvolt
        self.outvolt = 0

        # Creating the objects voltage_handler
        self.voltage_handler = VoltageHandler(1, 0) # Channel 0 in the UAIO board

        # Counter helper variable for lock processing
        self.counter_ref = 0

    def periodicCall(self):
        """
        Check every 100 ms if there is something new in the queue.
        """
        self.gui.processIncoming(  )

        # Setting a refresh rate for periodic call
        self.master.after(GUI_RATE, self.periodicCall)

        # Update the display of temperature
        self.gui.temperature_value = self.temperature_value
        for i in range(4):
            self.gui.temperature_disp[i]['text'] = '%.3f'%round(self.gui.temperature_value[i],3)+ u" \u00b0C"

        # Dealing with status and lock
        if self.gui.set_lock.get() == 1:    # If lock is set
            self.status = 1
        else:
            self.status = 0

        if self.status == 1:
            self.process_lock()

        # Shutting down the program
        if not self.running:
            print "Shutting Down"
            import sys
            sys.exit()

    def process_lock(self):
        # Refresh the entry value based on the GUI entry value (located in the set_value)
        self.entry = self.gui.set_value  # Set temp, P value, I value, Refresh rate

        # Calculate the difference between the set temp and temp
        delta = self.temperature_value[0] - self.entry[0]  # Positive if current temp is higher than the set
        num_of_avg = int(self.entry[3] * 1000 / GUI_RATE)  # get the number of averages
        self.params_value[0] = (self.params_value[0] * (num_of_avg - 1) + delta) / num_of_avg  # Update the delta avg (entry params 0) - using exponential moving average
        self.params_value[1] += self.params_value[0] * GUI_RATE / 1000

        # Update counter ref and check if time has come to modify the outvolt
        self.counter_ref += 1
        if self.counter_ref > num_of_avg:
            # PID modifiers
            self.params_value[2] = self.params_value[0] * self.entry[1]
            self.params_value[3] = self.params_value[1] * self.entry[2] / 1000  # self.entry[2] is in mV/Ks
            outvolt = self.params_value[2] + self.params_value[3]

            # Sanitise the output voltage
            outvolt = insanity_check(outvolt, MIN_OUTVOLT, MAX_OUTVOLT)
            self.outvolt = round(outvolt,3)

            # TO APPEND TO CONTROL LOG FILES
            # Get the time now
            now1 = str(time.strftime("%y%m%d")) # Day
            now2 = str(time.strftime("%H%M%S")) # Moment
            entry0 = '%.2f'%round(self.entry[0],2)
            entry1 = '%.2f'%round(self.entry[1],2)
            entry2 = '%.2f'%round(self.entry[2],2)
            entry3 = '%.2f'%round(self.entry[3],2)
            param0 = '%.3f'%round(self.params_value[0],3)
            param1 = '%.3f'%round(self.params_value[1],3)
            param2 = '%.3f'%round(self.params_value[2],3)
            param3 = '%.3f'%round(self.params_value[3],3)
            out = '%.3f'%round(self.outvolt,3)
            # Write to the file
            with open("control_log", "a") as myfile:
                myfile.write(now1 + ' ' + now2 + ' ' + entry0 + ' ' + entry1 + ' ' + entry2 + ' ' + entry3 + ' ' + param0 + ' ' + param1 + ' ' + param2 + ' ' + param3 + ' ' + out + '\n' )

            # Cancel the lock (dangerous) if some of the params get crazy
            if outvolt < 2 or outvolt > 9:
                message = '### Message from Shiva and Ifrit. Looks that the temperature is playing prank on us. If possible please handle it ASAP!!!'
                sp.call(['./telegram_report.sh',USER,message])
                message = 'PARAMS:' + ' ' + now1 + ' ' + now2 + ' ' + entry0 + ' ' + entry1 + ' ' + entry2 + ' ' + entry3 + ' ' + param0 + ' ' + param1 + ' ' + param2 + ' ' + param3 + ' ' + out
                sp.call(['./telegram_report.sh',USER,message])
                message = 'UNLOCKING (to prevent further problems) ###'
                sp.call(['./telegram_report.sh',USER,message])
                self.gui.set_lock.set(0)
                status = 2

            # Reset the counter
            self.counter_ref = 0

            # Report stuffs via telegram
            global WR_pointer
            WR_now = datetime.datetime.now().time()
            if WR_pointer != -1:
                if WR_now > WR_when[WR_pointer]:
                    print "Sending messages"
                    message = '### Message from Shiva and Ifrit ###'
                    sp.call(['./telegram_report.sh',USER,message])
                    message = WR_what[WR_pointer]
                    sp.call(['./telegram_report.sh',USER,message])
                    message = 'Temperatures around the chamber is ' + self.gui.temperature_disp[0]['text'] + ' ' + self.gui.temperature_disp[1]['text'] + ' ' + self.gui.temperature_disp[2]['text'] + ' ' + self.gui.temperature_disp[3]['text'] + ' , and output voltage is ' + out
                    sp.call(['./telegram_report.sh',USER,message])
                    WR_pointer +=1
                    if WR_pointer > len(WR_when) - 1:
                        WR_pointer = -1
                        print "Wait until the the counter reset the next day"
                    else:
                        print "Next message will be on " + str(WR_when[WR_pointer])
            else:
                if WR_now < datetime.time(00,05,0,0):
                    print "Hello the next day"
                    WR_pointer = 0

        # Update the display of params and outvolt value
        self.gui.params_value = self.params_value
        for i in range(4):
            self.gui.params_disp[i]['text'] = '%.3f'%round(self.gui.params_value[i],3)
        self.gui.outvolt_value = self.outvolt
        self.gui.outvolt_disp['text'] = '%.3f'%self.outvolt + " V"



    def workerThread1_UAIO(self):
        """
        This is another thread that deals with serial communication. This runs independently from the main thread,
        but communicates the necessary variables and parameters
        """
        while self.running:
            try:

                # Get temp from the board
                getallin = self.temp_comm.get_allin()
                value_array = getallin.split()[:4]
                # Conversion parameters
                R1 = 10000
                Vpu = 10
                T0 = 25
                B = 3988
                R0 = 10000
                C2K = 273.15
                # Conversion process
                temp_array = []
                for value in value_array:
                    R2 = R1 * float(value) / (Vpu - float(value))
                    temp_array.append(1/( 1/(T0-C2K) + np.log(R2/R0)/B ) + C2K)
                self.temperature_value = temp_array # MODIFY THE MAIN THREAD

                # TO APPEND TO TEMP_LOG FILES
                # Get the time now
                now1 = str(time.strftime("%y%m%d")) # Day
                now2 = str(time.strftime("%H%M%S")) # Moment
                temp0 = '%.3f'%round(temp_array[0],3)
                temp1 = '%.3f'%round(temp_array[1],3)
                temp2 = '%.3f'%round(temp_array[2],3)
                temp3 = '%.3f'%round(temp_array[3],3)
                # Write to the file
                with open("temp_log", "a") as myfile:
                    myfile.write(now1 + ' ' + now2 + ' ' + temp0 + ' ' + temp1 + ' ' + temp2 + ' ' + temp3 + '\n' )

                # Now deal with outvolt using Voltage handler. Need to do this as not to overlap the communication to serial, i.e. all serial comm is done in this place
                self.voltage_handler.change_set_voltage(self.outvolt)   # Check and "update" what is the status of self.outvolt
                update, output = self.voltage_handler.update()
                if update:
                	self.temp_comm.set_output_volt(0, output)

                time.sleep(LOG_RATE/1000)

            except:
                print "Cannot get temp or update outvolt. Something fishy is happening."
                pass

    def endApplication(self):
        # Kill and wait for the processes to be killed
        self.running = 0

        # Turning the analog powermeter device and serial off
        self.temp_comm.close()
        print "Serial communication closed"


class VoltageHandler:
    """
    Handles the set voltage and give appropriate commands
    """
    def __init__(self, arg_max_step, arg_channel):
        """
        Initialise the object and giving it initial value
        """
        self.set_voltage = 5
        self.output_voltage = 0
        self.max_step = arg_max_step
        self.channel = arg_channel
        print "Voltage Handler Object Created"

    def change_set_voltage(self, arg_set_voltage):
        self.set_voltage = arg_set_voltage

    def update(self):
    	update = 0	# Either to update or not
        if self.output_voltage != self.set_voltage:
            if self.output_voltage > self.set_voltage:
                step_down = min((self.output_voltage-self.set_voltage), self.max_step)
                self.output_voltage -= step_down
            elif self.output_voltage < self.set_voltage:
                step_up = min((self.set_voltage-self.output_voltage), self.max_step)
                self.output_voltage += step_up
            ''' Here is where the command line to change the voltage goes'''
            print "Output Voltage ", self.channel, " modifed to ", self.output_voltage
            update = 1
        # Return output_voltage to be displayed on the GUI
        return (update, self.output_voltage)

''' Main program goes here '''

root = Tkinter.Tk(  )
root.title("Weather Report v1.01 With Telegram")

img = Tkinter.PhotoImage(file='icon.png')
root.tk.call('wm', 'iconphoto', root._w, img)

client = ThreadedClient(root)
root.mainloop(  )
