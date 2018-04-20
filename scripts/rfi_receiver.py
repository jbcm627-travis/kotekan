"""
/*********************************************************************************
* RFI Documentation Header Block
* File: rfi_receiver.py
* Purpose: A server to receive real-time rfi data from kotekan and send to rfi_client.py
* Python Version: 3.6 
* Dependencies: yaml, numpy, argparse
* Help: Run "python3 rfi_receiver.py" -H (or --Help) for how to use.
*********************************************************************************/
"""

import threading
import socket
import numpy as np
import datetime
import os
import random
import time
import argparse
import yaml
import json
import sys

class CommandLine:

    def __init__(self):

        #Defaults
        self.UDP_IP= "0.0.0.0"
        self.UDP_PORT = 2900
        self.TCP_IP = '10.10.10.2'
        self.TCP_PORT = 41214
        self.mode = 'pathfinder'
        self.config = {'frames_per_packet': 4, 'num_freq': 1024, 'num_local_freq': 8, 'samples_per_data_set':32768, 'num_elements': 2,
                        'timestep':2.56e-6, 'bytes_per_freq': 16, 'waterfallX': 1024, 'waterfallY': 1024, 'vdif_rfi_header_size': 21,
                        'sk_step': 256, 'chime_rfi_header_size': 35, 'num_receive_threads': 1}
        self.supportedModes = ['vdif','pathfinder', 'chime']
        parser = argparse.ArgumentParser(description = "RFI Receiver Script")
        parser.add_argument("-H", "--Help", help = "Example: Help argument", required = False, default = "")
        parser.add_argument("-r", "--receive", help = "Example: 127.0.0.1:2900", required = False, default = "")
        parser.add_argument("-s", "--send", help = "Example: 10.10.10.2:41214", required = False, default = "")
        parser.add_argument("-c", "--config", help = "Example: ../kotekan/kotekan_opencl_rfi.yaml", required = False, default = "")
        parser.add_argument("-m", "--mode", help = "Example: vdif, pathfinder", required = False, default = "")
        argument = parser.parse_args()
        status = False

        if argument.Help:
            print("You have used '-H' or '--Help' with argument: {0}".format(argument.Help))
            status = True
        if argument.send:
            print("You have used '-s' or '--send' with argument: {0}".format(argument.send))
            self.TCP_IP = argument.send[:argument.send.index(':')]
            self.TCP_PORT = int(argument.send[argument.send.index(':')+1:])
            print("Setting TCP IP: %s PORT: %d"%(self.TCP_IP ,self.TCP_PORT ))
            status = True
        if argument.receive:
            print("You have used '-r' or '--receive' with argument: {0}".format(argument.receive))
            self.UDP_IP = argument.receive[:argument.receive.index(':')]
            self.UDP_PORT = int(argument.receive[argument.receive.index(':')+1:]) 
            print("Setting UDP IP: %s PORT: %d"%(self.UDP_IP ,self.UDP_PORT ))
            status = True
        if argument.config:
            print("You have used '-c' or '--config' with argument: {0}".format(argument.config))
            for key, value in yaml.load(open(argument.config)).items():
                if(type(value) == dict):
                    if('kotekan_process' in value.keys() and value['kotekan_process'] == 'rfiBroadcast'):
                        for k in value.keys():
                            if k in self.config.keys():
                                if(type(self.config[k]) == type(value[k])):
                                    print("Setting Config Paramter %s to %s" %(k,str(value[k])))
                                    self.config[k] = value[k]
                else:
                    if key in self.config.keys():
                        if(type(self.config[key]) == type(value)):
                            print("Setting Config Paramter %s to %s" %(key,str(value)))
                            self.config[key] = value
            print(self.config)
            status = True
        if argument.mode:
            print("You have used '-m' or '--mode' with argument: {0}".format(argument.mode))

            if(argument.mode in self.supportedModes):
                self.mode = argument.mode
                print("Setting mode to %s mode."%(argument.mode))
            else:
                print("This mode in currently not supported, reverting to default")
                print("Supported Modes Include:")
                for mode in self.supportedModes:
                    print("- ",mode)
            status = True
        if not status:
            print("Remember: You can use -H or - Help to see configuration options") 

class Stream:


    def __init__(self, header):

        encoded_stream_id = header['encoded_stream_ID'][0]
        self.link_id = encoded_stream_id & 0x000F 
        self.slot_id = (encoded_stream_id & 0x00F0) >> 4
        self.crate = (encoded_stream_id & 0x0F00) >> 8
        self.unused = (encoded_stream_id & 0xF000) >> 12
        #self.bins = [self.slot_id + self.link_id * 16 + i * 128 for i in range(header['num_local_freq'])]
        self.bins = [self.crate*16 + self.slot_id + self.link_id*32 + self.unused *256 for i in range(header['num_local_freq'])]
        self.freqs = [800.0 - float(b) * 400.0/1024.0 for b in self.bins]
        self.bins = np.array(self.bins).astype(int)
        self.freqs = np.array(self.freqs)
        print("Stream Created %d %d %d %d"%( self.slot_id, self.link_id, self.crate, self.unused))
        print(self.bins, self.freqs)


def chimeHeaderCheck(header,app):

    if(header['combined_flag'] != 1):
        print("Chime Header Error: Only Combined RFI values are currently supported ")
        return False
    if(header['sk_step'] != app.config['sk_step']):
        print("Chime Header Error: SK Step does not match config")
        return False
    if(header['num_elements'] != app.config['num_elements']):
        print("Chime Header Error: Number of Elements does not match config")

        return False
    if(header['num_timesteps'] != app.config['samples_per_data_set']):
        print("Chime Header Error: Samples per Dataset does not match config")
        return False
    if(header['num_global_freq'] != app.config['num_freq']):
        print("Chime Header Error: Number of Global Frequencies does not match config")
        return False
    if(header['num_local_freq'] != app.config['num_local_freq']):
        print("Chime Header Error: Number of Local Frequencies does not match config")
        return False
    if(header['fpga_seq_num'] < 0):
        print("Chime Header Error: Invalid FPGA sequenc Number")
        return False
    if(header['frames_per_packet']  != app.config['frames_per_packet']):
        print("Chime Header Error: Frames per Packet does not match config")
        return False

    print("First Packet Received, Valid Chime Header Confirmed.")
    return True


def VDIFHeaderCheck(header,app):
    
    if(header['combined_flag'] != 1):
        print("VDIF Header Error: Only Combined RFI values are currently supported ")
        return False
    if(header['sk_step'] != app.config['sk_step']):
        print("VDIF Header Error: SK Step does not match config")
        return False
    if(header['num_elements'] != app.config['num_elements']):
        print("VDIF Header Error: Number of Elements does not match config")
        return False
    if(header['num_times_per_frame'] != app.config['samples_per_data_set']):
        print("VDIF Header Error: Samples per Dataset does not match config")
        return False
    if(header['num_freq'] != app.config['num_freq']):
        print("VDIF Header Error: Number of Frequencies does not match config")
        return False
    return True

def data_listener(socket_udp):

    global waterfall, t_min, app

    #Config Variables
    frames_per_packet = app.config['frames_per_packet']
    local_freq = app.config['num_local_freq']
    timesteps_per_frame = app.config['samples_per_data_set']
    timestep = app.config['timestep']
    bytesPerFreq = app.config['bytes_per_freq']
    global_freq = app.config['num_freq']
    sk_step = app.config['sk_step']
    vdifRFIHeaderSize = app.config['vdif_rfi_header_size']
    chimeRFIHeaderSize = app.config['chime_rfi_header_size']
    mode = app.mode
    firstPacket = True
    vdifPacketSize = global_freq*4 + vdifRFIHeaderSize
    chimePacketSize = chimeRFIHeaderSize + 4*local_freq
    chimeHeaderDataType = np.dtype([('combined_flag',np.uint8,1), ('encoded_stream_ID',np.uint16,1),('sk_step',np.uint32,1),
        ('num_elements',np.uint32,1),('num_timesteps',np.uint32,1),('num_global_freq',np.uint32,1),
        ('num_local_freq',np.uint32,1),('frames_per_packet',np.uint32,1),('fpga_seq_num',np.int64,1)])
    stream_dict = dict()
    packetCounter = 0;
    while True:

        if (mode == 'pathfinder'):

            #Receive packet from port
            packet, addr = sock_udp.recvfrom(frames_per_packet*local_freq*bytesPerFreq)

            if(packet != ''):

                print('Receiving UDP Packet...')
                data = np.fromstring(packet,dtype=np.dtype([('bin', 'i4',1), ('seq', 'i8',1), ('mask', 'f4',1)]))

                if(firstPacket):

                    t_min = datetime.datetime.utcnow()
                    min_seq = np.min(data['seq'])
                    max_seq = min_seq + (waterfall.shape[1]-1)*timesteps_per_frame
                    firstPacket = False

                else:

                    new_max = np.max(data['seq'])

                    if(new_max > max_seq):

                        roll_amount = int(-1*max((new_max-max_seq)/timesteps_per_frame,waterfall.shape[1]/8))

                        #DO THE ROLL
                        waterfall = np.roll(waterfall,roll_amount,axis=1)
                        waterfall[:,roll_amount:] = -1

                        #Adjust Times
                        min_seq += -1*roll_amount*timesteps_per_frame
                        max_seq += -1*roll_amount*timesteps_per_frame
                        t_min += datetime.timedelta(seconds=-1*roll_amount*timestep*timesteps_per_frame)

                waterfall[(data['bin']).astype(int),((data['seq']-min_seq)/timesteps_per_frame ).astype(int)] = data['mask']
                #print(data['bin'])

        elif (mode == 'chime'):

            #Receive packet from port
            packet, addr = sock_udp.recvfrom(chimePacketSize)


            if(packet != ''):

                if(packetCounter % 25*len(stream_dict) == 0):
                    print("Receiving Packets from %d Streams"%(len(stream_dict)))
                packetCounter += 1

                header = np.fromstring(packet[:chimeRFIHeaderSize],dtype=chimeHeaderDataType)
                data = np.fromstring(packet[chimeRFIHeaderSize:],dtype=np.float32)

                #Create a new stream object each time a new stream connects
                if(header['encoded_stream_ID'][0] not in stream_dict.keys()):

                    #Check that the new stream is providing the correct data
                    if(chimeHeaderCheck(header,app) == False):
                        break
                    #Add to the dictionary of Streams
                    stream_dict[header['encoded_stream_ID'][0]] = Stream(header)

                #On first packet received by any stream
                if(firstPacket):

                    #Set up waterfall parameters
                    t_min = datetime.datetime.utcnow()
                    min_seq = header['fpga_seq_num'][0]
                    max_seq = min_seq + (waterfall.shape[1] - 1)*timesteps_per_frame*frames_per_packet
                    firstPacket = False       

                else:

                    if(header['fpga_seq_num'][0] > max_seq):

                        roll_amount = int(-1*max((header['fpga_seq_num'][0]-max_seq)/(timesteps_per_frame*frames_per_packet),waterfall.shape[1]/8))
                        #If the roll is larger than the whole waterfall (kotekan dies and rejoins)
                        if(-1*roll_amount > waterfall.shape[1]):
                            #Reset Waterfall
                            t_min = datetime.datetime.utcnow()
                            waterfall[:,:] = -1
                            min_seq = header['fpga_seq_num'][0]
                            max_seq = min_seq + (waterfall.shape[1] - 1)*timesteps_per_frame*frames_per_packet
                        else:
                            #DO THE ROLL, Note: Roll Amount is negative
                            waterfall = np.roll(waterfall,roll_amount,axis=1)
                            waterfall[:,roll_amount:] = -1
                            min_seq -= roll_amount*timesteps_per_frame*frames_per_packet
                            max_seq -= roll_amount*timesteps_per_frame*frames_per_packet
                            #Adjust Time
                            t_min += datetime.timedelta(seconds=-1*roll_amount*timestep*timesteps_per_frame*frames_per_packet)

                waterfall[stream_dict[header['encoded_stream_ID'][0]].bins,int((header['fpga_seq_num'][0]-min_seq)/(timesteps_per_frame*frames_per_packet))] = data

        elif (mode == 'vdif'):

            packet, addr = sock_udp.recvfrom(vdifPacketSize)

            if(packet != ''):

                print('Receiving UDP Packet...')

                header = np.fromstring(packet[:vdifRFIHeaderSize],dtype=np.dtype([('combined_flag', np.uint8 ,1),
                    ('sk_step', np.int32,1), ('num_elements', np.int32,1),
                    ('num_times_per_frame', np.int32,1), ('num_freq', np.int32,1), ('seq', np.uint32 ,1)]))
                data = np.fromstring(packet[vdifRFIHeaderSize:],dtype=np.float32)
                print(header, data)
                if(firstPacket):

                    if(VDIFHeaderCheck(header,app) == False):
                        break
                    t_min = datetime.datetime.utcnow()
                    min_seq = header['seq']
                    max_seq = min_seq + (waterfall.shape[1] - 1)
                    firstPacket = False

                else:

                    if(header['seq'] > max_seq):

                        roll_amount = int(-1*waterfall.shape[1]/8)

                        #DO THE ROLL
                        waterfall = np.roll(waterfall,roll_amount,axis=1)
                        waterfall[:,roll_amount:] = -1
                        min_seq -= roll_amount
                        max_seq -= roll_amount

                        #Adjust Times
                        t_min += datetime.timedelta(seconds=-1*roll_amount*timestep*timesteps_per_frame)

                waterfall[:,int(header['seq']-min_seq)] = data

def TCP_stream():

    global sock_tcp, waterfall, t_min

    sock_tcp.listen(1)

    while True:

        conn, addr = sock_tcp.accept()
        print('Established Connection to %s:%s' %(addr[0],addr[1]))

        while True:

            MESSAGE = conn.recv(1).decode() #Client Message

            if not MESSAGE: break

            elif MESSAGE == "W":
                print("Sending Watefall Data %d ..."%(len(waterfall.tostring())))
                conn.send(waterfall.tostring())  #Send Watefall
            elif MESSAGE == "T":
                print("Sending Time Data ...")
                print(len(t_min.strftime('%d-%m-%YT%H:%M:%S:%f')))
                conn.send(t_min.strftime('%d-%m-%YT%H:%M:%S:%f').encode())  #Send Watefall
            print(MESSAGE)
        print("Closing Connection to %s:%s ..."%(addr[0],str(addr[1])))
        conn.close()

if( __name__ == '__main__'):

    app = CommandLine()

    #Intialize TCP
    TCP_IP= app.TCP_IP
    TCP_PORT = app.TCP_PORT
    sock_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock_tcp.bind((TCP_IP, TCP_PORT))

    #Intialize Time
    t_min = datetime.datetime.utcnow()

    #Initialize Plot
    nx, ny = app.config['waterfallY'], app.config['waterfallX']
    waterfall = -1*np.ones([nx,ny],dtype=float)

    time.sleep(1)

    receive_threads = []
    UDP_IP= app.UDP_IP
    for i in range(app.config['num_receive_threads']):
        UDP_PORT = app.UDP_PORT + i
        sock_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock_udp.bind((UDP_IP, UDP_PORT))
        receive_threads.append(threading.Thread(target=data_listener, args = (sock_udp,)))
        receive_threads[i].daemon = True
        receive_threads[i].start()

    thread2 = threading.Thread(target=TCP_stream)
    thread2.daemon = True
    thread2.start()

    input()


