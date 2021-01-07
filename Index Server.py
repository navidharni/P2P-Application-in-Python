# index_server.py
'''
Index Server
Message types:
R - used for registration
A - used by the server to acknowledge the success
Q - used by chat users for de-registration
D - download content between peers (not used here)
C - Content (not used here)
S - Search content
E - Error messages from the Server
'''

import socket  # Import socket module
from collections import namedtuple
import pickle
from _thread import *


port = 60000        # Reserve a port for your service.
THREAD_COUNT = 0
BUFFER_SIZE = 100


def threaded (conn):
    # receiving the binary_pdu = conn.recv(100)
    while True:
        data = []
        flag = True
        packet = conn.recv(BUFFER_SIZE)
        while flag:
            data.append(packet)
            binary_pdu = (b"".join(data))
            try:
                # convert pdu from binary to pdu object using pickle
                pdu = pickle.loads(binary_pdu)
                flag = False
            except:
                # if the PDU received was not complete, receive another packet.
                packet = conn.recv(BUFFER_SIZE)
                flag = True
        print("Request from peer: ")
        print(pdu)

        # extract the type from pdu, type = pdu.data_type
        data_type = pdu.data_type  # check data_type

        # if 'R'
        if data_type == 'R':
            data = pdu.data
            p_peer_name = data.get('peer_name')
            p_file_name = data.get('file_name')
            p_peer_address = data.get('address')
            # check list of files
            file_exist = False
            for i in fList:
                if i.peer_name == p_peer_name and i.file_name == p_file_name:
                    # send 'E' type pdu
                    e_pdu = PDU('E', {'msg': 'File already exist for this peer name. Choose another peer name.'})
                    if i.address == p_peer_address:
                        e_pdu =PDU('E',{'msg':'You have already registered this file.'})
                    b_pdu = pickle.dumps(e_pdu)
                    conn.send(b_pdu)
                    file_exist = True
                    break
            # if file does not already exist (new)
            if not file_exist:
                # create new Files_List object and add it to file list
                fList.append(Files_List(p_peer_name, p_file_name, p_peer_address))
                # send 'A' type pdu
                a_pdu = PDU('A', {'msg': f'Successfully registered the file: {p_file_name}'})
                b_pdu = pickle.dumps(a_pdu)
                conn.send(b_pdu)

        # else if 'T'
        elif data_type == 'T':
            data = pdu.data
            p_peer_name = data.get('peer_name')
            p_file_name = data.get('file_name')
            p_peer_address = data.get('address')

            # File requested to be removed
            fileToRemove = Files_List(p_peer_name, p_file_name, p_peer_address)
            print(fileToRemove)
            print('flist:')
            print(fList)
            try:
                # remove the file from list
                fList.remove(fileToRemove)
                # if removed successfully send 'A'
                a_pdu = PDU('A', {'msg': f'Successfully De-Registered the file: {p_file_name}'})
                b_pdu = pickle.dumps(a_pdu)
                conn.send(b_pdu)
            except:
                # if file does not exist send 'E'
                e_pdu = PDU('E', {'msg': 'File does not exist. Nothing Removed.'})
                b_pdu = pickle.dumps(e_pdu)
                conn.send(b_pdu)

        # else if 'S'
        elif data_type == 'S':
            data = pdu.data
            p_file_name = data.get('file_name')

            content_located = False
            all_locations =[]
            # check the fList
            for i in fList:
                if i.file_name == p_file_name:
                    # Send the newest registered peer for the requested file
                    target = i.address
                    content_located = True

            # if the file exists, send the address
            if content_located:
                pdu = PDU('S', target)
                b_pdu = pickle.dumps(pdu)
                conn.send(b_pdu)
            else:
                # else send 'E' pdu
                e_pdu = PDU('E', {'msg': 'File does not exist or It already registered for this peer.'})
                b_pdu = pickle.dumps(e_pdu)
                conn.send(b_pdu)

        # else if 'O'
        elif data_type == 'O':
            content_list = []
            # iterate through the fList
            for i in fList:
                # create a list of files
                content_list.append((i.peer_name, i.file_name))
            pdu = PDU('O', content_list)
            b_pdu = pickle.dumps(pdu)
            # send the 'O' pdu, data is the list
            conn.send(b_pdu)

        print('Done sending')

s = socket.socket(socket.SOCK_DGRAM)  # Create a socket object
host = socket.gethostname()  # Get local machine name
s.bind((host, port))  # Bind to the port
s.listen(5)  # Now wait for client connection.

# server is up and listening
print('Server listening on port', port)

# Define the named tuples required
PDU = namedtuple('PDU', ['data_type', 'data'])
Files_List = namedtuple('Files_List', ['peer_name', 'file_name', 'address'])
# list of files, containing Files_List named tuples
fList = []

while True:

    conn, addr = s.accept()  # Establish connection with client.
    print(addr)

    # Start a new thread
    start_new_thread(threaded, (conn, ))

