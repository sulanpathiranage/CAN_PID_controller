class PIDController:
    def __init__(self, kp=1.0, ki=0.0, kd=0.0, setpoint=0.0):
        self.kp = kp  
        self.ki = ki  
        self.kd = kd  
        self.setpoint = setpoint
        self.prev_error = 0
        self.integral = 0

    @staticmethod
    def saturate(value, lower, upper):
        return max(lower, min(upper, value))
    
    def reset(self):
        self.prev_error = 0
        self.integral = 0

    def set_params(self, kp, ki, kd):
        self.kp, self.ki, self.kd = kp, ki, kd

    def set_setpoint(self, setpoint):
        self.setpoint = setpoint

    def calculate(self, measured_value):
        error = self.setpoint - measured_value
        self.integral += error
        derivative = error - self.prev_error

        output = (
            self.kp * error
            + PIDController.saturate(self.ki * self.integral, 0, 100)
            + PIDController.saturate(self.kd * derivative, 0, 100)
        )

        self.prev_error = error
        return PIDController.saturate(output, 0, 100)

