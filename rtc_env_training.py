#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import random
import numpy as np
import glob

import gym
from gym import spaces

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "gym"))
import alphartc_gym
from alphartc_gym.utils.packet_info import PacketInfo
from alphartc_gym.utils.packet_record import PacketRecord
from collections import deque


UNIT_M = 1000000
MAX_BANDWIDTH_MBPS = 8
MIN_BANDWIDTH_MBPS = 0.01
LOG_MAX_BANDWIDTH_MBPS = np.log(MAX_BANDWIDTH_MBPS)
LOG_MIN_BANDWIDTH_MBPS = np.log(MIN_BANDWIDTH_MBPS)
receiving_rate_old = 0.1
REWARD_USE = ['R1','R2','R3','R4','R5','R6']
fillTable = True


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

def makeSelection(p):
    index= np.where(p==np.max(p))
    choice=np.zeros(4)
    for i in range(len(choice)):
        if(i==index[0][0]):
            choice[i]=0.9
        else:
            choice[i]=0.1/3
    action=np.random.choice(4,p=choice)
    #return np.random.choice(4,choice)
    return action



class GymEnv:
    def __init__(self, step_time=60): # every one minutes
        self.gym_env = None     
        self.step_time = step_time
        trace_dir = os.path.join(os.path.dirname(__file__), "traces")
        self.trace_set = glob.glob(f'{trace_dir}/**/*.json', recursive=True)
        self.action_space = spaces.Box(low=0.0, high=1.0, shape=(1,), dtype=np.float64)
        self.observation_space = spaces.Box(
            low=np.array([0.0, 0.0, 0.0, 0.0, 0.0]),
            high=np.array([1.0, 1.0, 1.0, 1.0, 1.0]),
            dtype=np.float64)
        #fillTable = True
        self.bandwdith_list_state =  deque([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]) #np.zeros([8], dtype=np.float32)
        self.BW = np.zeros([8], dtype=np.float32)
    def reset(self):
        self.gym_env = alphartc_gym.Gym()
        self.gym_env.reset(trace_path=random.choice(self.trace_set),
            report_interval_ms=self.step_time,
            duration_time_ms=0)
        self.packet_record = PacketRecord()
        self.packet_record.reset()
        return np.append([0.0, 0.0, 0.0],self.bandwdith_list_state)

    def step(self, action):
        bandwidth_prediction = log_to_linear(action)
        # run the action
        packet_list, done = self.gym_env.step(bandwidth_prediction)
        for pkt in packet_list:
            packet_info = PacketInfo()
            packet_info.payload_type = pkt["payload_type"]
            packet_info.ssrc = pkt["ssrc"]
            packet_info.sequence_number = pkt["sequence_number"]
            packet_info.send_timestamp = pkt["send_time_ms"]
            packet_info.receive_timestamp = pkt["arrival_time_ms"]
            packet_info.padding_length = pkt["padding_length"]
            packet_info.header_length = pkt["header_length"]
            packet_info.payload_size = pkt["payload_size"]
            packet_info.bandwidth_prediction = bandwidth_prediction
            self.packet_record.on_receive(packet_info)

        # calculate state
        states = []
        receiving_rate = self.packet_record.calculate_receiving_rate(interval=self.step_time)
        receiving_rate_state = liner_to_log(receiving_rate)
        states.append(receiving_rate_state)
        delay = self.packet_record.calculate_average_delay(interval=self.step_time)
        delay_state = min(delay/1000, 1)
        states.append(delay_state)
        loss_ratio = self.packet_record.calculate_loss_ratio(interval=self.step_time)
        states.append(loss_ratio)
        latest_prediction = self.packet_record.calculate_latest_prediction()
        BW_state = liner_to_log(latest_prediction)
        for l in self.bandwdith_list_state:
            states.append(l)
        self.bandwdith_list_state.popleft()
        self.bandwdith_list_state.append(BW_state)

        #print('Feautres: receiving_rate {}, delay {}, loss_ration {}, BW_pred {}', receiving_rate, delay, loss_ratio, latest_prediction)

        RewardFunction = 'R2'
        if RewardFunction == REWARD_USE[0]:
            reward = states[0] - states[1] - states[2] 
        elif RewardFunction == REWARD_USE[1]:
            reward = receiving_rate - delay - loss_ratio
        elif RewardFunction == REWARD_USE[2]:
            reward = 0.6*np.log(4*states[0]+1) - 10*states[1] - 10*states[2]
        elif RewardFunction == REWARD_USE[3]:
            reward = 0.6*np.log(4*receiving_rate + 1) - 10*delay - 10*loss_ratio#10*delay - 10*loss_ratio #- delay_interval]:
        elif RewardFunction == REWARD_USE[4]:
            reward = 0.0622*states[0] - 0.000639*states[1] + 3.30
        else:
            reward = 0.0622*receiving_rate - 0.000639*delay + 3.30


        receiving_rate_old = latest_prediction

        return states, reward, done, {}
