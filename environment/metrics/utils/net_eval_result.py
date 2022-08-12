#!/usr/bin/env python3
# -*- coding: utf-8 -*-


class NetEvaluationResult(object):
    def __init__(self, network_score, recv_rate_score, delay_score, loss_rate):
        self.network_score = network_score
        self.recv_rate_score = recv_rate_score
        self.delay_score = delay_score
        self.loss_rate = loss_rate