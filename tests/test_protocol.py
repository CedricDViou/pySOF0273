import struct

import pytest

from pysof0273 import SOF0273


@pytest.fixture
def app():
    # port argument is unused by the tested methods
    return SOF0273("/dev/null")


def test_encode_read_frame(app):
    frame = app.encode_protocol("r")
    # READ CMD format is '>HBH' -> magic(H), code(B), crc(H)
    magic, code, crc = struct.unpack(">HBH", frame)
    assert magic == app.MAGIC_NUMBER
    assert code == app.READ_CODE
    # verify CRC matches computed value
    computed = app.calcul_crc_16(frame, len(frame) - 2)
    assert crc == computed


def test_encode_write_frame_and_values(app):
    # write 1.0 dB and 2.5 dB -> codes 2 and 5
    frame = app.encode_protocol("w 1.0 2.5")
    # WRITE CMD format is '>HBBBH'
    magic, code, a1, a2, crc = struct.unpack(">HBBBH", frame)
    assert magic == app.MAGIC_NUMBER
    assert code == app.WRITE_CODE
    assert a1 == app.att_2_code(1.0)
    assert a2 == app.att_2_code(2.5)
    assert crc == app.calcul_crc_16(frame, len(frame) - 2)


def test_decode_ack_valid(app):
    # Build a valid ACK frame for WRITE_CODE with att codes 2 and 5
    code = app.WRITE_CODE
    att1 = 2
    att2 = 5
    # ACK format '>HBBBH' (magic, code, att_lofar, att_nenu, crc)
    stub = struct.pack(app.FRM[code]["ACK"], app.MAGIC_NUMBER, code, att1, att2, 0)
    crc = app.calcul_crc_16(stub, len(stub) - 2)
    frame = struct.pack(app.FRM[code]["ACK"], app.MAGIC_NUMBER, code, att1, att2, crc)
    decoded = app.decode_protocol(frame)
    expected = (
        f"{app.FRM[code]['TYPE_str']} Ack - Att_LOFAR: "
        f"{app.code_2_att(att1)} dB, Att_NenuFAR: {app.code_2_att(att2)} dB\n"
    )
    assert decoded == expected


def test_decode_crc_mismatch(app):
    # Same frame but tamper CRC
    code = app.WRITE_CODE
    att1 = 2
    att2 = 5
    stub = struct.pack(app.FRM[code]["ACK"], app.MAGIC_NUMBER, code, att1, att2, 0)
    crc = app.calcul_crc_16(stub, len(stub) - 2)
    # change crc so it doesn't match
    bad_crc = (crc + 1) & 0xFFFF
    frame = struct.pack(
        app.FRM[code]["ACK"], app.MAGIC_NUMBER, code, att1, att2, bad_crc
    )
    decoded = app.decode_protocol(frame)
    assert decoded.startswith("Exception in decode_protocol:")


def test_decode_incomplete(app):
    assert app.decode_protocol(b"\x00\x01") == "Incomplete data received."
