import queue
import threading
import serial
import time

JRD100_ERROR_CODES = {
    0x09: "Tag not within field or the specified EPC is incorrect",
    0x16: "Access password incorrect",
    0x10: "Tag not within field or the specified EPC is incorrect",
    0x15: "No tag received or the tag failed the CRC check"

}


class JRD100exception(Exception):
    def __init__(self, code, error_frame):
        self.code = code
        self.error_frame = error_frame
        self.description = JRD100_ERROR_CODES.get(code, "Unknown error please refer EPC Gen2 protocol error codes")
        super().__init__(self.description)

    def __str__(self):
        return (f'ERROR: {self.description}'
                f' CODE: {f"0x{self.code:02X}"}'
                f' FRAME: "{self.error_frame.hex(" ").upper()}"')


class reader():
    def __init__(self, port="COM9", baud_rate=115200, debug=False):
        self.port = port
        self.baud_rate = baud_rate
        self.ser = serial.Serial(self.port, self.baud_rate)
        time.sleep(2)
        self.debug = debug

        self.response_queue = queue.Queue()
        self.notification_queue = queue.Queue()
        self.error_queue = queue.Queue()

        self._running = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def _read_loop(self):
        buffer = bytearray()
        while self._running:
            b = self.ser.read(1)
            if not b:
                continue
            buffer.append(b[0])

            if b[0] == 0x7E:

                frame = bytes(buffer)
                buffer = bytearray()
                if self.debug:
                    print("Recv: ", frame.hex(' ').upper())
                if len(frame) >= 3 and frame[1] == 0x01 and frame[2] == 0xFF:
                    pl = (frame[3] << 8) | frame[4]
                    code = frame[5] if pl >= 1 else 0x00
                    err = JRD100exception(code, frame)
                    print(err)  # visible immediately, doesn't stop the thread
                    self.last_error = err  # also stashed for the user to inspect on demand
                    self.error_queue.put(frame)
                elif frame[1] == 0x02:
                    self.notification_queue.put(frame)
                else:
                    self.response_queue.put(frame)

    def _send(self, command):
        self.ser.write((command + "\n").encode())
        if self.debug:
            print("Sent: ", command)

    def _get_response(self, timeout=2, resp=True):
        try:
            error_frame = self.error_queue.get_nowait()
            print("done")
        except queue.Empty:
            error_frame = None
        if error_frame is not None:
            pl = (error_frame[3] << 8) | error_frame[4]
            code = error_frame[5] if pl >= 1 else 0x00
            raise JRD100exception(code, error_frame)

        target_queue = self.response_queue if resp else self.notification_queue
        try:
            return target_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def _frame_comm(self, command, parameter=None):
        if parameter:
            length = len(parameter.split())
            hex_len = f"{length:04X}"
            pl_msb = hex_len[0:2]
            pl_lsb = hex_len[2:4]

            comm = "00 " + command + " " + pl_msb + " " + pl_lsb + " " + parameter
        else:
            comm = "00 " + command + " 00 00"
        checksum = format(sum(bytearray.fromhex(comm)) % 256, "02X")
        final_command = "BB " + comm + " " + checksum + " 7E"
        return final_command

    def getSoftwareversion(self):
        """Get software version of the module"""
        try:
            final_comm = self._frame_comm(command="03", parameter="01")
            self._send(final_comm)
            frame = self._get_response(timeout=2)
            if frame is None:
                raise TimeoutError("No response from module")
            pl = (frame[3] << 8) | frame[4]
            data = frame[5:5 + pl]

            return data.decode("ascii", errors="ignore")
        except JRD100exception as e:
            print(e)
            return None

    def getHardwareversion(self):
        """Get hardware version of the module"""
        try:
            final_comm = self._frame_comm(command="03", parameter="00")
            self._send(final_comm)
            frame = self._get_response(timeout=2)
            if frame is None:
                raise TimeoutError("No response from module")
            pl = (frame[3] << 8) | frame[4]
            data = frame[5:5 + pl]
        except JRD100exception as e:
            print(e)
            return None

            return data.decode("ascii", errors="ignore")

    def getManufacturer(self):
        """Get manufacturer of the module"""
        try:
            final_comm = self._frame_comm(command="03", parameter="02")
            self._send(final_comm)
            frame = self._get_response(timeout=2)
            if frame is None:
                raise TimeoutError("No response from module")
            pl = (frame[3] << 8) | frame[4]
            data = frame[5:5 + pl]

            return data.decode("ascii", errors="ignore")
        except JRD100exception as e:
            print(e)
            return None

    def SinglePoll(self):
        """Single poll command"""
        try:
            final_comm = self._frame_comm(command="22")
            self._send(final_comm)
            frame = self._get_response(timeout=2, resp=False)
            if frame is None:
                raise TimeoutError("No response from module")

            tag_data = self._construct_data(frame)
            return tag_data


        except (JRD100exception, TimeoutError) as e:
            print(e)
            return None

    def MultiPoll(self, polls=100):
        """Multi polll command ; default polls:100"""
        msb = f" {(polls >> 8) & 0xFF:02X}"
        lsb = f" {(polls & 0xFF):02X}"
        param = "22" + msb + lsb
        print(param)
        final_comm = self._frame_comm(command="27", parameter=param)
        self._send(final_comm)
        print(final_comm)

    def StopPoll(self):
        """Immediately Stop Multi poll command, Not a pause command"""
        final_comm = self._frame_comm(command="28")
        return None

    def _construct_data(self, frame):
        pl = (frame[3] << 8) | frame[4]
        data = frame[5:5 + pl]
        # return data
        hex_str = data.upper()
        pc = (frame[6] << 8) | frame[7]
        size = ((pc >> 11) & 0x1F) * 2  # size in bytes "1 word=2 bytes"
        rssi = frame[5]  # formula needed to compute exact strength
        epc = frame[8:8 + size].hex().upper()
        crc = f"0x{(frame[8 + size] << 8) | frame[8 + size + 1]:04X}"

        return {
            "epc": epc,
            "rssi": rssi,
            "pc": f"0x{pc:04X}",
            "crc": crc,
            "EPCsize": size
        }

    def stream_tags(self, timeout=1):
        """
        Yields the received value continuously.
        Waits for  upto "timeout" seconds for a new frame.
        Runs continuously until you break the loop or call StopPoll()

        Basic usage:
        for tag in reader1.stream_tags():
            print(tag)

        """

        while True:
            try:
                frame = self.notification_queue.get(timeout=timeout)
            except queue.Empty:
                continue
            try:
                yield self._construct_data(frame)
            except (IndexError, ValueError) as e:
                print(f"Unable to construct frame {frame.hex(' ').upper()}: {e}")
                continue
            except (JRD100exception, TimeoutError) as e:
                print(e)
                return None

    def getTransmitPower(self):
        """
        Returns transmit power. in dBm
        :return:Power in dBm
        :raises: TimeoutError if no response from module
        """
        try:
            final_comm = self._frame_comm(command="B7")
            self._send(final_comm)
            frame = self._get_response(timeout=2)
            if frame is None:
                raise TimeoutError("No response from module")
            power = (frame[5] << 8) | frame[6]
            return power
        except TimeoutError as e:
            print(e)
            return None
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None


    def setTransmitPower(self, power=2500):
        """
        Sets transmit power.
        :param power:
        :return: None
            """
        try:
            param = f"{(power >> 8) & 0xFF:02X}" + f" {power & 0xFF:02X}"
            final_comm = self._frame_comm(command="B6", parameter=param)
            self._send(final_comm)
            frame = self._get_response(timeout=2)
            if frame is None:
                raise TimeoutError("No response from module")
            if frame[5] == 0x00:
                print(f"Transmit power set to: {power} dBm ")
        except TimeoutError as e:
            print(e)
            return None
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None

    def getSelectParam(self):
        """
        Gets select parameter values.
        :return: A dict containing all the decoded parameters
        """
        try:
            final_comm = self._frame_comm(command="0B")
            self._send(final_comm)
            frame = self._get_response(timeout=2, resp=True)

            if frame is None:
                raise TimeoutError("No response from module")

            pl = (frame[3] << 8) | frame[4]
            data = frame[5:5 + pl]

            selparam_byte = data[0]
            target = (selparam_byte >> 5) & 0x07
            action = (selparam_byte >> 2) & 0x07
            membank = selparam_byte & 0x03

            ptr = (data[1] << 24) | (data[2] << 16) | (data[3] << 8) | data[4]

            mask_len_bits = data[5]

            truncate = data[6]

            mask_len_bytes = (mask_len_bits + 7) // 8
            mask = data[7:7 + mask_len_bytes]

            return {
                "target": target,
                "action": action,
                "membank": membank,
                "ptr": ptr,
                "mask_len_bits": mask_len_bits,
                "truncate": truncate,
                "mask": mask.hex().upper(),
            }
        except TimeoutError as e:
            print(e)
            return None
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None

    def setSelectParam(self, mask, membank=0x01, ptr=0x00000020, target=0x00, action=0x00, truncate=0x00):
        """
        mask: hex string of the EPC/data to filter on, e.g. "E200470... "
        membank: 0x00=RFU, 0x01=EPC, 0x02=TID, 0x03=User
        ptr: bit offset to start comparing from (default 0x20 = right after CRC+PC)
        target: 0x00-0x04 (which session/flag this Select affects)
        action: 0x00-0x07 (what happens to matching vs non-matching tags)
        truncate: 0x00=disabled, 0x80=enabled
        """
        try:
            mask_bytes = bytes.fromhex(mask.replace(" ", ""))
            mask_len_bits = len(mask_bytes) * 8

            selparam_byte = ((target & 0x07) << 5) | ((action & 0x07) << 2) | (membank & 0x03)

            ptr_bytes = bytes([
                (ptr >> 24) & 0xFF,
                (ptr >> 16) & 0xFF,
                (ptr >> 8) & 0xFF,
                ptr & 0xFF,
            ])
            params = (
                    bytes([selparam_byte]) +
                    ptr_bytes +
                    bytes([mask_len_bits]) +
                    bytes([truncate]) +
                    mask_bytes)
            params1 = params.hex(" ").upper()
            final_comm = self._frame_comm(command="0C", parameter=params1)
            self._send(final_comm)
            frame = self._get_response(timeout=2, resp=True)
            if frame is None:
                raise TimeoutError("No response from module")
            elif frame[5] == 0x00:
                print(f"Successfully applied mask {mask}")
        except TimeoutError as e:
            print(e)
            return None
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None

    def setSelectMode(self, mode=0):
        """
        Modes:(0,1,2)
            0: Send command before every tag operation to select a specific tag
            1:Do not send Select command(Cancel select command)
            2:Send select command before operations other than polling inventory
        :param mode:
        :return:
        """
        try:
            final_comm = self._frame_comm(command="12", parameter=f"{mode:02X}")
            self._send(final_comm)
            frame = self._get_response(timeout=2, resp=True)
            if frame is None:
                raise TimeoutError("No response from module")
            elif frame[5] == 0x00:
                print("Select parameter set")
        except TimeoutError as e:
            print(e)
            return None
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None

    def readTagMemoryArea(self, membank=1, access_password="00 00 00 00", start_offset=0, data_length=2):
        """Read tag memory area from specific bank

        membank: 0=RFU, 1=EPC, 2=TID, 3=User (default=1)
        access_password: Tag access password in hex signed 2's complement (default=00 00 00 00)
        start_offset: Start offset in words (default=0)
        data_length: Data length in words (default=2)
        note: 1 word = 2 bytes
"""
        try:
            final_comm = self._frame_comm(command="0B")
            self._send(final_comm)
            frame1 = self._get_response(timeout=2, resp=True)

            if frame1 is None:
                raise TimeoutError("No response from module")
            elif frame1[10] == 0x00:
                raise Exception("Please SET SELECT PARAMETER before using read/write bank operations")

            param = access_password + " " + f"{membank:02X}" + " " + f"{(start_offset >> 8) & 0xFF:02X}" + f" {start_offset & 0xFF:02X}" + f" {(data_length >> 8) & 0xFF:02X}" + f" {data_length & 0xFF:02X}"
            final_comm1 = self._frame_comm(command="39", parameter=param)
            # print(final_comm)
            self._send(final_comm1)
            frame = self._get_response(timeout=2, resp=True)

            if frame is None:
                raise TimeoutError("No response from module")
            pl = (frame[3] << 8) | frame[4]
            pc = (frame[6] << 8) | frame[7]
            epcsize = ((pc >> 11) & 0x1F) * 2  # size in bytes "1 word=2 bytes"
            epc = frame[8:8 + epcsize].hex(" ").upper()
            data = frame[8 + epcsize:-2].hex(" ").upper()

            return {"pc": pc,
                    "EPC": epc,
                    "EPCsize": epcsize,
                    "data": data,
                    "pl": pl}
        except TimeoutError as e:
            print(e)
            return None


reader1 = reader(debug=True)
reader1.setSelectParam("A001")
dat = reader1.readTagMemoryArea(membank=2, data_length=3)
print(dat)

