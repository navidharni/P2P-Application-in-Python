# peer.py
"""
A P2P client
It provides the following functions:
- Register the content file to the index server (R)
- Contact the index server to search for a content file (D)
    - Contact the peer to download the file
    - Register the content file to the index server
- De-register a content file (T)
- List the local registered content files (L)
- List the on-line registered content files (O)
"""
import socket  # Import socket module
from collections import namedtuple
import select
import pickle
import os
import sys
import time

BUFFER_SIZE = 100
# define the PDU
PDU = namedtuple('PDU', ['data_type', 'data'])

# Define the socket
s = socket.socket(socket.SOCK_DGRAM)  # Create a socket object
host = socket.gethostname()  # Get local machine name
port = 60000  # Reserve a port for your service.

# client is connected to the server
s.connect((host, port))

################## Functions ##################

def select_name():
    return input('Please enter preferred username:')

# File registration w/ Index Server
def register(username,content_name,address):
    # Create an R-Type PDU.
    r_pdu = PDU('R', {'peer_name': username, 'file_name': content_name, 'address': address})

    # Convert R-Type PDU (namedtuple) to byte stream and send to index server.
    r_pdu = pickle.dumps(r_pdu)
    print("Sending register request to index server...")
    s.send(r_pdu)

    # Receive PDU from index server and decode it.
    a_pdu = nt_assmbld(s)

    # Look for the acknowledgement and handle errors
    data_type = a_pdu.data_type
    data = a_pdu.data
    if 'E' in data_type:
        # Attempt a re-register with another peer name
        print(data)
        if data == {'msg':'You have already registered this file.'}:
            print('Wrong Selection')
        else:
            new_peer_name = select_name()
            register(new_peer_name, content_name,address)
    elif 'A' in data_type:
        print(data)

# File De-registration w/ Index Server
def de_register(username, filename):
    # Create the 'T' type PDU
    t_data = {'peer_name': username, 'file_name': filename,'address':(host,serverPort)}
    t_pdu = PDU(data_type='T', data=t_data)
    t_pdu = pickle.dumps(t_pdu)

    # Send 'T' PDU
    s.send(t_pdu)

    # Receive acknowledgement status from the index server
    a_pdu = nt_assmbld(s)

    data_type = a_pdu.data_type
    data = a_pdu.data

    # Handle errors
    if 'A' in data_type:
        print(data)
    else:
        print(data)

# File download from Peer
def download_file(filename, address):
    # establish new TCP connection
    connect_peer = socket.socket()
    connect_peer.connect(address)
    # Create a D-Type PDU to request a download
    d_pdu = PDU('D', filename)
    d_pdu = pickle.dumps(d_pdu)
    # Send D-Type PDU to the content server (peer)
    connect_peer.send(d_pdu)

    # Receive the data (should be C-Type PDU) and write it to the file
    f = open('dwnld_file_{}_{}'.format(username, filename), 'wb')
    while True:
        content_load = nt_assmbld(connect_peer)
        print("Received Content Load:")
        print(content_load)
        data_type = content_load.data_type
        data = content_load.data
        if 'C' in data_type:
            print(data)
            f.write(data)
        elif 'E' in data_type:
            error_message = data
            print(error_message)
            break
        print(len(content_load.data))
        if len(content_load.data)<99:
            break
    f.close()
    if 'C'in data_type:
        print('File Downloaded.')
        # Register content to the index server.
        register(username, filename, address)
    else:
        print('No such file existed at content server.')
    print("Closing TCP connection with peer...")
    connect_peer.close()

# Function to assemble and forward complete PDU's
def nt_assmbld(socket):
    temp = []
    flag = True
    pkt = socket.recv(BUFFER_SIZE)
    pdu = []
    while flag:
        temp.append(pkt)
        binary_pdu = (b"".join(temp))
        try:
            # convert pdu from binary to pdu object using pickle
            pdu = pickle.loads(binary_pdu)
            flag = False
        except:
            pkt = socket.recv(100)
            flag = True
    return pdu
###############################################

# select username
username = select_name()

# create a server to listen to the file requests
"""
Here we config the server capability of the peers. As a server we need to specify ip address and ports. Since all the 
peers are inside the local network (IP=127.0.0.1), we need to use unique port numbers for each peers so they can
bind socket successfully. This can be done by generating random numbers and using try/except command to bind a socket.
Withing multiple attempt we can be sure that peer would eventually bind a socket with random port number. Here I do not
use this approach. Instead I asked the user to enter a port number manually. During the test, for each of the peers,
you will need to enter different port numbers for different peers. 
The '' for IP address means our server is listening to all IPs,
you can change it to socket.hostname instead like before.
"""
inputs = []
outputs = []
exp = []
ss = socket.socket()  # TCP connection
host = socket.gethostname()
serverPort = int(input("Please enter listening port number for the download server: "))

try:
    ss.bind(('', serverPort))
except Exception:
    print("[Warning] Port unavailable...")

ss.listen(5)
print('listening on port', serverPort)
inputs.append(ss)
exp.append(ss)
print(inputs)

# service loop
while True:
    # When readable is empty (No incoming connection request), go to peer menu.
    # Allowing the peer to execute some commands.
    command = str(input('Please choose from the list below:\n'
                            '[O] Get online list\n'
                            '[L] List local files\n'
                            '[R] Register a file\n'
                            '[T] De-register a file\n'
                            '[Q] Quit the program\n'))

    if command == 'O':
        # Create 'O' type PDU
        o_pdu = PDU(data_type='O', data={'msg': 'Requesting online list.'})
        # Convert PDU to binary
        o_binary_pdu = pickle.dumps(o_pdu)
        # Send 'O' type PDU using (UDP)
        s.send(o_binary_pdu)
        print("Requesting online files list from index server...")

        # Receive the online files list
        o_received_pdu = nt_assmbld(s)
        online_files_list = o_received_pdu.data

        # Print the list
        print("List of all online files:")
        print(online_files_list)

        # Ask user for the target file
        filename = str(input("If you would like to download one of these files, please enter its name: "))

        # Create 'S' type PDU
        s_pdu = PDU('S', {'file_name': filename})
        s_pdu = pickle.dumps(s_pdu)
        # Send 'S' type PDU to the index server
        s.send(s_pdu)
        print("Requesting file to download...")

        # Receive 'S' PDU in response
        s_received_pdu = nt_assmbld(s)
        # Extract peer address
        data = s_received_pdu.data
        data_type = s_received_pdu.data_type

        # Check if any errors were received
        if 'E' in data_type:
            print(data)
        else:
            print("Attempting to download from: ", data)
            # Establish new connection with the peer and download the file from them
            download_file(filename, data)

    if command == 'L':
        # List local files
        local_files = [f for f in os.listdir('.') if os.path.isfile(f)]
        print("Local files:\n")
        print(local_files)

    if command == 'R':
        content_name = str(input("Enter the name of the file you would like to register: "))
        register(username, content_name, (host, serverPort))

    if command == 'T':
        # Get the file name from user
        filename = str(input("Please enter the name of the file you would like to de-register: "))
        de_register(username, filename)

    if command == 'Q':
        # Execute option [O] to obtain a list of files online files.
        # user_online_list = files assigned to the username.
        o_pdu = PDU('O', '')
        o_pdu = pickle.dumps(o_pdu)
        # Send 'O' type PDU using (UDP)
        s.send(o_pdu)

        # Receive the online files list
        o_received_pdu = s.recv(BUFFER_SIZE)
        o_received_pdu = pickle.loads(o_received_pdu)
        online_files_list = o_received_pdu.data
        # for file in user_online_list:
        for file in online_files_list:
            de_register(username,file[1])
        # Exit program with code 0 (successful exit).
        print("Terminating the Peer program")
        exit(0)

    timeout = 15
    print("Peer will listen to any connection request for {} seconds".format(timeout))

    readable, writable, exceptional = select.select(inputs, outputs, exp, timeout)
    # Check the incoming connection requests using readable.
    for sock in readable:
        # If a request exists, process the connection.
        if sock is ss:
            fileReq_Socket, fileReq_addr = ss.accept()  # Accept connection
            print(fileReq_addr)
            # ss.recv(BUFFER_SIZE)   # Receive the 'D' PDU
            b_pdu = fileReq_Socket.recv(BUFFER_SIZE)
            d_pdu = pickle.loads(b_pdu)
            print(d_pdu)
            data_type = d_pdu.data_type
            file_name = d_pdu.data
            # Check the file name (it should be 'D' type)
            if data_type == 'D':
                print("A file requested from: ")
                print(fileReq_addr)
                # In the same folder or path is this file running must the file you want to transfer to be
                if os.path.isfile(file_name):
                    with open(file_name, 'rb') as f:
                        load = f.read(99)
                        while load != b'':
                            # Send the file using 'C' type
                            c_pdu = PDU('C', load)
                            b_pdu = pickle.dumps(c_pdu)
                            fileReq_Socket.send(b_pdu)
                            time.sleep(1)
                            load = f.read(99)
                # else if file doest not exist send 'E' pdu
                else:
                    e_pdu = PDU('E', {'msg': 'File does not exist.'})
                    b_pdu = pickle.dumps(e_pdu)
                    fileReq_Socket.send(b_pdu)
            fileReq_Socket.close()

    print("Running Peer menu...")