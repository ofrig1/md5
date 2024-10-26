import socket
import threading
import logging
import protocol

LISTEN_SIZE = 5
SERVER_IP = 'localhost'
SERVER_PORT = 12345
NUM_OF_NUMS = 1000  # per core
HASH_TO_DECRYPT = 'a4ff94d8b38039a7db3d26437e7079ef'
START_NUM = 10000
RANGES = set()  # Store which ranges have been tried
TARGET_MD5 = HASH_TO_DECRYPT.lower()  # make sure hash is all lowercase letters
# global variables
unassigned_ranges = []  # Store ranges that need reassignment
client_sockets = []


def handle_client(server_socket, addr, range_lock):
    """
    Handle incoming client connection and assign work to attempt hash decryption
    :param range_lock: Thread lock object to synchronize range assignments among clients
    :param server_socket: socket object for the client connection
    :param addr: client address information
    :return:
    """
    global unassigned_ranges
    logging.info(f"Client {addr} connected.")
    protocol.protocol_send(TARGET_MD5, "MD5", server_socket)
    msg_type, num_cores = protocol.protocol_receive(server_socket)
    if msg_type != "COR":
        logging.error(f"Expected 'COR' but received '{msg_type}' from client {addr}. Disconnecting.")
        protocol.protocol_send("ERROR: Expected COR", "ERR", server_socket)
        server_socket.close()  # Close the connection to the client
        return

    logging.info(f"Client {addr} has {num_cores} cores.")
    try:
        while True:
            workload = int(NUM_OF_NUMS) * int(num_cores)
            with range_lock:
                if unassigned_ranges:
                    # Reassign an unfinished range if any are available
                    start, end = unassigned_ranges.pop(0)
                else:
                    # Assign a new range to the client
                    start = START_NUM + len(RANGES) * workload
                    end = start + workload
                    RANGES.add((start, end))
            if start > START_NUM*10:
                logging.info("No matching number found after exhausting search ranges.")
                break

            # Send the range to the client
            logging.info(f"Assigning range {start}-{end} to client {addr}.")
            protocol.protocol_send(f"{start}-{end}", "RNG", server_socket)

            # Wait for result from client
            msg_type, result = protocol.protocol_receive(server_socket)
            if msg_type != "RES":
                protocol.protocol_send("ERROR: Expected RES", "ERR", server_socket)
                logging.error("Expected RES")
                server_socket.close()  # Close the connection to the client
                return

            if result == "NOT FOUND":
                logging.info(f"Client {addr} did not find a valid string in the assigned range.")
                continue  # Go back to waiting for new connections
                # Check if the result is valid
            if isinstance(result, str) and len(result) == len(str(START_NUM)) and result.isdigit():
                logging.info(f"Client {addr} found valid number: {result}")
                # send a message to the client to let them disconnect
                broadcast_message('FOUND', "RES")
                break
            else:
                # This block handles any result that is not in the correct range
                logging.warning(f"Client {addr} found an invalid result: {result}")
                protocol.protocol_send("RESULT NOT VALID", "ERR", server_socket)

    except (ConnectionResetError, ValueError) as e:
        logging.warning(f"Client {addr} disconnected or error occurred: {e}")
        with range_lock:
            unassigned_ranges.append((start, end))  # Reassign unfinished range

    finally:
        server_socket.close()
        logging.info(f"Connection with client {addr} closed.")


def broadcast_message(message, msg_type):
    """
    Send message to all clients (in client_sockets)
    :param message: message to send
    :param msg_type: message type
    """
    global client_sockets
    for client in client_sockets[:]:  # Use a copy of the list to avoid modification issues
        try:
            protocol.protocol_send(message, msg_type, client)
        except Exception as e:
            logging.error(f"Failed to send message to a client: {e}")
            client_sockets.remove(client)  # Remove client if sending fails


def start_server():
    """
    Initialize and start the server, accepting client connections and spawning threads
    to handle each client
    """
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((SERVER_IP, SERVER_PORT))
    server.listen(LISTEN_SIZE)
    range_lock = threading.Lock()
    print("Server listening on port", SERVER_PORT)

    while True:
        server_socket, addr = server.accept()
        client_sockets.append(server_socket)
        client_thread = threading.Thread(target=handle_client, args=(server_socket, addr, range_lock))
        client_thread.start()


if __name__ == "__main__":
    logging.basicConfig(filename="server.log", level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s',)
    assert isinstance(NUM_OF_NUMS, int) and NUM_OF_NUMS > 0, "NUM_OF_NUMS must be a positive integer."
    assert isinstance(HASH_TO_DECRYPT, str) and len(
        HASH_TO_DECRYPT) == 32, "HASH_TO_DECRYPT must be a 32-character string."
    assert isinstance(START_NUM, int) and START_NUM > 0, "START_NUM must be a positive integer."
    start_server()
