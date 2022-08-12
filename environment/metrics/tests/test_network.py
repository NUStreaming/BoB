#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, json, subprocess
from tempfile import NamedTemporaryFile


cur_dir = os.path.dirname(os.path.abspath(__file__))


def check_network_score(dst_network_log, max_delay):
    file_path = cur_dir + "/../eval_network.py"
    cmd = ["python3", file_path, "--network_eval_method", "normal", "--dst_network_log", dst_network_log, "--max_delay", max_delay]
    cmd_result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf8")
    
    data = json.loads(cmd_result.stdout)
    assert "network" in data
    assert type(data["network"]) == float
    assert data["network"] >= 0 and data["network"] <= 100

    # check output file
    with NamedTemporaryFile('w+t') as output:
        cmd.extend(["--output", output.name])
        cmd_result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf8")

        data = json.loads(output.read())
        assert "network" in data
        assert type(data["network"]) == float
        assert data["network"] >= 0 and data["network"] <= 100


def test_network_score():
    dst_network_log = cur_dir + "/data/alphartc.log"
    test_max_delay = "400"
    check_network_score(dst_network_log, test_max_delay)