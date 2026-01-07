#!/usr/bin/env python3
"""pysof0273.sof0273 - SOF0273 device utilities"""
import argparse
import struct
import sys
import threading

import serial


class SOF0273:
    """
    Class to configure DOS0157 attenuators
    """

    MAGIC_NUMBER = 0xAA55
    READ_CODE = 0x01
    WRITE_CODE = 0x02
    SAVE_CODE = 0x08
    FRM = {
        READ_CODE: {"CMD": ">HBH", "ACK": ">HBBBH", "TYPE_str": "Read"},
        WRITE_CODE: {"CMD": ">HBBBH", "ACK": ">HBBBH", "TYPE_str": "Write"},
        SAVE_CODE: {"CMD": ">HBH", "ACK": ">HBBBH", "TYPE_str": "Save"},
    }
    FRM_MAX_LEN = 10

    def __init__(self, port, baudrate=9600, parity="N", stopbits=1):
        self.port = port
        self.baudrate = baudrate
        # parity: one of 'N','E','O','M','S' (None, Even, Odd, Mark, Space)
        self.parity = (parity or "N").upper()
        # stopbits: 1, 1.5 or 2
        try:
            self.stopbits = float(stopbits)
        except Exception:
            self.stopbits = 1.0
        self.serial_connection = None
        self.running = False

    @staticmethod
    def calcul_crc_16(buffer_crc_16: bytes, taille_calcul_crc_16: int) -> int:
        """
        Calculates CRC-16 (Modbus) over the
        first taille_calcul_crc_16 bytes of buffer_crc_16.
        """
        polynome_generateur_crc = 0xA001
        resultat_crc_16 = 0xFFFF  # initialisation du CRC16
        for i in range(taille_calcul_crc_16):
            resultat_crc_16 ^= buffer_crc_16[i]
            for _ in range(8):
                if (resultat_crc_16 & 0x01) == 1:
                    resultat_crc_16 >>= 1
                    resultat_crc_16 ^= polynome_generateur_crc
                else:
                    resultat_crc_16 >>= 1
        return resultat_crc_16 & 0xFFFF  # garantir un résultat sur 16 bits

    @staticmethod
    def att_2_code(att: float) -> int:
        """Converts attenuation in dB to device-specific code."""
        assert att >= 0.0 and att <= 31.5, "Attenuation must be between 0.0 and 31.5 dB"
        code = int(att * 2)  # Each step is 0.5 dB
        return code

    @staticmethod
    def code_2_att(code: int) -> float:
        """Converts device-specific code to attenuation in dB."""
        assert code >= 0 and code <= 63, "Code must be between 0 and 63"
        att = code / 2.0  # Each step is 0.5 dB
        return att

    def encode_protocol(self, command: str) -> bytes:
        """Dedicated function for protocol encoding."""
        match command[0].lower():
            case "r":
                code = self.READ_CODE
                args = ()

            case "w":
                code = self.WRITE_CODE
                args = command.split()
                if len(args) != 3:
                    print(
                        "Write command requires 2 arguments: Att_LOFAR and Att_NenuFAR.",
                        file=sys.stderr,
                    )
                    return b""
                try:
                    Att_LOFAR = self.att_2_code(float(args[1]))
                    Att_NenuFAR = self.att_2_code(float(args[2]))
                except ValueError:
                    print(
                        "Att_LOFAR and Att_NenuFAR must be floats between 0.0 and 31.5 dB.",
                        file=sys.stderr,
                    )
                    return b""
                args = (Att_LOFAR, Att_NenuFAR)

            case "s":
                code = self.SAVE_CODE
                args = ()

            case _:
                print("Unknown command. Use 'r', 'w', or 's'.", file=sys.stderr)
                return b""

        frame = struct.pack(
            self.FRM[code]["CMD"], self.MAGIC_NUMBER, code, *args, 0
        )  # Placeholder for CRC
        crc = self.calcul_crc_16(frame, len(frame) - 2)
        frame = struct.pack(self.FRM[code]["CMD"], self.MAGIC_NUMBER, code, *args, crc)
        return frame

    def decode_protocol(self, frame: bytes) -> str:
        """Dedicated function for protocol decoding."""
        try:
            if len(frame) < 4:
                return "Incomplete data received."
            magic, code = struct.unpack(">HB", frame[:3])
            if magic != self.MAGIC_NUMBER:
                return "Invalid magic number."
            if code not in self.FRM.keys():
                return "Unknown response code."
            else:
                _, _, att_lofar_code, att_nenufar_code, received_crc = struct.unpack(
                    self.FRM[code]["ACK"], frame
                )
                att_lofar = self.code_2_att(att_lofar_code)
                att_nenufar = self.code_2_att(att_nenufar_code)
                # Check CRC
                calculated_crc = self.calcul_crc_16(frame, len(frame) - 2)
                if calculated_crc != received_crc:
                    print(
                        f"CRC check failed : received {received_crc}, computed {calculated_crc}",
                        file=sys.stderr,
                    )
                    raise ValueError
                return f"{self.FRM[code]['TYPE_str']} Ack - Att_LOFAR: {att_lofar} dB, Att_NenuFAR: {att_nenufar} dB\n"
        except Exception:
            return "Exception in decode_protocol: " + repr(frame)

    def read_serial(self):
        """Continuously reads data from the serial port and prints it."""
        while self.running:
            try:
                if self.serial_connection.in_waiting:
                    data = self.serial_connection.read(self.FRM_MAX_LEN)
                    # print("Received raw data:", data)
                    decoded = self.decode_protocol(data)
                    print(decoded, end="> ", flush=True)
            except serial.SerialException as e:
                print(f"\n[SERIAL ERROR] {e}", file=sys.stderr)
                break
            except Exception as e:
                print(f"Read error: {e}", file=sys.stderr)
                break

    def start(self):
        """Starts the serial connection and the reading thread."""
        try:
            # Map parity and stopbits to pyserial constants with validation
            parity_map = {
                "N": serial.PARITY_NONE,
                "E": serial.PARITY_EVEN,
                "O": serial.PARITY_ODD,
                "M": serial.PARITY_MARK,
                "S": serial.PARITY_SPACE,
            }
            stopbits_map = {
                1.0: serial.STOPBITS_ONE,
                1.5: serial.STOPBITS_ONE_POINT_FIVE,
                2.0: serial.STOPBITS_TWO,
            }

            parity_val = parity_map.get(self.parity, serial.PARITY_NONE)
            if self.parity not in parity_map:
                print(
                    f"Warning: unknown parity '{self.parity}', defaulting to 'N'",
                    file=sys.stderr,
                )

            stopbits_val = stopbits_map.get(self.stopbits, serial.STOPBITS_ONE)
            if self.stopbits not in stopbits_map:
                print(
                    f"Warning: unknown stopbits '{self.stopbits}', defaulting to 1",
                    file=sys.stderr,
                )

            self.serial_connection = serial.Serial(
                self.port,
                self.baudrate,
                parity=parity_val,
                stopbits=stopbits_val,
                timeout=0.1,
            )
            self.running = True
            print(
                f"Connected to {self.port} at {self.baudrate} baud."
                f" Parity={self.parity} Stopbits={self.stopbits}"
            )
            print(
                "Enter commands to send to the device."
                "Commands:\n"
                "  r                           - Read current attenuation settings\n"
                "  w <Att_LOFAR> <Att_NenuFAR> - Set attenuation in dB (0.0 to 31.5)\n"
                "  s                           - Save current settings to device memory\n"
            )
            print("Type 'quit' to exit.\n")

            # Start the reading thread
            reader_thread = threading.Thread(target=self.read_serial)
            reader_thread.daemon = True
            reader_thread.start()

            # Main loop for sending commands
            while self.running:
                try:
                    cmd = input("> ")
                except (EOFError, KeyboardInterrupt):
                    # Exit on Ctrl-D / Ctrl-C
                    break

                # Ignore empty commands (only whitespace)
                if not cmd.strip():
                    continue

                # Ignore comment lines starting with '#', allow leading whitespace
                if cmd.lstrip().startswith("#"):
                    continue

                if cmd.lower() in ("quit", "exit", "q"):
                    break

                payload = self.encode_protocol(cmd)
                # print("Cmd encoded as:", payload)
                if payload:
                    self.serial_connection.write(payload)

        except serial.SerialException as e:
            print(f"Connection error: {e}", file=sys.stderr)
        finally:
            self.running = False
            if self.serial_connection and self.serial_connection.is_open:
                self.serial_connection.close()
            print("Connection closed.", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Serial port communication tool.")
    parser.add_argument(
        "--port",
        type=str,
        default="/dev/ttyUSB0",
        help="Serial port (e.g. /dev/ttyUSB0 or COM3)",
    )
    parser.add_argument(
        "--baudrate", type=int, default=9600, help="Baud rate (default: 9600)"
    )
    parser.add_argument(
        "--parity",
        type=str,
        default="N",
        choices=["N", "E", "O", "M", "S"],
        help="Parity: N (none), E (even), O (odd), M (mark), S (space). Default: N",
    )
    parser.add_argument(
        "--stopbits",
        type=float,
        default=1.0,
        choices=[1, 1.5, 2],
        help="Number of stop bits: 1, 1.5 or 2. Default: 1",
    )
    args = parser.parse_args()

    app = SOF0273(args.port, args.baudrate, parity=args.parity, stopbits=args.stopbits)
    app.start()


if __name__ == "__main__":
    main()
