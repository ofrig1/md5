import socket
import hashlib
import multiprocessing
import protocol
import logging

LISTEN_SIZE = 5
CLIENT_HOST = 'localhost'
CLIENT_PORT = 12345


def md5_hash(string):
    """
    Generate the MD5 hash of a given string
    :param string: The input string to hash
    :return: The MD5 hash of the input string
    """
    return hashlib.md5(string.encode()).hexdigest()


def brute_force_range(start, end, target_md5):
    """
    Attempt to find a string within a specified range that matches the target MD5 hash
    :param start: Starting integer of the range to test
    :param end: Ending integer of the range to test
    :param target_md5: The MD5 hash to match
    :return: The matching string if found; otherwise, None.
    """
    logging.debug(f"Starting brute-force from {start} to {end} for target MD5: {target_md5}")
    for i in range(start, end):
        string = str(i)
        if md5_hash(string) == target_md5:
            logging.info(f"Match found: {string} -> {target_md5}")
            return string
    logging.debug(f"No match found in range {start}-{end}")
    return None


def client_worker():
    """
    Connect to the server and request an MD5 hash to brute-force
    Attempts to brute-force the target hash by receiving and processing assigned ranges
    :return:
    """
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((CLIENT_HOST, CLIENT_PORT))
    logging.info("Connected to the server")

    num_cores = multiprocessing.cpu_count()
    logging.info(f"Client has {num_cores} cores, sending info to server")

    # Send the number of cores to the server
    protocol.protocol_send(str(num_cores), "COR", client)

    msg_type, target_md5 = protocol.protocol_receive(client)
    if msg_type == "ERR":
        logging.error("Received an error message from the server. Closing connection.")
        client.close()
        return
    if msg_type != "MD5":
        logging.error(f"Expected 'MD5', but received '{msg_type}'. Closing connection.")
        # client.send(b"ERROR: Expected MD5")  # Optionally send an error message back to the server
        client.close()
        return
    # target_md5 = client.recv(1024).decode()
    logging.info(f"Received target MD5 hash to brute-force: {target_md5}")

    while True:
        # Receive the range from the server
        # data = client.recv(1024).decode()
        msg_type, data = protocol.protocol_receive(client)
        if msg_type == "ERR":
            logging.error("Received an error message from the server. Closing connection.")
            client.close()
            return
        if msg_type != "RNG":
            logging.error(f"Expected 'RNG', but received '{msg_type}'. Closing connection.")
            client.close()
            return
        if data == "STOP":
            logging.info("Stopping work, answer was found by another client.")
            break

        start, end = map(int, data.split('-'))
        logging.info(f"Client working on range: {start}-{end}")

        # Brute force through the range
        result = brute_force_range(start, end, target_md5)

        if result:
            logging.info(f"Sending found result {result} to server.")
            protocol.protocol_send(result, "RES", client)
            # client.send(result.encode())
            break
        else:
            logging.debug("No result found in current range. Notifying server.")
            protocol.protocol_send("NOT FOUND", "RES", client)
            # client.send(b"NOT FOUND")  # Notify server if no match found in range

    client.close()
    logging.info("Connection to the server closed.")


if __name__ == "__main__":
    logging.basicConfig(filename="client.log", level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s',)
    assert isinstance(LISTEN_SIZE, int) and LISTEN_SIZE > 0, "LISTEN_SIZE must be a positive integer."
    assert isinstance(CLIENT_HOST, str) and CLIENT_HOST, "CLIENT_HOST must be a non-empty string."
    assert isinstance(CLIENT_PORT, int) and 1024 <= CLIENT_PORT <= 65535, "CLIENT_PORT must be between 1024 and 65535."
    assert callable(protocol.protocol_send), "protocol_send should be a callable function in protocol."
    assert callable(protocol.protocol_receive), "protocol_receive should be a callable function in protocol."
    client_worker()
