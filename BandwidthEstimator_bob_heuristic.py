#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import torch
import numpy as np
from utils.packet_info import PacketInfo
from utils.packet_record import PacketRecord
#from deep_rl.actor_critic import ActorCritic
from deep_rl.ppo_AC import Actor
from deep_rl.ppo_AC import Critic
from collections import deque
from BandwidthEstimator_heuristic import HeuristicEstimator
import logging

UNIT_M = 1000000
MAX_BANDWIDTH_MBPS = 8
MIN_BANDWIDTH_MBPS = 0.01
LOG_MAX_BANDWIDTH_MBPS = np.log(MAX_BANDWIDTH_MBPS)
LOG_MIN_BANDWIDTH_MBPS = np.log(MIN_BANDWIDTH_MBPS)
#global FactorH
FactorH = 1.10

logging.basicConfig(filename='bandwidth_estimator.log', level=logging.DEBUG)

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

def load_active_model(active_model_file='active_model'):
    with open(active_model_file, 'r') as f:
        try:
            model=f.read().strip()
            logging.debug("Using model="+model)
        except Exception as ex:
            logging.debug("Couldn't find active model using default value! Exception:" + ex)
            model='./model/bob.pth'
    return model

class Estimator(object):
    def __init__(self, model_path=load_active_model(), step_time=120): # Make sure to push model and change the name of the model
        self.packet_record = PacketRecord()
        self.packet_record.reset()
        self.step_time = step_time
        self.first_arrival_time = 0
        self.last_arrival_time = 0

        self.bandwidth_prediction = 0
        self.last_call = "init"

        #heuristic
        self.heuristic_estimator = HeuristicEstimator()

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
        self.heuristic_estimator.report_states(stats)

    def get_estimated_bandwidth(self)->int:
        if self.last_call and self.last_call == "report_states":
            self.last_call = "get_estimated_bandwidth"
            # calculate state
            receiving_rate = self.packet_record.calculate_receiving_rate(interval=self.step_time)
            heuristic_prediction, heuristic_overuse_flag = self.heuristic_estimator.get_estimated_bandwidth()
            
            self.bandwidth_prediction = heuristic_prediction
            isHeuristicUsed=True

            #self.bandwidth_prediction = log_to_linear(percentage)
            #self.bandwidth_prediction = min(self.bandwidth_prediction,MAX_BANDWIDTH_MBPS*UNIT_M)
            #self.bandwidth_prediction = max(self.bandwidth_prediction,MIN_BANDWIDTH_MBPS*UNIT_M)

            logging.debug("time:"+str(self.last_arrival_time - self.first_arrival_time)+" actual_bw:"+str(receiving_rate)+" predicted_bw:"+str(self.bandwidth_prediction)+ " isHeuristicUsed:"+str(isHeuristicUsed)+ " HeuristicBW:" +str(heuristic_prediction))
        return self.bandwidth_prediction