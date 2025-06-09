from pymodbus.client import ModbusTcpClient
from pymodbus.payload import BinaryPayloadBuilder, BinaryPayloadDecoder
from pymodbus.constants import Endian

# Modbus TCP settings
# !!! IMPORTANT: Replace 'localhost' with your Modbus device's IP address !!!
MODBUS_HOST = 'localhost'
MODBUS_PORT = 502         # Standard Modbus TCP port
UNIT_ID = 1               # Modbus Slave ID (typically 1 for most devices)

# Register Addresses (based on CSV and common Modbus conventions)
# Modbus '4xxxx' addresses correspond to holding registers.
# In pymodbus, you usually use the register address directly (e.g., 402161 becomes 2160)
SETPOINT_REGISTER_ADDRESS = 2160       # Corresponds to 402161 for 'Control Loop - Set Point'
PROCESS_VARIABLE_REGISTER_ADDRESS = 2208 # Corresponds to 402209 for 'Control Loop - Source Value B' (Assumed PV)
CONTROLLER_OUTPUT_REGISTER_ADDRESS = 2162 # Corresponds to 402163 for 'Control Loop - Manual Power' (Assumed PID Output)

# PID Tuning Register Addresses (PLACEHOLDERS - NOT FOUND IN YOUR CSV)
# You MUST replace these with actual addresses from your device's Modbus documentation if available.
P_GAIN_REGISTER_ADDRESS = None  # Example: 2000 (replace with actual P gain register address)
I_GAIN_REGISTER_ADDRESS = None  # Example: 2002 (replace with actual I gain register address)
D_GAIN_REGISTER_ADDRESS = None  # Example: 2004 (replace with actual D gain register address)

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
        # Read two holding registers for a 32-bit float
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
        # Read two holding registers for a 32-bit float
        result = client.read_holding_registers(CONTROLLER_OUTPUT_REGISTER_ADDRESS, 2, unit=UNIT_ID)
        
        if result.isError():
            print(f"Error reading controller output: {result}")
            return None
        else:
            # Decode the float value from the registers
            decoder = BinaryPayloadDecoder.fromRegisters(result.registers, byteorder=Endian.Big, wordorder=Endian.Little)
            output = decoder.decode_32bit_float()
            print(f"Controller Output (Power): {output}%")
            return output
    else:
        print("Modbus client not connected.")
        return None

def tune_pid_parameters(client, p_gain=None, i_gain=None, d_gain=None):
    """
    Writes PID tuning parameters (P, I, D) to the controller.
    NOTE: This function uses placeholder addresses. You MUST replace
    P_GAIN_REGISTER_ADDRESS, I_GAIN_REGISTER_ADDRESS, and D_GAIN_REGISTER_ADDRESS
    with the actual Modbus addresses for your specific device.
    """
    if client:
        print("\n--- PID Tuning (Conceptual) ---")
        if P_GAIN_REGISTER_ADDRESS and p_gain is not None:
            builder = BinaryPayloadBuilder(byteorder=Endian.Big, wordorder=Endian.Little)
            builder.add_32bit_float(p_gain)
            payload = builder.build()
            result = client.write_registers(P_GAIN_REGISTER_ADDRESS, payload, unit=UNIT_ID)
            if result.isError():
                print(f"Error writing P gain: {result}")
            else:
                print(f"P Gain set to: {p_gain}")
        else:
            print("P gain register address not defined or value not provided.")

        if I_GAIN_REGISTER_ADDRESS and i_gain is not None:
            builder = BinaryPayloadBuilder(byteorder=Endian.Big, wordorder=Endian.Little)
            builder.add_32bit_float(i_gain)
            payload = builder.build()
            result = client.write_registers(I_GAIN_REGISTER_ADDRESS, payload, unit=UNIT_ID)
            if result.isError():
                print(f"Error writing I gain: {result}")
            else:
                print(f"I Gain set to: {i_gain}")
        else:
            print("I gain register address not defined or value not provided.")

        if D_GAIN_REGISTER_ADDRESS and d_gain is not None:
            builder = BinaryPayloadBuilder(byteorder=Endian.Big, wordorder=Endian.Little)
            builder.add_32bit_float(d_gain)
            payload = builder.build()
            result = client.write_registers(D_GAIN_REGISTER_ADDRESS, payload, unit=UNIT_ID)
            if result.isError():
                print(f"Error writing D gain: {result}")
            else:
                print(f"D Gain set to: {d_gain}")
        else:
            print("D gain register address not defined or value not provided.")

        if not (P_GAIN_REGISTER_ADDRESS and I_GAIN_REGISTER_ADDRESS and D_GAIN_REGISTER_ADDRESS):
            print("\nWARNING: PID tuning registers (P, I, D) were not explicitly identified in the provided CSV.")
            print("Please consult your heater controller's Modbus documentation for the correct register addresses to tune PID parameters.")
    else:
        print("Modbus client not connected.")

def main():
    """Main function to demonstrate Modbus communication with the heater controller."""
    client = connect_modbus_client()
    if client:
        # --- Example Usage ---

        # 1. Set the Setpoint
        new_setpoint_temp = 75.0 # Example setpoint in degrees Fahrenheit
        set_setpoint(client, new_setpoint_temp)

        # 2. Get the Process Variable (Current Temperature)
        current_temperature = read_process_variable(client)

        # 3. Get the Controller Output (Power being applied)
        current_output_power = get_controller_output(client)

        # 4. Tune PID Parameters (Conceptual - requires actual register addresses)
        # Uncomment and modify these lines if you have the actual PID gain register addresses
        # tune_pid_parameters(client, p_gain=1.2, i_gain=0.5, d_gain=0.1)

        # Always close the Modbus connection when done
        client.close()
        print("\nModbus connection closed.")

if __name__ == "__main__":
    main()