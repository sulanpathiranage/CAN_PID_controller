from pymodbus.client import ModbusTcpClient
from pymodbus.payload import BinaryPayloadBuilder
from pymodbus.constants import Endian

ip = "169.254.1.1"
client = ModbusTcpClient(ip, port=502)

setpoint_value = 20.0  # degrees Celsius

if client.connect():
    builder = BinaryPayloadBuilder(byteorder=Endian.BIG, wordorder=Endian.LITTLE)
    builder.add_32bit_float(setpoint_value)
    payload = builder.to_registers()  # converts float into 2 registers

    result = client.write_registers(2160, payload)
    if result.isError():
        print("Modbus write failed.")
    else:
        print(f"Successfully wrote setpoint value: {setpoint_value} °C")
    client.close()
else:
    print("Failed to connect over Modbus TCP")
