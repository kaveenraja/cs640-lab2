import argparse
import socket
import struct
import math
import os
import errno

from datetime import datetime
import time

parser = argparse.ArgumentParser(prog='sender',description='sets up a file packet sender on specified port')

parser.add_argument('-p', '--port')           #port is the port on which the sender waits for requests
parser.add_argument('-g', '--requester_port') #requester port is the port on which the requester is waiting
parser.add_argument('-r', '--rate')           #rate is the number of packets to be sent per second
parser.add_argument('-q', '--seq_no')         #seq_no is the initial sequence of the packet exchange
parser.add_argument('-l', '--length')         #length is the length of the payload (in bytes) in the packets

parser.add_argument('-f', '--f_hostname')     #hostname of the emulator
parser.add_argument('-e', '--f_port')         #port of the emulator
parser.add_argument('-i', '--priority')       #priority of sent packets
parser.add_argument('-t', '--timeout')        #timeout for lost packets in  milliseconds

args = parser.parse_args()

retrans = 0

sequence = 1
length = int(args.length)
rate = int(args.rate)
data_buffer = []

senip = socket.gethostbyname(socket.gethostname())
soc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
soc.bind((senip, int(args.port)))

req_packet, req_addr = soc.recvfrom(65565)

inner_header = struct.unpack("!cII", req_packet[17:26])

with open(req_packet[26:].decode(), "rb") as f:
    read_data = f.read()


for i in range(math.ceil(len(read_data)/length)):
    # Data, ack, # of retransmits
    data_buffer.append((read_data[i * length : (i+1) * length], 0, 0))

f.close()


# Checks to see if window ack/ max retransmits tried
def check_done(window, window_size):
    done = 1
    for i in range(window_size):

        if window * window_size + i == len(data_buffer):
            return 1

        if data_buffer[window * window_size + i][1] != 1 and  data_buffer[window * window_size + i][2] < 5 :
            return 0
    return 1

# Retransmits all unack packages
def retransmit(window, window_size):

    for i in range(window_size):

        if window * window_size + i == len(data_buffer):
            return

        if data_buffer[window * window_size + i][1] == 0:
            global retrans 
            retrans += 1

            data = data_buffer[window * window_size + i][0]
            data_buffer[window * window_size + i] = (data, 0, data_buffer[window * window_size + i][2] + 1)
            inner_header = struct.pack("!cII", 'D'.encode(), socket.htonl(window * window_size + i + 1), len(data))
            inner_packet = inner_header + data
                    
            outer_header = struct.pack("!B4sH4sHI", int(args.priority), socket.inet_aton(senip), int(args.port), socket.inet_aton(socket.gethostbyname(args.f_hostname)), int(args.f_port), len(inner_packet))
            packet = outer_header + inner_packet

            soc.sendto(packet, (socket.gethostbyname(args.f_hostname), int(args.f_port)) )
            print(window)

    return


def proc_ack(window, window_size):
    while 1:
        try:
            soc.settimeout(round(int(args.timeout) / 1000))
            ack_packet, ack_addr = soc.recvfrom(65565)
            inner_header = struct.unpack("!cII", ack_packet[17:26])

            if inner_header[0].decode() == 'A':
                data_buffer[socket.ntohl(inner_header[1])-1] = (data_buffer[socket.ntohl(inner_header[1])-1][0], 1, 0)

            if check_done(window, window_size):
                return
                    
        except:
            retransmit(window, window_size)
done = 1
window = 0
window_size = inner_header[2]

while done:
    # Transmit window
    for i in range(window_size):
        if window * window_size + i == len(data_buffer):
            done = 0
            break
        data = data_buffer[window * window_size + i][0]
        inner_header = struct.pack("!cII", 'D'.encode(), socket.htonl(sequence), len(data))
        inner_packet = inner_header + data
        
        outer_header = struct.pack("!B4sH4sHI", int(args.priority), socket.inet_aton(senip), int(args.port), socket.inet_aton(socket.gethostbyname(args.f_hostname)), int(args.f_port), len(inner_packet))
        packet = outer_header + inner_packet


        soc.sendto(packet, (socket.gethostbyname(args.f_hostname), int(args.f_port)) )
        sequence += 1

        time.sleep(1/int(args.rate))

    # Receive ack
    proc_ack(window, window_size)
   
    
    window += 1;




inner_header = struct.pack("!cII", 'E'.encode(), socket.htonl(sequence), 0)
    
outer_header = struct.pack("!B4sH4sHI", int(args.priority), socket.inet_aton(senip), int(args.port), socket.inet_aton(socket.gethostbyname(args.f_hostname)), int(args.f_port), len(inner_packet))
packet = outer_header + inner_header

soc.sendto(packet, (socket.gethostbyname(args.f_hostname), int(args.f_port)) )

