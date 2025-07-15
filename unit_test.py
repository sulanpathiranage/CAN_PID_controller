import pytest
from data_manager import SystemDataManager

def test_initial_state():
    manager = SystemDataManager(history_len=10)
    
    # Check initial pressure and temperature buffers length
    assert len(manager.ch_data) == len(manager.pressure_sensor_names)
    assert all(len(deq) == 10 for deq in manager.ch_data)
    assert len(manager.temp_data) == len(manager.temperature_sensor_names)
    
    # Check initial setpoints are zero
    assert manager.get_mfm1() == 0.0
    assert manager.get_mfm2() == 0.0
    assert manager.get_pic() == 0.0
    
    # E-Stop is off initially
    assert manager.eStopValue is False

def test_update_pressure_data():
    manager = SystemDataManager(history_len=5)
    
    # Create sample raw voltages matching pt_info size
    raw_voltages = [0.5] * len(manager.pt_info)
    
    # Call update_pressure_data
    manager.update_pressure_data(raw_voltages)
    
    # Check if last_pressures are updated with scaled values
    expected_pressures = [v * scale for v, scale in zip(raw_voltages, manager.pt_info.values())]
    assert manager.last_pressures == expected_pressures
    
    # Check data stored in deques matches the latest value
    for i, val in enumerate(expected_pressures):
        assert manager.ch_data[i][-1] == val

def test_update_temperature_data_with_invalid_marker():
    manager = SystemDataManager(history_len=5)
    
    invalid_temps = [manager.INVALID_TEMP_MARKER] * len(manager.temperature_sensor_names)
    manager.update_temperature_data(invalid_temps)
    
    assert all(t == 0.0 for t in manager.last_temps)

def test_set_mfm_setpoints_bounds():
    manager = SystemDataManager()
    
    manager.set_mfm1(120)  # Above 100%
    assert manager.get_mfm1() == 100.0
    
    manager.set_mfm2(-10)  # Below 0%
    assert manager.get_mfm2() == 0.0

def test_e_stop_toggle_resets_pump_and_esv():
    manager = SystemDataManager()
    manager._commanded_pump_on = 1
    manager._commanded_manual_speed = 50
    manager._commanded_pid_output = 75.0
    
    manager.eStopValue = True
    
    assert manager._commanded_pump_on == 0
    assert manager._commanded_manual_speed == 0
    assert manager._commanded_pid_output == 0.0
    assert all(state == 0 for state in manager.esv_state)

def test_interlock_trigger_sets_e_stop():
    manager = SystemDataManager()
    # Provide sensor values that trigger interlock limits:
    
    # Fake method patching for get_latest_sensor_value to simulate triggering
    manager.get_latest_sensor_value = lambda designator: {
        # "PT10110": manager._bar_to_psi(8),  # Above upper limit 7 psi
        "PT10120": manager._bar_to_psi(21),
        "TI10119": 70
    }.get(designator, 0)
    manager._last_deditec = [0.0] * len(manager.deditec_feedback)
    
    # Run interlock trigger
    manager.interlock_trigger()
    
    # E-stop should be enabled
    assert manager.eStopValue is True
    assert manager.interlock_flag is True
