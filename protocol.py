import logging
import traceback

SEPERATOR = '|'

# types_send = cor\/, rng\/, md5\/, res


def protocol_receive(my_socket):
    """
    Receive message
    :param my_socket:
    :return:
    """
    final_message = ''
    msg_type = ''
    try:
        # Receive the first 3 characters for the msg_type
        for i in range(3):
            msg_type += my_socket.recv(1).decode()

        # Get the message length by reading characters until the separator
        cur_char = ''
        message_len = ''
        while cur_char != SEPERATOR:
            cur_char = my_socket.recv(1).decode()
            if cur_char != SEPERATOR:
                message_len += cur_char

        # Ensure we have a valid message length before proceeding
        if not message_len.isdigit():
            raise ValueError(f"Invalid message length: {message_len}")

        # Now read the actual message of length 'message_len'
        for i in range(int(message_len)):
            final_message += my_socket.recv(1).decode()

        # Return the msg_type and final_message separately
        return msg_type, final_message
    except ConnectionResetError as e:
        print(f"Connection was reset: {e}")
        raise
    except Exception as e:
        stack_trace = traceback.format_exc()
        print(stack_trace)
        print(f"Error: {e}. Server failed to receive client message")
        raise


def protocol_send(message, msg_type, my_socket):
    try:
        message_len = len(message)
        # Format the message according to the protocol
        final_message = f"{msg_type}{message_len}{SEPERATOR}{message}"
        # Send the message through the socket
        my_socket.send(final_message.encode())
    except Exception as e:
        logging.info(traceback.format_exc())
        print(f"Error: {e}. Client message failed to send to server with protocol")
