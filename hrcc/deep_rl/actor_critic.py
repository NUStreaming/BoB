#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import torch
from torch import nn
from torch.distributions import MultivariateNormal
import torch.nn.functional as F

import numpy as np


class ActorCritic(nn.Module):
    def __init__(self, state_dim, state_length, action_dim, exploration_param=0.05, device="cpu"):
        super(ActorCritic, self).__init__()
        
        self.layer1_shape = 128
        self.layer2_shape = 128
        self.numFcInput = 6144

        self.rConv1d = nn.Conv1d(1, self.layer1_shape, 3)
        self.dConv1d = nn.Conv1d(1, self.layer1_shape, 3)
        self.lConv1d = nn.Conv1d(1, self.layer1_shape, 3)
        self.pConv1d = nn.Conv1d(1, self.layer1_shape, 3)
        self.oConv1d = nn.Conv1d(1, self.layer1_shape, 3)
        self.cConv1d = nn.Conv1d(1, self.layer1_shape, 3)


        self.rConv1d_critic = nn.Conv1d(1, self.layer1_shape, 3)
        self.dConv1d_critic = nn.Conv1d(1, self.layer1_shape, 3)
        self.lConv1d_critic = nn.Conv1d(1, self.layer1_shape, 3)
        self.pConv1d_critic = nn.Conv1d(1, self.layer1_shape, 3)
        self.oConv1d_critic = nn.Conv1d(1, self.layer1_shape, 3)
        self.cConv1d_critic = nn.Conv1d(1, self.layer1_shape, 3)

        self.fc = nn.Linear(self.numFcInput, self.layer2_shape)
        self.actor_output = nn.Linear(self.layer2_shape, action_dim)
        self.critic_output = nn.Linear(self.layer2_shape, 1)
        self.device = device
        self.action_var = torch.full((action_dim,), exploration_param**2).to(self.device)
        self.random_action = False


    def forward(self, inputs):
        # actor
        receivingConv = F.relu(self.rConv1d(inputs[:, 0:1, :]), inplace=True)
        delayConv = F.relu(self.dConv1d(inputs[:, 1:2, :]), inplace=True)
        lossConv = F.relu(self.lConv1d(inputs[:, 2:3, :]), inplace=True)
        predicationConv = F.relu(self.pConv1d(inputs[:, 3:4, :]), inplace=True)
        overusedisConv = F.relu(self.oConv1d(inputs[:, 4:5, :]), inplace=True)
        oversuecapConv = F.relu(self.cConv1d(inputs[:, 5:6, :]), inplace=True)
        receiving_flatten = receivingConv.view(receivingConv.shape[0], -1)
        delay_flatten = delayConv.view(delayConv.shape[0], -1)
        loss_flatten = lossConv.view(lossConv.shape[0], -1)
        predication_flatten = predicationConv.view(predicationConv.shape[0], -1)
        overusedis_flatten = overusedisConv.view( overusedisConv.shape[0], -1)
        oversuecap_flatten = oversuecapConv.view(oversuecapConv.shape[0], -1)

        merge = torch.cat([receiving_flatten, delay_flatten, loss_flatten, predication_flatten,overusedis_flatten,oversuecap_flatten], 1)
        fcOut = F.relu(self.fc(merge), inplace=True)
        action_mean = torch.sigmoid(self.actor_output(fcOut))
        cov_mat = torch.diag(self.action_var).to(self.device)
        dist = MultivariateNormal(action_mean, cov_mat)
        if not self.random_action:
            action = action_mean
        else:
            action = dist.sample()
        action_logprobs = dist.log_prob(action)
        #critic
        receivingConv_critic = F.relu(self.rConv1d_critic(inputs[:, 0:1, :]), inplace=True)
        delayConv_critic = F.relu(self.dConv1d_critic(inputs[:, 1:2, :]), inplace=True)
        lossConv_critic = F.relu(self.lConv1d_critic(inputs[:, 2:3, :]), inplace=True)
        predicationConv_critic = F.relu(self.pConv1d_critic(inputs[:, 3:4, :]), inplace=True)
        overusedisConv_critic = F.relu(self.oConv1d_critic(inputs[:, 4:5, :]), inplace=True)
        oversuecapConv_critic = F.relu(self.cConv1d_critic(inputs[:, 5:6, :]), inplace=True)
        receiving_flatten_critic = receivingConv_critic.view(receivingConv_critic.shape[0], -1)
        delay_flatten_critic = delayConv_critic.view(delayConv_critic.shape[0], -1)
        loss_flatten_critic = lossConv_critic.view(lossConv_critic.shape[0], -1)
        predication_flatten_critic = predicationConv_critic.view(predicationConv_critic.shape[0], -1)
        overusedis_flatten_critic = overusedisConv_critic.view(overusedisConv_critic.shape[0], -1)
        oversuecap_flatten_critic = oversuecapConv_critic.view(oversuecapConv_critic.shape[0], -1)
        merge_critic = torch.cat([receiving_flatten_critic, delay_flatten_critic, loss_flatten_critic,predication_flatten_critic,overusedis_flatten_critic,oversuecap_flatten_critic ], 1)

        fcOut_critic = F.relu(self.fc(merge_critic), inplace=True)
        value = self.critic_output(fcOut_critic)

        return action.detach(), action_logprobs, value, action_mean

    def evaluate(self, state, action):
        _, _, value, action_mean = self.forward(state)
        cov_mat = torch.diag(self.action_var).to(self.device)
        dist = MultivariateNormal(action_mean, cov_mat)

        action_logprobs = dist.log_prob(action)
        dist_entropy = dist.entropy()

        return action_logprobs, torch.squeeze(value), dist_entropy

