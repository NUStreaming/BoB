#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import torch
import numpy as np
import time
from torch import nn
from .AC import Actor
from .AC import Critic
from torch.autograd import Variable
from rtc_env import log_to_linear



class PPO:
    def __init__(self, state_dim, action_dim, exploration_param, lr, betas, gamma, ppo_epoch, ppo_clip, use_gae=False):
        self.lr = lr
        self.betas = betas
        self.gamma = gamma
        self.ppo_clip = ppo_clip
        self.ppo_epoch = ppo_epoch
        self.use_gae = use_gae
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.exploration_param = exploration_param
        
        self.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        
        self.policy = Actor(state_dim, action_dim, exploration_param, self.device).to(self.device)
        self.value =  Critic(state_dim, action_dim, exploration_param, self.device).to(self.device)
        self.policy_optimizer = torch.optim.Adam(self.policy.parameters(), lr=lr, betas=betas)
        self.value_optimizer = torch.optim.Adam(self.value.parameters(), lr=lr, betas=betas)
        
        self.policy_old = Actor(state_dim, action_dim, exploration_param, self.device).to(self.device)
        self.value_old = Critic(state_dim, action_dim, exploration_param, self.device).to(self.device)
        #self.policy_old = ActorCritic(state_dim, action_dim, exploration_param, self.device).to(self.device)
        self.policy_old.load_state_dict(self.policy.state_dict())
        self.value_old.load_state_dict(self.value.state_dict())

    def select_action(self, state, storage):
        state = torch.FloatTensor(state.reshape(1, -1)).to(self.device)
        sumall = 0
        actionSelected = []
        aa = 0
        action, action_logprobs = self.policy_old.forward(state)
        value = self.value_old.forward(state)
        
        softmax_action =torch.exp(action)
        #print('====================== ACTION SET', action)
        action = softmax_action.detach().reshape(1, -1)#.tolist()#.tolist()#.round(2.665, 2)#.view(1,-1)#reshape(1, -1)
        sumall = np.sum(action[0].tolist())
        actionSelected = action[0].tolist()/sumall
        #action =   #np.round(action[0],3)
        #print(sumall, actionSelected)
        actionSelected = np.random.choice(4,p=actionSelected)
        #actionSelected = np.where(actionSelected == np.amax(actionSelected))
        storage.logprobs.append(action_logprobs)
        storage.values.append(value)
        storage.states.append(state)
        aa = Variable(torch.Tensor([actionSelected])).to(self.device).detach()
        #print('PPO UPDATE', action[0][actionSelected], actionSelected, aa[0])
        storage.actions.append(log_to_linear(action[0][actionSelected]))#aa[0])#aa[0])#actionSelected) #action[0][actionSelected])#[0][0])
        return action[0][actionSelected], actionSelected #action[0][actionSelected] # action[0][actionSelected]

    def get_value(self, state):
        state = torch.FloatTensor(state.reshape(1, -1)).to(self.device)
        value = self.value_old(state)
        return value

    def update(self, storage, state):
        episode_policy_loss = 0
        episode_value_loss = 0
        if self.use_gae:
            raise NotImplementedError
        advantages = (torch.tensor(storage.returns) - torch.tensor(storage.values)).detach()
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-5)
        #print('SSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSS: ', storage.actions)
        old_states = torch.squeeze(torch.stack(storage.states).to(self.device), 1).detach()
        #print('SSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSS: ', old_states)
        old_actions = torch.stack(storage.actions).to(self.device).detach() #torch.squeeze(torch.stack(storage.actions).to(self.device), 1).detach()
        #print('SSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSS: ', old_actions)
        old_action_logprobs = torch.squeeze(torch.stack(storage.logprobs), 1).to(self.device).detach()
        old_returns = torch.squeeze(torch.stack(storage.returns), 1).to(self.device).detach()        

        for t in range(self.ppo_epoch):
            logprobs, state_values, dist_entropy = self.policy.evaluate(old_states, old_actions, self.policy, self.value) #EvaluateAC(self, old_states, old_actions, self.state_dim, self.action_dim, self.exploration_param, self.device)#self.policy.evaluate(old_states, old_actions, self.state_dim, self.action_dim, self.exploration_param, self.device)#self.policy, self.value)#improt evaluate()
            ratios = torch.exp(logprobs - old_action_logprobs)

            surr1 = ratios * advantages
            surr2 = torch.clamp(ratios, 1-self.ppo_clip, 1+self.ppo_clip) * advantages
            policy_loss = -torch.min(surr1, surr2).mean()
            value_loss = 0.5 * (state_values - old_returns).pow(2).mean()
            loss = policy_loss + value_loss

            self.policy_optimizer.zero_grad()
            loss.backward()
            self.policy_optimizer.step()          
            episode_policy_loss += policy_loss.detach()
            episode_value_loss += value_loss.detach()

        self.policy_old.load_state_dict(self.policy.state_dict())
        return episode_policy_loss / self.ppo_epoch, episode_value_loss / self.ppo_epoch

    def save_model(self, data_path):
        torch.save(self.policy.state_dict(), '{}ppo_{}.pth'.format(data_path, time.strftime("%Y_%m_%d_%H_%M_%S", time.localtime())))
