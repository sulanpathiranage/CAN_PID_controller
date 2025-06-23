from pymodbus.client import ModbusTcpClient
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.constants import Endian

ip = "169.254.1.1"
client = ModbusTcpClient(ip, port=502)

if client.connect():
    result = client.read_holding_registers(2160, count = 2)
    if result.isError():
        print("Modbus request failed.")
    else:
        print("Modbus registers:", result.registers)
    client.close()
else:
    print("Failed to connect over Modbus TCP")

decoder = BinaryPayloadDecoder.fromRegisters(
result.registers,
byteorder=Endian.BIG,   
wordorder=Endian.LITTLE    
)

float_value = decoder.decode_32bit_float()
celsius = (float_value - 32) * 5.0 / 9.0
print(f"Temperature in Celsius: {celsius:.2f}°C")
print("Decoded float value:", float_value)
