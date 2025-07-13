from pymodbus.client import ModbusTcpClient
from pymodbus.payload import BinaryPayloadBuilder, BinaryPayloadDecoder
from pymodbus.constants import Endian


MODBUS_HOST = 'localhost'
MODBUS_PORT = 502        
UNIT_ID = 1               


SETPOINT_REGISTER_ADDRESS = 2160       # Corresponds to 402161 for 'Control Loop - Set Point'
PROCESS_VARIABLE_REGISTER_ADDRESS = 2208 # Corresponds to 402209 for 'Control Loop - Source Value B' (Assumed PV)
CONTROLLER_OUTPUT_REGISTER_ADDRESS = 2162 # Corresponds to 402163 for 'Control Loop - Manual Power' (Assumed PID Output)

class ModbusClient:

    def connect_modbus_client():
        """Establishes a Modbus TCP client connection."""
        client = ModbusTcpClient(MODBUS_HOST, port=MODBUS_PORT)
        if client.connect():
            print(f"Connected to Modbus TCP device at {MODBUS_HOST}:{MODBUS_PORT}")
            return client
        else:
            print(f"Failed to connect to Modbus TCP device at {MODBUS_HOST}:{MODBUS_PORT}")
            return None

    def set_setpoint(client, setpoint_value):
        """Writes the setpoint value to the controller."""
        if client:
            # Build payload for a 32-bit float (occupies two 16-bit registers)
            builder = BinaryPayloadBuilder(byteorder=Endian.Big, wordorder=Endian.Little)
            builder.add_32bit_float(setpoint_value)
            payload = builder.build()
            
            # Write multiple registers for float values
            result = client.write_registers(SETPOINT_REGISTER_ADDRESS, payload, unit=UNIT_ID)
            
            if result.isError():
                print(f"Error writing setpoint: {result}")
            else:
                print(f"Setpoint successfully set to: {setpoint_value}°F")
        else:
            print("Modbus client not connected.")

    def read_process_variable(client):
        """Reads the process variable (temperature) from the controller."""
        if client:
            result = client.read_holding_registers(PROCESS_VARIABLE_REGISTER_ADDRESS, 2, unit=UNIT_ID)
            
            if result.isError():
                print(f"Error reading process variable: {result}")
                return None
            else:
                # Decode the float value from the registers
                decoder = BinaryPayloadDecoder.fromRegisters(result.registers, byteorder=Endian.Big, wordorder=Endian.Little)
                pv = decoder.decode_32bit_float()
                print(f"Current Process Variable (Temperature): {pv}°F")
                return pv
        else:
            print("Modbus client not connected.")
            return None

    def get_controller_output(client):
        """Reads the controller output (power) from the controller."""
        if client:
            result = client.read_holding_registers(CONTROLLER_OUTPUT_REGISTER_ADDRESS, 2, unit=UNIT_ID)
            
            if result.isError():
                print(f"Error reading controller output: {result}")
                return None
            else:
                decoder = BinaryPayloadDecoder.fromRegisters(result.registers, byteorder=Endian.Big, wordorder=Endian.Little)
                output = decoder.decode_32bit_float()
                print(f"Controller Output (Power): {output}%")
                return output
        else:
            print("Modbus client not connected.")
            return None



def main():
    """Main function to demonstrate Modbus communication with the heater controller."""
    client = ModbusClient.connect_modbus_client()
    if client:

        new_setpoint_temp = 75.0 
        ModbusClient.set_setpoint(client, new_setpoint_temp)

        current_temperature = ModbusClient.read_process_variable(client)

        current_output_power = ModbusClient.get_controller_output(client)

        client.close()
        print("\nModbus connection closed.")

if __name__ == "__main__":
    main()