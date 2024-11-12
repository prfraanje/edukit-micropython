class PID():
    def __init__(self,get_sensor,set_actuator,sampling_time_ms,Kp1,Ki1,Kd1,Kp2,Ki2,Kd2,r1,r2,e1_sum,e2_sum,y1_prev,y2_prev,limit1_sum,limit2_sum,run=False,run1=True,run2=True,supervisory={}):
        self.get_sensor = get_sensor
        self.set_actuator = set_actuator
        self.sampling_time_ms = sampling_time_ms    
        self.Kp1 = Kp1
        self.Ki1 = Ki1
        self.Kd1 = Kd1
        self.Kp2 = Kp2
        self.Ki2 = Ki2
        self.Kd2 = Kd2
        self.r1 = r1
        self.r2 = r2      
        self.e1_sum = e1_sum
        self.e2_sum = e2_sum        
        self.limit1_sum = limit1_sum
        self.limit1_sum_flag = False
        self.limit2_sum = limit2_sum
        self.limit2_sum_flag = False
        self.u = 0.
        self.y = [0, 0]
        self.e1 = 0
        self.e2 = 0        
        self.y1_diff = 0
        self.y2_diff = 0        
        self.y1_prev = y1_prev
        self.y2_prev = y2_prev        
        self.run = run  # if True run the controller
        self.run1 = run1  # if True run the controller
        self.run2 = run2  # if True run the controller                
        self.sample = [0, 0, 0.]
        self.supervisory = supervisory
        self.log = 0
 
    @micropython.native
    def limit(self):
        if self.e1_sum < -self.limit1_sum:
            self.e1_sum = -self.limit1_sum
            self.limit1_sum_flag = True
        elif self.e1_sum > self.limit1_sum:
            self.e1_sum = self.limit1_sum
            self.limit1_sum_flag = True
        else:
            self.limit1_sum_flag = False
            
        if self.e2_sum < -self.limit2_sum:
            self.e2_sum = -self.limit2_sum
            self.limit2_sum_flag = True
        elif self.e2_sum > self.limit2_sum:
            self.e2_sum = self.limit2_sum
            self.limit2_sum_flag = True
        else:
            self.limit2_sum_flag = False

    def set_gains1(self,Kp1,Ki1,Kd1):
        self.Kp1 = Kp1
        self.Ki1 = Ki1
        self.Kd1 = Kd1

    def set_gains2(self,Kp2,Ki2,Kd2):
        self.Kp2 = Kp2
        self.Ki2 = Ki2
        self.Kd2 = Kd2

    def get_gains1(self):
        return (self.Kp1,self.Ki1,self.Kd1)

    def get_gains2(self):
        return (self.Kp2,self.Ki2,self.Kd2)
    
    def reset_state(self):
        self.e1_sum = 0
        self.y1_prev = 0
        self.limit1_sum_flag = False
        self.e2_sum = 0
        self.y2_prev = 0
        self.limit2_sum_flag = False

    @micropython.native
    async def control(self):
        self.y1_prev = self.y[0]
        self.y2_prev = self.y[1]        
        self.y = self.get_sensor()
        self.y1_diff = self.y[0] - self.y1_prev
        self.y2_diff = self.y[1] - self.y2_prev        
        supervis = self.supervisory
        #async with self.supervisory['lock']:
        if supervis['reference_add']:
            if supervis['reference_counter'] >= supervis['reference_num_samples']:
                if not supervis['reference_repeat']:
                    supervis['reference_add'] = False
                supervis['reference_counter'] = 0
                self.e1 = self.r1 + supervis['reference_sequence'][supervis['reference_counter']] - self.y[0]                
            else:
                self.e1 = self.r1 + supervis['reference_sequence'][supervis['reference_counter']] - self.y[0]
                supervis['reference_counter'] += 1
        else:
            self.e1 = self.r1 - self.y[0]

        self.e2 = self.r2 - self.y[1]
        
        self.u = 0.
        if self.run:
            if self.run1:
                self.e1_sum += self.e1
                self.limit()

                self.u += self.Kp1 * self.e1 + self.Ki1 * self.e1_sum - self.Kd1 * self.y1_diff  # do not take feedback of derivative in reference (!)

            if self.run2:
                self.e2_sum += self.e2
                self.limit()

                self.u += self.Kp2 * self.e2 + self.Ki2 * self.e2_sum - self.Kd2 * self.y2_diff  # do not take feedback of derivative in reference (!)

        #async with supervis['lock']:
        if supervis['control_add']:
            if supervis['control_counter'] >= supervis['control_num_samples']:
                if not supervis['control_repeat']:
                    supervis['control_add'] = False
                    supervis['control_counter'] = 0
                    self.set_actuator(self.u)
                    self.sample[2] = self.u
                else:
                    supervis['control_counter'] = 0
                    self.set_actuator(self.u + supervis['control_sequence'][supervis['control_counter']])
                    self.sample[2] = self.u + supervis['control_sequence'][supervis['control_counter']]
                    supervis['control_counter'] += 1                    
                    
            else:
                self.set_actuator(self.u + supervis['control_sequence'][supervis['control_counter']])
                self.sample[2] = self.u + supervis['control_sequence'][supervis['control_counter']]
                supervis['control_counter'] += 1
        else:
            self.set_actuator(self.u)
            self.sample[2] = self.u
            
        self.sample[0] = self.y[0]
        self.sample[1] = self.y[1]

        

