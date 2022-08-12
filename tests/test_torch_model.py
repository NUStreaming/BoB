#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from BandwidthEstimator_hrcc import Estimator


def using_torch_model(model_path, states):
    BWE = Estimator(model_path)

    assert BWE.get_estimated_bandwidth()
    BWE.report_states(states)
    assert BWE.get_estimated_bandwidth()
    

def test_torch_model():
    model_path = "./model/ppo_2021_06_23_14_12_14.pth"
    states = {
            "send_time_ms": 100,
            "arrival_time_ms": 400,
            "payload_type": 125,
            "sequence_number": 10,
            "ssrc": 123,
            "padding_length": 0,
            "header_length": 120,
            "payload_size": 1350
    }
    using_torch_model(model_path, states)
