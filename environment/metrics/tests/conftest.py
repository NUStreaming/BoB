#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pytest, os


cur_dir = os.path.dirname(os.path.abspath(__file__))

yuv_videos = [
    {
        "path" : cur_dir + "/data/test.yuv",
        "video_size" : "320x240",
        "pixel_format" : "420",
        "bitdepth" : "8"
    }
]

y4m_videos = [
    {
        "path" : cur_dir + "/data/test.y4m"
    },
    {
        "path" : cur_dir + "/data/test_labeled.y4m"
    }
]


def pytest_addoption(parser):
    parser.addoption("--dnsmos_uri", action="store")
    parser.addoption("--dnsmos_key", action="store")


@pytest.fixture
def dnsmos_uri(request):
    return request.config.getoption("--dnsmos_uri")


@pytest.fixture
def dnsmos_key(request):
    return request.config.getoption("--dnsmos_key")


@pytest.fixture(params=[None, "None", "ffmpeg", "ocr"])
def align_method(request):
    return request.param


@pytest.fixture(params=y4m_videos)
def y4m_video(request):
    return request.param


@pytest.fixture(params=yuv_videos)
def yuv_video(request):
    return request.param