import piheaan as heaan
from piheaan.math import approx

import pandas as pd
import numpy as np
import math, os
from tqdm import tqdm
from time import time

class Server:
    def __init__(self):
        # 상수 정의
        self.log_slots = 15
        self.inf1 = 1e+10
        self.inf2 = 1e+15
        self.inf2_inverse = 1e-15
        self.threshold = 0.3
        
        # 데이터를 저장할 딕셔너리 생성
        self.args_dict = {}
        self.eval_dict = {}
        self.data_dict = {}
        
        # 인증정보를 저장할 딕셔너리 생성
        self.validation_code_dict = {}
        self.lock_status = {}
        
    # 계산을 위한 메세지 생성
    def set_msgs_for_calc(self):
        # 첫번째 인덱스만 inf, 나머지 0
        """
        특정 인덱스에 inf 값을 넣기 위한 벡터
        """
        msg_inf = heaan.Message(self.log_slots)
        msg_inf[0] = float(self.inf1)

        # 첫번째 인덱스만 1, 나머지 0
        """
        특정 인덱스만 남기고 나머지를 0으로 초기화하기 위한 벡터
        """
        msg_scalar = heaan.Message(self.log_slots)
        msg_scalar[0] = 1

        # 첫번째 인덱스만 0, 나머지 1
        """
        특정 인덱스 값을 0으로 초기화하기 위한 벡터
        """
        msg_eraser = heaan.Message(self.log_slots)
        self.eval.add(msg_eraser, 1, msg_eraser)
        msg_eraser[0] = 0
        msg_eraser_tmp = heaan.Message(self.log_slots)
        
        self.msgs_for_calc = [msg_inf, msg_scalar, msg_eraser, msg_eraser_tmp]
    
    # 계산을 위한 eval 객체 저장
    def save_eval(self, name, eval_):
        self.eval_dict[name] = eval_
        
    # 계산을 위한 eval 객체 불러오기
    def load_eval(self, name):
        self.eval = self.eval_dict[name]
        
    # Client로부터 받은 인자 저장
    def save_args(self, name, *args):
        self.args_dict[name] = args[0]
        
    # Client로부터 받은 인자 불러오기
    def load_args(self, name):
        self.args = self.args_dict[name]

    # Client로부터 받은 데이터 저장
    def save_data(self, name, data):
        self.data_dict[name] = data

    # Client로부터 받은 데이터 불러오기
    def load_data(self, name):
        data = self.data_dict[name]
        return data

    # bootstrap check
    def check_bootstrap(self, ctxt):
        if ctxt.level == self.eval.min_level_for_bootstrap:
            self.eval.bootstrap(ctxt, ctxt)

    # 두 시계열 간 dtw 거리 계산
    def dtw(self, ctxt_n, ctxt_m):
        n, m = 100, 100
        
        # 변수 초기화
        ctxt_n_tmp, ctxt_m_tmp, ctxt_cost, ctxt_zero, ctxt_left, ctxt_up, ctxt_diagonal, \
        ctxt_min, ctxt_max, ctxt_normalizer, ctxt_result, ctxt_dist_n, ctxt_dist_m = self.args
        msg_inf, msg_scalar, msg_eraser, msg_eraser_tmp = self.msgs_for_calc

        # 계산
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
                
                # min_max 함수에 입력가능한 범위로 변환
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

                # bootstrap check
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

        # 결과값 반환
        """
        1. dtw_matrix[1][m] = dtw 결과값
        2. ctxt_dist_m를 m만큼 이동시켜 dtw 결과값을 첫번째 인덱스로 이동
        3. msg_scaler를 곱해 첫번째 인덱스 값만 남김
        """
        self.eval.left_rotate(ctxt_dist_m, m, ctxt_result)
        self.eval.mult(ctxt_result, msg_scalar, ctxt_result)
        
        return ctxt_result
    
    # 본인 확인하기
    def identification(self, name, input_data):
        # 클라이언트로부터 받은 eval 객체 불러오기
        self.load_eval(name)

        # 클라이언트로부터 받은 인자 불러오기
        self.load_args(name)
        
        # 계산을 위한 메세지 생성
        self.set_msgs_for_calc()
        
        # 클라이언트로부터 받은 인증용 데이터 불러오기
        total_data = self.load_data(name)
        n_data = len(total_data)
        
        # DTW 거리 계산
        total_result = []
        for data in total_data:
            result = self.dtw(data, input_data)
            total_result.append(result)
            
        # 총합 계산
        ctxt_sum = total_result[0]
        for result in total_result[1:]:
            self.eval.add(ctxt_sum, result, ctxt_sum)
            
        # 평균 계산
        ctxt_mean = ctxt_sum
        msg_div = heaan.Message(self.log_slots)
        msg_div[0] = 1 / n_data
        self.eval.mult(ctxt_sum, msg_div, ctxt_mean)
        
        # 임계값 넘을 경우 1, 아닐 경우 0
        ctxt_threshold = self.msgs_for_calc[1]
        ctxt_threshold[0] = self.threshold
        approx.compare(self.eval, ctxt_mean, ctxt_threshold, ctxt_mean)
        
        # 인덱스 1부터 100까지 validation code 입력
        validation_code = np.random.randint(0, 10, 100)
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
    
    # 파일 잠금: True 반환 시 잠금 성공
    def lock_file(self, name, validation_code):
        if self.check_validation_code(name, validation_code):
            self.lock_status[name] = True # 잠금
            return True
        return False
    
    # 파일 잠금 해제: True 반환 시 잠금 해제 성공
    def unlock_file(self, name, validation_code):
        if self.check_validation_code(name, validation_code):
            self.lock_status[name] = False # 잠금 해제
            return True
        return False
        