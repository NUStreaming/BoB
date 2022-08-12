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
    def __init__(self, model_path=load_active_model(), step_time=60): # Make sure to push model and change the name of the model
        # model parameters
        state_dim = 11
        action_dim = 4
        # the std var of action distribution
        exploration_param = 0.05
        actionSelected = []
        sumall = 0
        FactorH = 1.1
        # load model
        self.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        self.policy = Actor(state_dim, action_dim, exploration_param, self.device).to(self.device)
        self.value =  Critic(state_dim, action_dim, exploration_param, self.device).to(self.device)
        self.policy.load_state_dict(torch.load(model_path))#(self.policy.state_dict())
        #self.value.load_state_dict(torch.load(model_path))
        self.value.load_state_dict(self.value.state_dict())
        #self.model = ActorCritic(state_dim, action_dim, exploration_param, self.device).to(self.device)
        #self.model.load_state_dict(torch.load(model_path))
        # the model to get the input of model
        self.packet_record = PacketRecord()
        self.packet_record.reset()
        self.step_time = step_time
        self.first_arrival_time = 0
        self.last_arrival_time = 0
        # init
        #states = [0.0, 0.0, 0.0, 0.
        self.bandwdith_list_state =  deque([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        states = np.append([0.0, 0.0, 0.0],self.bandwdith_list_state)
        '''
        torch_tensor_states = torch.FloatTensor(torch.Tensor(states).reshape(1, -1)).to(self.device)
        action, action_logprobs, value = self.model.forward(torch_tensor_states)
        self.bandwidth_prediction = log_to_linear(action)
        self.last_call = "init"
        '''
        torch_tensor_states = torch.FloatTensor(torch.Tensor(states).reshape(1, -1)).to(self.device)
        action, action_logprobs = self.policy.forward(torch_tensor_states)
        value = self.value.forward(torch_tensor_states)

        softmax_action = torch.exp(action)
        action = softmax_action.detach().reshape(1, -1)
        sumall = np.sum(action[0].tolist())
        actionSelected = action[0].tolist()/sumall
        actionSelected = np.random.choice(4,p=actionSelected)

        self.bandwidth_prediction = log_to_linear(action[0][actionSelected])
        self.last_call = "init"

        #heuristic
        self.heuristic_estimator = HeuristicEstimator()
        self.delay = 0
        self.loss_ratio = 0

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
            global FactorH
            states = []
            receiving_rate = self.packet_record.calculate_receiving_rate(interval=self.step_time)
            states.append(liner_to_log(receiving_rate))
            previousDelay = self.delay
            self.delay = self.packet_record.calculate_average_delay(interval=self.step_time)
            #states.append(min(self.delay/1000, 1))
            states.append(self.delay/1000)
            previousLossRatio = self.loss_ratio
            self.loss_ratio = self.packet_record.calculate_loss_ratio(interval=self.step_time)
            states.append(self.loss_ratio)

            heuristic_prediction, heuristic_overuse_flag = self.heuristic_estimator.get_estimated_bandwidth()
            heuristic_prediction = heuristic_prediction * FactorH #1.10 #FactorH #1.10

            for l in self.bandwdith_list_state:
                states.append(l)
                
            #latest_prediction = self.packet_record.calculate_latest_prediction()
            BW_state = liner_to_log(heuristic_prediction)
            self.bandwdith_list_state.popleft()
            self.bandwdith_list_state.append(BW_state)

            #states.append(liner_to_log(heuristic_prediction))
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
            MinactionSelected = actionSelected
            MinactionSelected = np.where(MinactionSelected == np.amin(MinactionSelected))
            actionSelected = np.random.choice(4,p=actionSelected)
            # update prediction of bandwidth by using action
            learningBasedBWE = log_to_linear(pow(2, (2 * action[0][actionSelected] - 1))).item()
            #MinactionSelected = np.where(MinactionSelected == np.amin(action[0].tolist()/sumall)) 
            FactorH = 1 - (action[0][MinactionSelected]).item()/2  # 1.02 - (action[0][actionSelected]).item()/2  # test with directly 0.8 and with min action +-  #pow(2, (2 * action[0][actionSelected] - 1)).item() + 1
            #FactorH = (action[0][actionSelected]).item() + 0.8
            self.bandwidth_prediction = learningBasedBWE
            isHeuristicUsed=False

            diff_predictions = abs(int(self.bandwidth_prediction) - int(heuristic_prediction))
            average_predictions = (int(self.bandwidth_prediction) + int(heuristic_prediction)) / 2
            percentage = diff_predictions / average_predictions
            if percentage >= 0.3:
                self.bandwidth_prediction = heuristic_prediction
                if self.delay - previousDelay < 200:   
                    FactorH = (action[0][actionSelected]).item() + 0.85
                isHeuristicUsed=True

            #self.bandwidth_prediction = log_to_linear(percentage)
            #self.bandwidth_prediction = min(self.bandwidth_prediction,MAX_BANDWIDTH_MBPS*UNIT_M)
            #self.bandwidth_prediction = max(self.bandwidth_prediction,MIN_BANDWIDTH_MBPS*UNIT_M)

            self.heuristic_estimator.change_bandwidth_estimation(self.bandwidth_prediction)
            logging.debug("time:"+str(self.last_arrival_time - self.first_arrival_time)+" actual_bw:"+str(receiving_rate)+" predicted_bw:"+str(self.bandwidth_prediction)+ " isHeuristicUsed:"+str(isHeuristicUsed)+ " heuristic_overuse_flag:"+str(heuristic_overuse_flag)+ " HeuristicBW:" +str(heuristic_prediction) + " learningBW:" + str(learningBasedBWE)+" Actions:"+str(action)+" SelectedActionIdx:"+str(actionSelected)+" SeletedAction:"+str(action[0][actionSelected])+" Percentage:"+str(percentage)+" FactorH:"+str(FactorH))
        return self.bandwidth_prediction