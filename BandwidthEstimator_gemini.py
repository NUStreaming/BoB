#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import torch
import numpy as np
from gemini.utils.packet_info import PacketInfo
from gemini.utils.packet_record import PacketRecord
from gemini.deep_rl.actor_critic import ActorCritic
import logging

from gemini.gcc.delaybasedbwe import bwe_result
from gemini.gcc.delaybasedbwe import delay_base_bwe
from gemini.gcc.delaybasedbwe import get_time_ms
from gemini.gcc.ack_bitrate_estimator import Ack_bitrate_estimator

UNIT_M = 1000000
MAX_BANDWIDTH_MBPS = 20 #新版本模型需要修改
MIN_BANDWIDTH_MBPS = 0.08
LOG_MAX_BANDWIDTH_MBPS = np.log(MAX_BANDWIDTH_MBPS)
LOG_MIN_BANDWIDTH_MBPS = np.log(MIN_BANDWIDTH_MBPS)

logging.basicConfig(filename='bandwidth_estimator.log', level=logging.DEBUG)

class unsafety_detector: #
    def __init__(self, window_size=20):
        self.window_size=window_size
        self.index = 0
        self.arrival_delta_list = [0.0 for _ in range(self.window_size)]
        self.last_D=1
        self.gamma=1
        self.state=1 # 1/0 1:DL;0:GCC
        self.k=0.5

        self.change_window=10 # 进行一次切换之后十次之后再改变


        self.last_recv=None
        self.last_send=None

        self.last_result=0

        # # ## 用于测试 
        # self.state=1
        # self.change_window=10
        # print("测试,state 恒定") 
    def receive(self,recv,send):
        if self.last_recv==None:
            self.last_recv=recv
            self.last_send=send
        else:
            recv_delta_ms=recv-self.last_recv
            send_delta_ms=send-self.last_send
            self.update(recv_delta_ms,send_delta_ms)
            self.last_recv=recv
            self.last_send=send    
    def update(self,recv_delta_ms, send_delta_ms, arrival_ts=0):
        
        delta_ms=recv_delta_ms-send_delta_ms

        # mean_delta=0
        if delta_ms>0:
            self.index+=1
            self.last_D=self.last_D*1/2+delta_ms
            self.gamma=self.gamma+self.k*(self.last_D-self.gamma) 
        #print(delta_ms)

            if self.state==1:
                if self.last_D>self.gamma and self.last_result>=0:
                    self.change_window-=1
                    if self.change_window==0:
                        self.state=0
            else:
                if self.last_D<=self.gamma and self.last_result<=0:
                    self.change_window-=1
                elif self.last_D>self.gamma and self.last_result>=0:
                    self.change_window+=1
                    self.change_window=min(10,self.change_window)
                    if self.change_window==0:
                        self.state=1



            if self.change_window==0:
                self.change_window=10
        #print("state",self.state)
            self.last_result=self.last_D-self.gamma

        # ## 用于测试 
        # self.state=1
        # self.change_window=10
        # print("state",self.state)
        # if self.state==0:
        #     print(self.change_window)
        return self.state
    def reset(self):
        # self.window_size=window_size
        self.index = 0
        self.arrival_delta_list = [0.0 for _ in range(self.window_size)]
        self.last_D=200
        self.gamma=1
        self.state=1 # 1/0 1:DL;0:GCC
        self.k=0.5

        self.change_window=10 # 进行一次切换之后十次之后再改变

        self.last_recv=None
        self.last_send=None
    def detect_big_delay(self):
        self.change_window=10
        self.state=0
        # ## 用于测试 
        # self.state=1
        # self.change_window=10
def liner_to_log(value):
    # from 10kbps~8Mbps to 0~1
    value = np.clip(value / UNIT_M, MIN_BANDWIDTH_MBPS, MAX_BANDWIDTH_MBPS)
    log_value = np.log(value)
    return (log_value - LOG_MIN_BANDWIDTH_MBPS) / (LOG_MAX_BANDWIDTH_MBPS - LOG_MIN_BANDWIDTH_MBPS)


def log_to_linear(value):
    # from 0~1 to 10kbps to 8Mbps
    value = np.clip(value, 0, 1)
    log_bwe = value * (LOG_MAX_BANDWIDTH_MBPS - LOG_MIN_BANDWIDTH_MBPS) + LOG_MIN_BANDWIDTH_MBPS
    return np.exp(log_bwe) * UNIT_M


class Estimator(object):
    def __init__(self, model_path="./model/ppo_gemini_2021_07_20_09_15_37.pth", step_time=60):
        # model parameters
        state_dim = 5
        action_dim = 1
        # the std var of action distribution
        exploration_param = 0.05
        # load model
        self.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        self.model = ActorCritic(state_dim, action_dim, exploration_param, self.device).to(self.device)
        self.model.load_state_dict(torch.load(model_path))
        # the model to get the input of model
        self.packet_record = PacketRecord()
        self.packet_record.reset()
        self.step_time = step_time
        self.first_arrival_time = 0
        self.last_arrival_time = 0
        # init
        states = [0.0, 0.0, 0.0, 0.0,0.0]
        torch_tensor_states = torch.FloatTensor(torch.Tensor(states).reshape(1, -1)).to(self.device)
        action, action_logprobs, value = self.model.forward(torch_tensor_states)
        self.bandwidth_prediction = log_to_linear(action)
        self.last_call = "init"
        #self.last_bandwidth_prediction=self.bandwidth_prediction
        self.latest_bandwidth=300000
        self.first_time = get_time_ms()
        self.gcc_rate_controller = delay_base_bwe()
        self.gcc_rate_controller.set_time(self.first_time)
        self.gcc_rate_controller.set_start_bitrate(self.latest_bandwidth)
        self.gcc_ack_bitrate = Ack_bitrate_estimator()
        self.gcc_bitrate = self.latest_bandwidth
        self.unsafety_dector=unsafety_detector()
        self.last_time=None
        self.safety = 1


    def report_states(self, stats: dict):
        '''
        stats is a dict with the following items
        {
            "send_time_ms": uint,
            "arrival_time_ms": uint,
            "payload_type": int,
            "sequence_number": uint,
            "ssrc": int,
            "padding_length": uint,
            "header_length": uint,
            "payload_size": uint
        }
        '''
        if self.last_arrival_time != 0:
            self.step_time = stats["arrival_time_ms"] - self.last_arrival_time
        else:
            self.first_arrival_time = stats["arrival_time_ms"]
        self.last_arrival_time = stats["arrival_time_ms"]        

        self.last_call = "report_states"
        packet_list=[]
        packet_list.append(stats)
        # packet_list=self.packet_list
        length_packet = len(packet_list)
        gcc_bitrate = 0
        if length_packet > 0:
            now_ts = get_time_ms() - self.first_time
            self.gcc_ack_bitrate.ack_estimator_incoming(packet_list)
            result = self.gcc_rate_controller.delay_bwe_incoming(
            packet_list, self.gcc_ack_bitrate.ack_estimator_bitrate_bps(),
            now_ts) 
            gcc_bitrate = result.bitrate
        if gcc_bitrate != 0:
           self.gcc_bitrate = gcc_bitrate
        
        
               
        # clear data
        packet_info = PacketInfo()
        packet_info.payload_type = stats["payload_type"]
        packet_info.ssrc = stats["ssrc"]
        packet_info.sequence_number = stats["sequence_number"]
        packet_info.send_timestamp = stats["send_time_ms"]
        packet_info.receive_timestamp = stats["arrival_time_ms"]
        packet_info.padding_length = stats["padding_length"]
        packet_info.header_length = stats["header_length"]
        packet_info.payload_size = stats["payload_size"]
        packet_info.bandwidth_prediction = self.bandwidth_prediction

        self.packet_record.on_receive(packet_info)
        self.unsafety_dector.receive(packet_info.receive_timestamp,packet_info.send_timestamp)

    def get_estimated_bandwidth(self)->int:
        if self.last_call and self.last_call == "report_states":
            self.last_call = "get_estimated_bandwidth"
            # calculate state
            states = []
            receiving_rate = self.packet_record.calculate_receiving_rate(interval=self.step_time)
            states.append(liner_to_log(receiving_rate))
            
            delay = self.packet_record.calculate_average_delay(interval=self.step_time)
            states.append(min(delay/1000, 1))
            
            loss_ratio = self.packet_record.calculate_loss_ratio(interval=self.step_time)
            states.append(loss_ratio)
            
            latest_prediction = self.packet_record.calculate_latest_prediction()
            states.append(liner_to_log(latest_prediction))
            
            # delta_prediction = abs(self.bandwidth_prediction-self.latest_bandwidth).squeeze().numpy()# 原来的是[[x]]现在先压平然后转换成numpy

            if self.safety==1:
                delta_prediction = abs((self.bandwidth_prediction - self.latest_bandwidth
            )).squeeze().numpy()  # 原来的是[[x]]现在先压平然后转换成numpy
            else:
                delta_prediction=abs((self.bandwidth_prediction - self.latest_bandwidth
            )) # 单位是百分比            
            states.append(liner_to_log(delta_prediction))
            # make the states for model
            torch_tensor_states = torch.FloatTensor(torch.Tensor(states).reshape(1, -1)).to(self.device)
            # get model output
            action, action_logprobs, value = self.model.forward(torch_tensor_states)
            
            self.latest_bandwidth=self.bandwidth_prediction
            
            bandwidth_prediction_dl = log_to_linear(action)
            bandwidth_prediction=bandwidth_prediction_dl
            if self.safety == 1:
                bandwidth_prediction=bandwidth_prediction_dl
                self.bandwidth_prediction=bandwidth_prediction
            else:
                bandwidth_prediction_gcc=self.gcc_bitrate
                bandwidth_prediction=bandwidth_prediction_gcc
                
                if self.unsafety_dector.change_window!=10 and self.unsafety_dector.change_window!=0:
                    window=self.unsafety_dector.change_window
                    bandwidth_prediction=bandwidth_prediction_dl*((10-window)/10)+bandwidth_prediction_gcc*(window/10)
                self.bandwidth_prediction=bandwidth_prediction
            
            if delay>1000:
                self.unsafety_dector.detect_big_delay()          
            self.safety=self.unsafety_dector.state    
            # update prediction of bandwidth by using action
            #self.latest_bandwidth=self.bandwidth_prediction
            # self.bandwidth_prediction = log_to_linear(action)
        result=min(self.bandwidth_prediction,MAX_BANDWIDTH_MBPS*UNIT_M)
        result=max(result,MIN_BANDWIDTH_MBPS*UNIT_M)

        result_log = result
        if hasattr(result_log, 'item'):
            result_log=result_log.item()
        logging.debug("time:"+str(self.last_arrival_time - self.first_arrival_time)+" actual_bw:"+str(receiving_rate)+" predicted_bw:"+str(result_log))
        return result
