# class PIDController:
#     def __init__(self, kp=1.0, ki=0.0, kd=0.0, setpoint=0.0):
#         self.kp = kp  
#         self.ki = ki  
#         self.kd = kd  
#         self.setpoint = setpoint
#         self.prev_error = 0
#         self.integral = 0

#     @staticmethod
#     def saturate(value, lower, upper):
#         return max(lower, min(upper, value))
    
#     def reset(self):
#         self.prev_error = 0
#         self.integral = 0

#     def set_params(self, kp, ki, kd):
#         self.kp, self.ki, self.kd = kp, ki, kd

#     def set_setpoint(self, setpoint):
#         self.setpoint = setpoint

#     def calculate(self, measured_value):
#         error = self.setpoint - measured_value
#         self.integral += error
#         derivative = error - self.prev_error

#         output = (
#             self.kp * error
#             + PIDController.saturate(self.ki * self.integral, 0, 100)
#             + PIDController.saturate(self.kd * derivative, 0, 100)
#         )

#         self.prev_error = error
#         return PIDController.saturate(output, 0, 100)

class PIDController:
    def __init__(self, kp=1.0, ki=0.0, kd=0.0, setpoint=0.0):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.setpoint = setpoint
        self.prev_error = 0
        self.integral = 0
        self.prev_measured_value = setpoint 

    @staticmethod
    def saturate(value, lower, upper):
        return max(lower, min(upper, value))

    def reset(self):
        self.prev_error = 0
        self.integral = 0
        self.prev_measured_value = self.setpoint
    def set_params(self, kp, ki, kd):
        self.kp, self.ki, self.kd = kp, ki, kd

    def set_setpoint(self, setpoint):
        self.setpoint = setpoint

    def calculate(self, measured_value, dt=1.0):
        error = self.setpoint - measured_value

        p_term = self.kp * error

        provisional_output = p_term + self.ki * self.integral + self.kd * (measured_value - self.prev_measured_value) / dt
        s_output = PIDController.saturate(provisional_output, 0, 100)

        if not ((s_output >= 100 and error > 0) or (s_output <= 0 and error < 0)):
             self.integral += error * dt

        i_term = self.ki * self.integral
        # i_term = PIDController.saturate(i_term, -some_max_integral_value, some_max_integral_value)


        derivative = (measured_value - self.prev_measured_value) / dt
        d_term = self.kd * derivative
        # d_term = PIDController.saturate(d_term, -some_max_derivative_value, some_max_derivative_value)


        output = p_term + i_term + d_term

        self.prev_error = error
        self.prev_measured_value = measured_value 

        return PIDController.saturate(output, 0, 100)