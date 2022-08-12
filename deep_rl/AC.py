#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import torch
from torch import nn
from torch.distributions import MultivariateNormal
import numpy as np
import torch.nn.functional as F
from torch.autograd import Variable
import math
import random
from rtc_env import log_to_linear

class Actor(nn.Module):
    def __init__(self, state_dim, action_dim, exploration_param=0.05, device="cpu", input_channels=1,output_channels=128, output_size=4):
        super(Actor ,self).__init__() 
        self.cov1 =nn.Conv1d(input_channels,64,kernel_size=3)
        self.cov2 =nn.Conv1d(64, 128,kernel_size=3)
        self.fc1= nn.Linear(515,320)
        self.fc2= nn.Linear(320, 64)
        self.fc3= nn.Linear(64,8)
        self.fc4= nn.Linear(8,output_size)
        self.device = device
        self.action_var = torch.full((output_size,), exploration_param**2).to(self.device) # action_dim change it to output_size
        self.random_action = True

    def forward(self,state):
       reciving_rate = np.array([state[0][0]], dtype=np.float32)
       delay = np.array([state[0][1]], dtype=np.float32)
       packet_loss = np.array([state[0][2]], dtype=np.float32)
       bandwidth = np.array([state[0][3]], dtype=np.float32) 
       
       bandwidth_two = np.zeros([8], dtype=np.float32)
       delay_loss = np.zeros([2], dtype=np.float32)
       for i in range(8):
            bandwidth_two[i] = np.array([state[0][i+3]], dtype=np.float32)
       delay_loss[0] = delay
       delay_loss[1] = packet_loss

       reciving_rate = Variable(torch.from_numpy(reciving_rate))
       delay = Variable(torch.from_numpy(delay))
       packet_loss = Variable(torch.from_numpy(packet_loss))
       bandwidth  = Variable(torch.from_numpy(bandwidth_two))
       reciving_rate = reciving_rate.view(1, -1)
       delay = delay.view(1, -1)
       packet_loss = packet_loss.view(1, -1)
       bandwidth = bandwidth.view(1, 1, -1)
       bandwidth = self.cov1(bandwidth)
       bandwidth = self.cov2(bandwidth)
       bandwidth = bandwidth.view(1, self.num_flat_features(bandwidth)) # this we might remove
       datain = torch.cat((reciving_rate, delay), 1)
       datain = torch.cat((datain, packet_loss), 1)
       datain = torch.cat((datain, bandwidth), 1)
       
       out = F.relu(self.fc1(datain))
       out = F.relu(self.fc2(out))
       out = F.relu(self.fc3(out))
       out = self.fc4(out)
       cov_mat = torch.diag(self.action_var).to(self.device)
       dist = MultivariateNormal(out, cov_mat) 
       action_logprobs = dist.log_prob(out)
       return F.log_softmax(out, dim = 1), action_logprobs
   
    def evaluate(self, state, action, policy_network, value_network):
       action_mean, prob = policy_network(state)
       action_mean_array = []
       actionSelected = []
       sumall = 0
       aa = 0 
       for i in range(0,len(state)):
           action_mean, prob = policy_network(state[i].view(1,-1))
           softmax_action = torch.exp(action_mean)
           action_mean = softmax_action.detach().reshape(1, -1)
           sumall = np.sum(action_mean[0].tolist())
           actionSelected = action_mean[0].tolist()/sumall
           actionSelected = np.random.choice(4,p=actionSelected)
           aa = Variable(torch.Tensor([actionSelected])).to(self.device).detach()
           action_mean_array.append(log_to_linear(action_mean[0][actionSelected]))#aa[0])# aa[0]#action_mean[0][actionSelected])#[0][0].tolist())     


       
       action_mean_array = torch.Tensor(action_mean_array).to(self.device)#.reshape(1,-1)
       cov_mat = torch.diag(self.action_var).to(self.device)     
       dist = MultivariateNormal(action_mean_array.view(-1,1), cov_mat)
       action_logprobs = dist.log_prob(action.view(-1,1).float())
       dist_entropy = dist.entropy()
       value = value_network(state)
       return action_logprobs, torch.squeeze(value), dist_entropy

    def num_flat_features(self,x):
       size = x.size()[1:]
       num_features = 1
       for s in size:
           num_features *= s
       return num_features
   

class Critic(nn.Module):
    def __init__(self, state_dim, action_dim, exploration_param=0.05, device="cpu", input_channels=1,output_channels=128, output_size=1):
        super(Critic ,self).__init__() # values between (,) in each layer might change   
        self.cov1 =nn.Conv1d(input_channels,64,kernel_size=3)
        self.cov2=nn.Conv1d(64,128,kernel_size=3)
        self.fc1=nn.Linear(515,320) # 128 to action_dim
        self.fc2=nn.Linear(320,64)
        self.fc3=nn.Linear(64,8)
        self.fc4=nn.Linear(8,output_size)
        self.device = device
        self.action_var = torch.full((action_dim,), exploration_param**2).to(self.device) # action_dim change it to output_size

    def forward(self,state):
       reciving_rate = np.array([state[0][0]], dtype=np.float32) 
       delay = np.array([state[0][1]], dtype=np.float32)
       packet_loss = np.array([state[0][2]], dtype=np.float32)
       bandwidth = np.array([state[0][3]], dtype=np.float32) 
       bandwidth_two = np.zeros([8], dtype=np.float32)
       for i in range(8):
            bandwidth_two[i] = np.array([state[0][i+3]], dtype=np.float32)#bandwidth[i]
            
       reciving_rate = Variable(torch.from_numpy(reciving_rate))
       delay = Variable(torch.from_numpy(delay))
       packet_loss = Variable(torch.from_numpy(packet_loss))
       bandwidth  = Variable(torch.from_numpy(bandwidth_two))
       # bandwdith_history = Variable(torch.from_numpy(bandwdith_history))
       reciving_rate = reciving_rate.view(1, -1)
       delay = delay.view(1, -1)
       packet_loss = packet_loss.view(1, -1)
       bandwidth = bandwidth.view(1, 1, -1)
       bandwidth = self.cov1(bandwidth) # this we might remove
       bandwidth = self.cov2(bandwidth)
       bandwidth = bandwidth.view(-1, self.num_flat_features(bandwidth)) # this we might remove
       datain = torch.cat((reciving_rate, delay), 1)
       datain = torch.cat((datain, packet_loss), 1)
       datain = torch.cat((datain, bandwidth), 1)
       out = F.relu(self.fc1(datain))
       out = F.relu(self.fc2(out))
       out = F.relu(self.fc3(out))
       out = self.fc4(out)
       #cov_mat = torch.diag(self.action_var).to(self.device)
       #dist = MultivariateNormal(out, cov_mat)
       #action_logprobs = dist.log_prob(out) 
	   
       return out
       
    def evaluate(self, state, action, policy, value):
       action_mean = policy(state) # action_mean = Actor(state)
       cov_mat = torch.diag(self.action_var).to(self.device)
       dist = MultivariateNormal(action_mean, cov_mat)
       action_logprobs = dist.log_prob(action)
       dist_entropy = dist.entropy()
       value = value(state)
       return action_logprobs, torch.squeeze(value), dist_entropy

    def num_flat_features(self,x):
       size = x.size()[1:]
       num_features = 1
       for s in size:
           num_features *= s
       return num_features



