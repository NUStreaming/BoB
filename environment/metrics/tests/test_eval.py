#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, json, pytest, subprocess
from tempfile import NamedTemporaryFile


# path of test data
cur_dir = os.path.dirname(os.path.abspath(__file__))
file_path = cur_dir + "/../eval.py"
video_y4m_path = cur_dir + "/data/test.y4m"
video_yuv_path = cur_dir + "/data/test.yuv"
audio_path = cur_dir + "/data/test.wav"
dst_network_log = cur_dir + "/data/alphartc.log"


def run_and_check_result(cmd):
    cmd_result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf8")
    
    data = json.loads(cmd_result.stdout)
    assert "video" in data
    assert type(data["video"]) == float
    assert data["video"] >= 0 and data["video"] <= 100
    assert "audio" in data
    assert type(data["audio"]) == float
    assert data["audio"] >= 0 and data["audio"] <= 100
    assert "network" in data
    assert type(data["network"]) == float
    assert data["network"] >= 0 and data["network"] <= 100

    # check output file
    with NamedTemporaryFile('w+t') as output:
        cmd.extend(["--output", output.name])
        cmd_result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf8")

        data = json.loads(output.read())
        assert "video" in data
        assert type(data["video"]) == float
        assert data["video"] >= 0 and data["video"] <= 100
        assert "audio" in data
        assert type(data["audio"]) == float
        assert data["audio"] >= 0 and data["audio"] <= 100
        assert "network" in data
        assert type(data["network"]) == float
        assert data["network"] >= 0 and data["network"] <= 100


def check_video_score(src_video, dst_video, audio_path, dnsmos_uri, dnsmos_key, dst_network_log):
    cmd = ["python3", file_path, "--src_video", src_video, "--dst_video", dst_video, \
                                 "--dnsmos_uri", dnsmos_uri, "--dnsmos_key", dnsmos_key, "--dst_audio", audio_path, \
                                 "--dst_network_log", dst_network_log]
    run_and_check_result(cmd)


def check_yuv_video_vmaf(src_video, dst_video, video_size, pixel_format, bitdepth, audio_path, dnsmos_uri, dnsmos_key, dst_network_log):
    cmd = ["python3", file_path, "--src_video", src_video, "--dst_video", dst_video, \
                                 "--video_size", video_size, "--pixel_format", pixel_format, "--bitdepth", bitdepth, \
                                 "--dnsmos_uri", dnsmos_uri, "--dnsmos_key", dnsmos_key, "--dst_audio", audio_path, \
                                 "--dst_network_log", dst_network_log]
    run_and_check_result(cmd)


def test_y4m_y4m_compare(dnsmos_uri, dnsmos_key):
    check_video_score(video_y4m_path, video_y4m_path, audio_path=audio_path, \
                dnsmos_uri=dnsmos_uri, dnsmos_key=dnsmos_key, dst_network_log=dst_network_log)


def test_y4m_yuv_compare(dnsmos_uri, dnsmos_key):
    check_video_score(video_y4m_path, video_yuv_path, audio_path=audio_path, \
                dnsmos_uri=dnsmos_uri, dnsmos_key=dnsmos_key, dst_network_log=dst_network_log)

    check_video_score(video_yuv_path, video_y4m_path, audio_path=audio_path, \
                dnsmos_uri=dnsmos_uri, dnsmos_key=dnsmos_key, dst_network_log=dst_network_log)


def test_yuv_yuv_compare(dnsmos_uri, dnsmos_key):
    check_yuv_video_vmaf(video_yuv_path, video_yuv_path, video_size="320x240", pixel_format="420", bitdepth="8", \
                        audio_path=audio_path, dnsmos_uri=dnsmos_uri, dnsmos_key=dnsmos_key, dst_network_log=dst_network_log)
