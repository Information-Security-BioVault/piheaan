import piheaan as heaan
from piheaan.math import approx

import pandas as pd
import numpy as np
import math, os
from tqdm import tqdm
from time import time

class Client:
    def __init__(self, name):
        # set parameters
        self.key_file_path = f"./keys/{name}"
        params = heaan.ParameterPreset.FGb
        self.context = heaan.make_context(params) # context has paramter information
        heaan.make_bootstrappable(self.context) # make parameter bootstrapable
        self.log_slots = 15
    
    def create_keys(self):
        # create and save keys
        sk = heaan.SecretKey(self.context) # create secret key
        os.makedirs(self.key_file_path, mode=0o775, exist_ok=True)
        sk.save(self.key_file_path+"/secretkey.bin") # save secret key

        key_generator = heaan.KeyGenerator(self.context, sk) # create public key
        key_generator.gen_common_keys()
        key_generator.save(self.key_file_path+f"/") # save public key
    
    def load_keys(self):
        # load secret key and public key
        # When a key is created, it can be used again to save a new key without creating a new one
        self.sk = heaan.SecretKey(self.context, self.key_file_path+"/secretkey.bin") # load secret key
        self.pk = heaan.KeyPack(self.context, self.key_file_path+"/") # load public key
        self.pk.load_enc_key()
        self.pk.load_mult_key()

        self.eval = heaan.HomEvaluator(self.context,self.pk) # to load piheaan basic function
        self.dec = heaan.Decryptor(self.context) # for decrypt
        self.enc = heaan.Encryptor(self.context) # for encrypt
        
    # 암호화
    def encrypt(self, data):
        # Create message
        msg = heaan.Message(self.log_slots)
        self.len = len(data)
        for i in range(self.len):
            msg[i] = data[i]
        
        # Encrypt message
        ctxt = heaan.Ciphertext(self.context)
        self.enc.encrypt(msg, self.pk, ctxt)
        return ctxt
         
    # 복호화         
    def decrypt(self, ctxt):
        # Decrypt
        msg = heaan.Message(self.log_slots)
        self.dec.decrypt(ctxt, self.sk, msg)
        return msg
    
    # 결과 확인
    def check_result(self, ctxt):
        result_code = self.decrypt(ctxt)[0].real
        if result_code == 1:
            print("본인이 확인되었습니다.")
        else:
            print("본인이 아닙니다.")
        return result_code
      
    # 계산을 위한 벡터 생성
    def set_args(self):
        # 계산을 위한 벡터
        ctxt_n_tmp = heaan.Ciphertext(self.context)
        ctxt_m_tmp = heaan.Ciphertext(self.context)
        ctxt_cost = heaan.Ciphertext(self.context)
        ctxt_zero = heaan.Ciphertext(self.context)
        ctxt_left = heaan.Ciphertext(self.context)
        ctxt_up = heaan.Ciphertext(self.context)
        ctxt_diagonal = heaan.Ciphertext(self.context)
        ctxt_min = heaan.Ciphertext(self.context)
        ctxt_max = heaan.Ciphertext(self.context)
        ctxt_normalizer = heaan.Ciphertext(self.context)
        ctxt_result = heaan.Ciphertext(self.context)
        
        # 거리 행렬 생성
        msg_dist_n = heaan.Message(self.log_slots)
        msg_dist_m = heaan.Message(self.log_slots)
        for i in range(100+1):
            msg_dist_n[i] = float(1e+10)
            msg_dist_m[i] = float(1e+10)
        msg_dist_n[0] = 0
        ctxt_dist_n = heaan.Ciphertext(self.context)
        ctxt_dist_m = heaan.Ciphertext(self.context)
        self.enc.encrypt(msg_dist_n, self.pk, ctxt_dist_n)
        self.enc.encrypt(msg_dist_m, self.pk, ctxt_dist_m)
        
        self.args = ctxt_n_tmp, ctxt_m_tmp, ctxt_cost, ctxt_zero, ctxt_left, ctxt_up, ctxt_diagonal, \
                    ctxt_min, ctxt_max, ctxt_normalizer, ctxt_result, ctxt_dist_n, ctxt_dist_m
    
