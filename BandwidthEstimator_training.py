#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import torch
import numpy as np
import sys
import os
#from utils.packet_info import PacketInfo
#from utils.packet_record import PacketRecord
#from deep_rl.actor_critic import ActorCritic
from deep_rl.AC import Actor
from deep_rl.AC import Critic
import gym
from gym import spaces

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "gym"))
import alphartc_gym
from alphartc_gym.utils.packet_info import PacketInfo
from alphartc_gym.utils.packet_record import PacketRecord
from BandwidthEstimator_heuristic import HeuristicEstimator


UNIT_M = 1000000
MAX_BANDWIDTH_MBPS = 8
MIN_BANDWIDTH_MBPS = 0.01
LOG_MAX_BANDWIDTH_MBPS = np.log(MAX_BANDWIDTH_MBPS)
LOG_MIN_BANDWIDTH_MBPS = np.log(MIN_BANDWIDTH_MBPS)


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
    def __init__(self, model_path="./data/ppo_2021_06_23_14_12_14.pth", step_time=60):
        # model parameters
        state_dim = 11
        action_dim = 4
        # the std var of action distribution
        exploration_param = 0.05
        actionSelected = []
        sumall = 0
        # load model
        self.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        #self.model = ActorCritic(state_dim, action_dim, exploration_param, self.device).to(self.device)
        #self.model.load_state_dict(torch.load(model_path))

        self.policy = Actor(state_dim, action_dim, exploration_param, self.device).to(self.device)
        self.value =  Critic(state_dim, action_dim, exploration_param, self.device).to(self.device)
        
        self.policy.load_state_dict(self.policy.state_dict())
        self.value.load_state_dict(self.value.state_dict())

        # the model to get the input of model
        self.packet_record = PacketRecord()
        self.packet_record.reset()
        self.step_time = step_time
        # init
        self.bandwdith_list_state =  deque([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        states = np.append([0.0, 0.0, 0.0],self.bandwdith_list_state)
        torch_tensor_states = torch.FloatTensor(torch.Tensor(states).reshape(1, -1)).to(self.device)
        action, action_logprobs = self.policy.forward(torch_tensor_states)
        value = self.value.forward(torch_tensor_states)

        softmax_action = torch.exp(action)
        action = softmax_action.detach().reshape(1, -1)
        sumall = np.sum(action[0].tolist())
        actionSelected = action[0].tolist()/sumall
        actionSelected = np.random.choice(4,p=actionSelected)

        self.heuristic_estimator = HeuristicEstimator()
        self.bandwidth_prediction = log_to_linear(action[0][actionSelected])
        self.last_call = "init"

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
            #latest_prediction = self.packet_record.calculate_latest_prediction()
            latest_prediction, overuse_flag = self.heuristic_estimator.get_estimated_bandwidth()
            BW_state = liner_to_log(latest_prediction)
            for l in self.bandwdith_list_state:
                states.append(l)
            self.bandwdith_list_state.popleft()
            self.bandwdith_list_state.append(BW_state)

            states.append(liner_to_log(latest_prediction))
            #delay_interval = self.packet_record.calculate_delay_interval(interval=self.step_time)
            #states.append(min(delay_interval/1000,1))
            # make the states for model
            torch_tensor_states = torch.FloatTensor(torch.Tensor(states).reshape(1, -1)).to(self.device)
            # get model output
            #action, action_logprobs, value = self.model.forward(torch_tensor_states)
            action, action_logprobs = self.policy.forward(torch_tensor_states)
            value = self.value.forward(torch_tensor_states)
            softmax_action = torch.exp(action)
            action = softmax_action.detach().reshape(1, -1)
            sumall = np.sum(action[0].tolist())
            actionSelected = action[0].tolist()/sumall
            actionSelected = np.random.choice(4,p=actionSelected)
            # update prediction of bandwidth by using action
            self.bandwidth_prediction = log_to_linear(action[0][actionSelected])
            print(self.bandwidth_prediction)
        return self.bandwidth_prediction
