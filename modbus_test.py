# from pymodbus.client import ModbusTcpClient
# from pymodbus.payload import BinaryPayloadDecoder
# from pymodbus.constants import Endian

# ip = "169.254.1.1"
# client = ModbusTcpClient(ip, port=502)

# if client.connect():
#     result = client.read_holding_registers(2160, count = 2)
#     if result.isError():
#         print("Modbus request failed.")
#     else:
#         print("Modbus registers:", result.registers)
#     client.close()
# else:
#     print("Failed to connect over Modbus TCP")

# decoder = BinaryPayloadDecoder.fromRegisters(
# result.registers,
# byteorder=Endian.BIG,   
# wordorder=Endian.LITTLE    
# )

# float_value = decoder.decode_32bit_float()
# celsius = (float_value - 32) * 5.0 / 9.0
# print(f"Temperature in Celsius: {celsius:.2f}°C")
# print("Decoded float value:", float_value)

from pymodbus.client import ModbusTcpClient
from pymodbus.payload import BinaryPayloadDecoder, BinaryPayloadBuilder
from pymodbus.constants import Endian
from pymodbus.exceptions import ModbusException

def read_write_clear_force_setpoint(
    ip_address,
    port,
    new_setpoint_value=None,
    clear_alarm_instance=None, # Integer 1-4 for alarm instance to clear, or None
    force_alarm_trigger=False  # Boolean to attempt to trigger force alarm
):
    """
    Connects to a Modbus TCP device, performs operations including
    reading/writing setpoint, clearing an alarm, and attempting to force an alarm.

    Args:
        ip_address (str): The IP address of the Modbus TCP device.
        port (int): The Modbus TCP port (usually 502).
        new_setpoint_value (float, optional): The new setpoint value to write.
                                             If None, only reads the setpoint.
        clear_alarm_instance (int, optional): The instance number (1-4) of the alarm to clear.
                                              If None, no alarm is cleared.
        force_alarm_trigger (bool, optional): If True, attempts to trigger the "Force Alarm to Occur" feature.
                                              Note: Direct digital trigger via Modbus might not be supported.
    """
    client = ModbusTcpClient(ip_address, port=port)

    # Modbus register addresses (0-indexed for pymodbus holding registers)
    # Setpoint for Control Loop 1: Parameter ID 7001, Map 1 Absolute Address 402161 -> register 2160
    SETPOINT_REGISTER = 2160

    # Alarm Clear Request: Parameter ID 9013
    # Alarm 1 Clear Request: Map 1 Absolute Address 401505 -> register 1504
    # Each subsequent alarm instance is 50 registers higher.
    ALARM_CLEAR_BASE_REGISTER = 1504
    ALARM_REGISTER_OFFSET_PER_INSTANCE = 50
    ALARM_CLEAR_VALUE = 0 # Value to write to clear the alarm

    try:
        # 1. Connect to the Modbus device
        print(f"Attempting to connect to Modbus TCP at {ip_address}:{port}...")
        if not client.connect():
            print("Failed to connect over Modbus TCP. Please check IP, port, and device availability.")
            return

        print("Successfully connected to Modbus TCP.")

        # 2. Read the current setpoint
        print("\n--- Reading current setpoint ---")
        read_result = client.read_holding_registers(SETPOINT_REGISTER, count=2)

        if read_result.isError():
            raise ModbusException(f"Modbus read request failed: {read_result}")
        
        print("Raw registers read:", read_result.registers)

        # Decode the float value from the read registers
        # The documentation states Modbus Word Order default is Low-High (Endian.LITTLE for wordorder).
        # Byte order is typically BIG for Modbus.
        decoder = BinaryPayloadDecoder.fromRegisters(
            read_result.registers,
            byteorder=Endian.BIG,
            wordorder=Endian.LITTLE
        )
        current_setpoint = decoder.decode_32bit_float()
        print(f"Decoded current setpoint: {current_setpoint:.2f}")

        # 3. Optionally write a new setpoint
        if new_setpoint_value is not None:
            print(f"\n--- Attempting to write new setpoint: {new_setpoint_value:.2f} ---")
            
            builder = BinaryPayloadBuilder(
                byteorder=Endian.BIG,
                wordorder=Endian.LITTLE
            )
            builder.add_32bit_float(new_setpoint_value)
            payload_registers = builder.to_registers()
            
            write_result = client.write_registers(SETPOINT_REGISTER, payload_registers)

            if write_result.isError():
                raise ModbusException(f"Modbus write request failed: {write_result}")
            
            print("Successfully wrote new setpoint.")
            
            # Read the setpoint again to confirm the write
            print("\n--- Reading setpoint after write confirmation ---")
            confirm_read_result = client.read_holding_registers(SETPOINT_REGISTER, count=2)

            if confirm_read_result.isError():
                raise ModbusException(f"Modbus read confirmation failed: {confirm_read_result}")
            
            decoder_confirm = BinaryPayloadDecoder.fromRegisters(
                confirm_read_result.registers,
                byteorder=Endian.BIG,
                wordorder=Endian.LITTLE
            )
            confirmed_setpoint = decoder_confirm.decode_32bit_float()
            print(f"Confirmed setpoint after write: {confirmed_setpoint:.2f}")

            if abs(confirmed_setpoint - new_setpoint_value) < 0.01: # Check for float equality within a small tolerance
                print("Setpoint successfully updated and confirmed!")
            else:
                print("Warning: Written setpoint does not match confirmed read value. This might indicate an issue or a value outside the device's acceptable range.")

        # 4. Optionally clear an alarm
        if clear_alarm_instance is not None:
            if 1 <= clear_alarm_instance <= 4:
                alarm_clear_register = ALARM_CLEAR_BASE_REGISTER + (clear_alarm_instance - 1) * ALARM_REGISTER_OFFSET_PER_INSTANCE
                print(f"\n--- Attempting to clear Alarm {clear_alarm_instance} at register {alarm_clear_register} ---")
                
                # Write 0 to the alarm clear request register
                clear_result = client.write_register(alarm_clear_register, ALARM_CLEAR_VALUE)
                
                if clear_result.isError():
                    print(f"Failed to clear Alarm {clear_alarm_instance}: {clear_result}")
                else:
                    print(f"Successfully sent clear request for Alarm {clear_alarm_instance}.")
                    print("Note: Alarm will only clear if its condition no longer exists and it's latched.")
            else:
                print(f"\nInvalid alarm instance for clearing: {clear_alarm_instance}. Must be between 1 and 4.")

        # 5. Optionally attempt to force an alarm
        if force_alarm_trigger:
            print("\n--- Attempting to trigger 'Force Alarm to Occur' ---")
            print("Note: The 'Force Alarm to Occur' feature in Watlow PM PLUS is typically assigned to a physical Digital Input or Function Key.")
            print("There is no direct Modbus register that, when written to, digitally triggers this action.")
            print("To activate this feature via Modbus, you would typically need to:")
            print("1. Configure a Digital I/O on the PM PLUS as an input and assign 'Force Alarm to Occur' to it.")
            print("2. Then, use a Modbus-controlled digital output (from another device, or potentially another configured output on the PM PLUS itself) to toggle that physical input.")
            print("No Modbus write operation was performed for 'force_alarm_trigger' due to this architectural design.")


    except ModbusException as e:
        print(f"Modbus operation error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        # 6. Close the client connection
        if client.is_connected():
            client.close()
            print("\nModbus client disconnected.")


device_ip = "169.254.1.1"
modbus_port = 502

print("--- Test 1: Just read the current setpoint ---")
read_write_clear_force_setpoint(device_ip, modbus_port)

print("\n" + "="*50 + "\n")

print("--- Test 2: Read, then write a new setpoint (e.g., 85.0) ---")
read_write_clear_force_setpoint(device_ip, modbus_port, new_setpoint_value=85.0)

print("\n" + "="*50 + "\n")

print("--- Test 3: Read, write another setpoint (e.g., 70.0), and try to clear Alarm 1 ---")
read_write_clear_force_setpoint(device_ip, modbus_port, new_setpoint_value=70.0, clear_alarm_instance=1)

print("\n" + "="*50 + "\n")

print("--- Test 4: Read, and attempt to trigger 'Force Alarm to Occur' (no direct digital trigger) ---")
read_write_clear_force_setpoint(device_ip, modbus_port, force_alarm_trigger=True)

print("\n" + "="*50 + "\n")

print("--- Test 5: Clear Alarm 2 (example of clearing a different alarm instance) ---")
read_write_clear_force_setpoint(device_ip, modbus_port, clear_alarm_instance=2)