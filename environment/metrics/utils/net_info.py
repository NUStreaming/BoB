#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, json


class NetInfo(object):
    def __init__(self, net_path):
        self.net_path = net_path
        self.net_data = None

        self.parse_net_log()

    def parse_net_log(self):
        if  not self.net_path or not os.path.exists(self.net_path):
            raise ValueError("Error net path")

        ret = []
        with open(self.net_path, 'r') as f:
            for line in f.readlines():
                if ("remote_estimator_proxy.cc" not in line):
                    continue
                try:
                    raw_json = line[line.index('{'):]
                    json_network = json.loads(raw_json)
                    # it seems no use
                    del json_network["mediaInfo"]
                    ret.append(json_network)
                # can not parser json
                except ValueError as e:
                    pass
                # other exception that need to care
                except Exception as e:
                    raise ValueError("Exception when parser json log")
                    
        self.net_data = ret