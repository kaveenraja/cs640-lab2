import argparse
import socket
import struct

import time
from datetime import datetime

#Args
parser = argparse.ArgumentParser(prog='sender',description='sets up a file packet sender on specified port')

parser.add_argument('-p', '--port')         #port is the port on which the requester  waits for packets
parser.add_argument('-o', '--file_option')  #file_option is the name of the file that is being requested
parser.add_argument('-f', '--f_hostname')   #hostname of the emulator
parser.add_argument('-e', '--f_port')       #port of the emulator
parser.add_argument('-w', '--window')       #requester window size
args = parser.parse_args()


# Socket set up
reqip = socket.gethostbyname(socket.gethostname())
soc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
soc.bind((reqip, int(args.port)))


#Open file
requests = []
file = open("tracker.txt", "r")

for line in file:
    if args.file_option in line:
        requests.append(line.split(" "))

requests.sort(key=lambda x: x[1])


def proc_req(packet, filename, hostname, port):
    data_buffer = []

    soc.sendto(packet, (args.f_hostname, int(args.f_port)))

    
    while 1:
        
        sen_packet, sen_addr = soc.recvfrom(65565)
        emulator_header = struct.unpack("!B4sH4sHI", sen_packet[0:17])

        # Incoming packet incorrect dst in header
        if socket.inet_ntoa(emulator_header[3]) != reqip:
            continue
        

        inner_packet = sen_packet[17:]
        udp_header = struct.unpack("!cII", inner_packet[0:9])
        sequence = socket.ntohl(udp_header[1])

        if udp_header[0].decode() == 'E':
            break
       

        try:
            data_buffer[sequence] = inner_packet[9:9 + udp_header[2]].decode()
        except:
            data_buffer.insert(sequence, inner_packet[9:9 + udp_header[2]].decode())
        
        # Send ack packet
        ack_inner_header = struct.pack("!cII", 'A'.encode(), udp_header[1], 0)
        ack_inner_packet = ack_inner_header
        
        ack_outer_header = struct.pack("!B4sH4sHI", 0x01, socket.inet_aton(reqip), int(args.port), socket.inet_aton(socket.gethostbyname(hostname)), port, len(ack_inner_packet))
        ack_outer_packet = ack_outer_header + ack_inner_packet

        soc.sendto(ack_outer_packet, (socket.gethostbyname(args.f_hostname), int(args.f_port)) )

    f = open(filename, "a+")
    for buffer in data_buffer:
        f.write(buffer)

    f.close()


for request in requests:
    #Inner packet
    udp_header = struct.pack("!cII", 'R'.encode(), 0, int(args.window))
    inner_packet = udp_header + request[0].encode()

    #Outer packet
    emulator_header = struct.pack("!B4sH4sHI", 0x01, socket.inet_aton(reqip), int(args.port), socket.inet_aton(socket.gethostbyname(request[2])), int(request[3]), len(inner_packet))
    outer_packet = emulator_header + inner_packet

    proc_req(outer_packet, request[0], request[2], int(request[3]))

    













