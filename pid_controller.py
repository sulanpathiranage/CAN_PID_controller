class PIDController:
    def __init__(self, kp, ki, kd):
        self.kp = kp  # Proportional coefficient
        self.ki = ki  # Integral coefficient
        self.kd = kd  # Derivative coefficient
        
        self.prev_error = 0
        self.integral = 0

    def calculate(self, setpoint, measured_value):
        error = setpoint - measured_value  # The difference between target and current value
        self.integral += error  # Sum of errors (for integral term)
        derivative = error - self.prev_error  # Rate of change of error (for derivative term)
        
        # PID formula: P + I + D
        output = (self.kp * error) + (self.ki * self.integral) + (self.kd * derivative)
        
        self.prev_error = error  # Update the previous error for the next cycle
        
        return output

# Example usage:
pid = PIDController(kp=1.0, ki=0.1, kd=0.01)  # Create a PID controller with chosen constants
