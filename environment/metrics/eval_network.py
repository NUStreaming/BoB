#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse, json
import numpy as np
from utils.net_info import NetInfo
from utils.net_eval_method import NetEvalMethod, NetEvalMethodNormal


description = \
'''
This script provide multi methods to evaluate network quality.
'''


class NetworkEvaluation():
    def __init__(self, eval_method : NetEvalMethod, args):
        self.eval_method = eval_method
        self.args = args

    def eval(self, dst_network_path):
        dst_network_info = NetInfo(dst_network_path)
        ret = self.eval_method.eval(dst_network_info)

        return ret


def get_network_score(args):
    eval_method = None

    if args.network_eval_method == "normal":
        eval_method = NetEvalMethodNormal(args.max_delay, args.ground_recv_rate)
    else:
        raise ValueError("Not supoort such method to evaluate network")
    
    network_eval_tool = NetworkEvaluation(eval_method, args)
    network_out = network_eval_tool.eval(args.dst_network_log)

    return network_out


def init_network_argparse():
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--output", type=str, default=None, help="the path of output file. It will print the result in terminal if you don't specify its value.")
    # for network evaluation
    parser.add_argument("--network_eval_method", type=str, default="normal", choices=["normal"], help="the method to evaluate network.")
    parser.add_argument("--dst_network_log", type=str, required=True, default=None, help="the path of network log.")
    parser.add_argument("--max_delay", type=float, default=400, help="the max packet delay.")
    parser.add_argument("--ground_recv_rate", type=float, default=500, help="the receive rate of a special scenario ground truth.")

    return parser
    

if __name__ == "__main__":
    parser = init_network_argparse()
    args = parser.parse_args()
    out_dict = {}    
    netEvalResult=get_network_score(args);
    out_dict["network"] = netEvalResult.network_score
    out_dict["recv_rate_score"] = netEvalResult.recv_rate_score
    out_dict["delay_score"] = netEvalResult.delay_score
    out_dict["loss_rate"] = netEvalResult.loss_rate
        
    if args.output:
        with open(args.output, 'w') as f:
            f.write(json.dumps(out_dict))
    else:
        print(json.dumps(out_dict))
