import piheaan as heaan
from piheaan.math import approx

import pandas as pd
import numpy as np
import math, os
from tqdm import tqdm
from time import time

class Server:
    def __init__(self):
        # Define constant
        self.log_slots = 15
        self.inf1 = 1e+10
        self.inf2 = 1e+15
        self.inf2_inverse = 1e-15
        self.threshold = 0.00001
        
        # Define dictionaries to store data
        self.args_dict = {}
        self.eval_dict = {}
        self.data_dict = {}
        
        # Define dictionary to store authentication information
        self.validation_code_dict = {}
        self.lock_status = {}
        
    # Create messages for calculation
    def set_msgs_for_calc(self):
        # First index is inf, the rest is 0
        """
        특정 인덱스에 inf 값을 넣기 위한 벡터
        """
        msg_inf = heaan.Message(self.log_slots)
        msg_inf[0] = float(self.inf1)

        # First index is 1, the rest is 0
        """
        특정 인덱스만 남기고 나머지를 0으로 초기화하기 위한 벡터
        """
        msg_scalar = heaan.Message(self.log_slots)
        msg_scalar[0] = 1

        # First index is 0, the rest is 1
        """
        특정 인덱스 값을 0으로 초기화하기 위한 벡터
        """
        msg_eraser = heaan.Message(self.log_slots)
        self.eval.add(msg_eraser, 1, msg_eraser)
        msg_eraser[0] = 0
        msg_eraser_tmp = heaan.Message(self.log_slots)
        
        self.msgs_for_calc = [msg_inf, msg_scalar, msg_eraser, msg_eraser_tmp]
    
    # Save eval instance for calculation
    def save_eval(self, name, eval_):
        self.eval_dict[name] = eval_
        
    # Load eval instance for calculation
    def load_eval(self, name):
        self.eval = self.eval_dict[name]
        
    # Save the arguments received from the client
    def save_args(self, name, *args):
        self.lock_status[name] = True
        self.args_dict[name] = args[0]
        
    # Load the arguments received from the client
    def load_args(self, name):
        self.args = self.args_dict[name]

    # Save the data received from the client
    def save_data(self, name, data):
        self.data_dict[name] = data

    # Load the data received from the client
    def load_data(self, name):
        data = self.data_dict[name]
        return data

    # Bootstrap check
    def check_bootstrap(self, ctxt):
        if ctxt.level == self.eval.min_level_for_bootstrap:
            self.eval.bootstrap(ctxt, ctxt)

    # Calculate DTW distance between two time series
    async def dtw(self, ctxt_n, ctxt_m):
        n, m = 100, 100
        
        # Initialize arguments
        ctxt_n_tmp, ctxt_m_tmp, ctxt_cost, ctxt_zero, ctxt_left, ctxt_up, ctxt_diagonal, ctxt_threshold,\
        ctxt_min, ctxt_max, ctxt_normalizer, ctxt_result, ctxt_dist_n, ctxt_dist_m = self.args
        msg_inf, msg_scalar, msg_eraser, msg_eraser_tmp = self.msgs_for_calc

        # Calculate DTW distance
        for i in tqdm(range(1, n+1)):
            # dtw_matrix[1][0] = float('inf')
            self.eval.add(ctxt_dist_m, msg_inf, ctxt_dist_m)
            for j in range(1, m+1):
                # cost = s[i-1] - t[j-1]
                """
                1. s, t의 i-1, j-1번째 값을 첫 번째 인덱스로 옮김
                2. 두 벡터를 빼 ctxt_cost 첫번째 인덱스에 cost값 저장
                """
                self.eval.left_rotate(ctxt_n, i-1, ctxt_n_tmp)
                self.eval.left_rotate(ctxt_m, j-1, ctxt_m_tmp)
                self.eval.sub(ctxt_n_tmp, ctxt_m_tmp, ctxt_cost)

                # cost = abs(cost)
                """
                1. min_max 함수에 입력가능한 범위로 변환
                2. min_max 함수로 ctxt_min에 음수, ctxt_max에 양수 저장
                3. ctxt_max(양수)에서 ctxt_min(음수)를 빼서 ctxt_cost의 절댓값 계산 및 저장
                4. ctxt_cost에 1e+5를 곱해 원본 범위로 변환
                5. ctxt_cost에 msg_scalar를 첫번째 인덱스의 cost만 남김
                """
                self.eval.mult(ctxt_cost, 1e-5, ctxt_cost)
                approx.min_max(self.eval, ctxt_cost, ctxt_zero, ctxt_min, ctxt_max)
                self.eval.sub(ctxt_max, ctxt_min, ctxt_cost)
                self.eval.mult(ctxt_cost, 1e+5, ctxt_cost)
                self.eval.mult(ctxt_cost, msg_scalar, ctxt_cost)
                
                # dtw_matrix[1][j-1], dtw_matrix[0][j], dtw_matrix[0][j-1]
                """
                1. dtw_matrix[0] = ctxt_dist_n, dtw_matrix[1] = ctxt_dist_m
                2. Left, Up, Diagonal 값 계산: 첫번째 인덱스에 값 저장
                """
                self.eval.left_rotate(ctxt_dist_m, j-1, ctxt_left)
                self.eval.left_rotate(ctxt_dist_n, j, ctxt_up)
                self.eval.left_rotate(ctxt_dist_n, j-1, ctxt_diagonal)
                
                # Transform to the range that can be input to the min_max function
                self.eval.mult(ctxt_left, self.inf2_inverse, ctxt_left)
                self.eval.mult(ctxt_up, self.inf2_inverse, ctxt_up)
                self.eval.mult(ctxt_diagonal, self.inf2_inverse, ctxt_diagonal)

                # cost + min(left, up, diagonal)
                """
                1. left와 up 비교 후 작은 값 ctxt_min에 저장
                2. ctxt_min과 diagonal 비교 후 작은 값 ctxt_min에 저장
                3. ctxt_min을 원본 범위로 변환
                4. ctxt_min에 msg_scalar를 곱해 첫번째 인덱스의 값만 남김
                5. ctxt_cost에 ctxt_min을 더함
                """
                approx.min_max(self.eval, ctxt_left, ctxt_up, ctxt_min, ctxt_max)
                approx.min_max(self.eval, ctxt_min, ctxt_diagonal, ctxt_min, ctxt_max)
                self.eval.mult(ctxt_min, self.inf2, ctxt_min)
                self.eval.mult(ctxt_min, msg_scalar, ctxt_min)
                self.eval.add(ctxt_min, ctxt_cost, ctxt_cost)

                # dtw_matrix[1][j] = cost + min(left, up, diagonal)
                """
                1. msg_eraser를 j만큼 이동시켜 j번째 인덱스 값을 지울 msg_eraser_tmp 생성
                2. msg_eraser_tmp를 활용해 ctxt_dist_m의 j번째 값 0으로 초기화
                3. ctxt_cost의 첫번째 인덱스에 있는 cost를 j번째 인덱스로 이동
                4. ctxt_dist_m에 ctxt_cost를 더해 j번째 인덱스에 cost + min(left, up, diagonal) 저장
                """
                self.eval.right_rotate(msg_eraser, j, msg_eraser_tmp)
                self.eval.mult(ctxt_dist_m, msg_eraser_tmp, ctxt_dist_m)
                self.eval.right_rotate(ctxt_cost, j, ctxt_cost)
                self.eval.add(ctxt_dist_m, ctxt_cost, ctxt_dist_m)

                # Bootstrap check
                self.check_bootstrap(ctxt_cost)
                self.check_bootstrap(ctxt_dist_m)
                self.check_bootstrap(ctxt_left)
                self.check_bootstrap(ctxt_up)
                self.check_bootstrap(ctxt_diagonal)
                self.check_bootstrap(ctxt_min)
                self.check_bootstrap(ctxt_max)
            
            # dtw_matrix[0] = dtw_matrix[1][:]    
            """
            ctxt_dist_m의 값을 ctxt_dist_n으로 복사
            """
            self.eval.mult(ctxt_dist_m, 1, ctxt_dist_n)

        # Return result
        """
        1. dtw_matrix[1][m] = dtw 결과값
        2. ctxt_dist_m를 m만큼 이동시켜 dtw 결과값을 첫번째 인덱스로 이동
        3. msg_scaler를 곱해 첫번째 인덱스 값만 남김
        """
        self.eval.left_rotate(ctxt_dist_m, m, ctxt_result)
        self.eval.mult(ctxt_result, msg_scalar, ctxt_result)
        
        return ctxt_result
    
    # Identification
    async def identification(self, name, input_data):
        # Load eval instance, arguments and data that received from the client
        self.load_eval(name)
        self.load_args(name)
        total_data = self.load_data(name)
        n_data = len(total_data)
        
        # Initialize messages for calculation
        self.set_msgs_for_calc()
        
        # Calculate DTW distance between input data and all data
        total_result = []
        for data in total_data:
            result = await self.dtw(input_data, data)
            total_result.append(result)
            
        # Calculate the sum of the results
        ctxt_sum = total_result[0]
        for result in total_result[1:]:
            print(result)
            self.eval.add(ctxt_sum, result, ctxt_sum)
            
        # Calculate the mean of the results
        ctxt_mean = ctxt_sum
        msg_div = heaan.Message(self.log_slots)
        msg_div[0] = 1 / n_data
        self.eval.mult(ctxt_sum, msg_div, ctxt_mean)
        
        # If the mean is less than the threshold, return 1 else return 0
        msg_inf, msg_scalar, msg_eraser, msg_eraser_tmp = self.msgs_for_calc
        ctxt_threshold = self.args[7]
        msg_threshold = msg_inf
        msg_threshold[0] = self.threshold
        self.eval.add(ctxt_threshold, msg_threshold, ctxt_threshold)
        
        msg_threshold = msg_inf
        msg_threshold[0] = self.threshold
        
        approx.compare(self.eval, ctxt_mean, ctxt_threshold, ctxt_mean)
        
        # Insert validation code from index 1 to 100
        validation_code = list(np.random.randint(0, 10, 100))
        msg_code = heaan.Message(self.log_slots)
        for i in range(1, 101):
            msg_code[i] = validation_code[i-1]
        self.eval.add(ctxt_mean, msg_code, ctxt_mean)
        self.validation_code_dict[name] = validation_code
        
        return ctxt_mean
        
    def check_validation_code(self, name, validation_code):
        if validation_code == self.validation_code_dict[name]:
            return True
        return False
    
    # Lock file: Return True if locked successfully
    def lock_file(self, name, validation_code):
        if self.check_validation_code(name, validation_code):
            self.lock_status[name] = True # Lock
            return True
        return False
    
    # Unlock file: Return True if unlocked successfully
    def unlock_file(self, name, validation_code):
        if self.check_validation_code(name, validation_code):
            self.lock_status[name] = False # Unlock
            return True
        return False
        