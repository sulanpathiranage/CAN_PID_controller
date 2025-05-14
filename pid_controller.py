class PIDController:
    def __init__(self, kp, ki, kd, setpoint):
        self.kp = kp  
        self.ki = ki  
        self.kd = kd  
        self.setpoint = setpoint
        
        self.prev_error = 0
        self.integral = 0

    def __saturate(value, lower_bound, upper_bound):
        """Clip value at bounds

        Args:
            value (double/float/int): variable being bounded
            lower_bound (int): clip at this lower bound
            upper_bound (int): clip at this upper bound

        Returns:
            int: variable after being clipped
        """
        if (value<lower_bound):
            return lower_bound
        elif (value>upper_bound):
            return upper_bound
        else:
            return value
        
    def calculate(self, measured_value):
        """Calculate the PID output

        Args:
            setpoint (_type_): setpoint of PID
            measured_value (_type_): process var. 

        Returns:
            _type_: output variable
        """
        error = self.setpoint - measured_value  
        self.integral += error  
        derivative = error - self.prev_error  

        # PID formula: P + I + D
        output = (self.kp * error) + PIDController.__saturate((self.ki * self.integral), 0, 100) + (self.kd * derivative)
        
        self.prev_error = PIDController.__saturate(error, 0, 100) 
        
        return PIDController.__saturate(output,0, 100)
    

