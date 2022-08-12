#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests, json
import soundfile as sf
from utils.audio_info import AudioInfo
from urllib.parse import urlparse, urljoin
from abc import ABC, abstractmethod


class AudioEvalMethod(ABC):
    @abstractmethod
    def __init__(self):
        self.eval_name = "base"
        self.required_sample_rate = []
        self.required_channel = []

    @abstractmethod
    def eval(self, dst_audio_info : AudioInfo):
        pass


class AudioEvalMethodDNSMOS(AudioEvalMethod):
    def __init__(self, dnsmos_uri, dnsmos_key):
        super(AudioEvalMethodDNSMOS, self).__init__()
        if not dnsmos_uri or not dnsmos_key:
            raise ValueError("Please specify the arguments dnsmos_uri and dnsmos_key.")
        
        self.eval_name = "dnsmos"
        self.dnsmos_uri = dnsmos_uri
        self.dnsmos_key = dnsmos_key
        self.required_sample_rate = ["16000"]
        self.required_channel = ["1"]

    def eval(self, dst_audio_info : AudioInfo):
        # Set the content type
        headers = {'Content-Type': 'application/json'}
        # If authentication is enabled, set the authorization header
        headers['Authorization'] = f'Basic {self.dnsmos_key}'
        
        audio, fs = sf.read(dst_audio_info.audio_path)
        if fs != 16000:
            print('Only sampling rate of 16000 is supported as of now')
        data = {"data": audio.tolist()}
        input_data = json.dumps(data)
        # Make the request and display the response
        u = urlparse(self.dnsmos_uri)
        resp = requests.post(urljoin("https://" + u.netloc, 'score'), data=input_data, headers=headers)
        score_dict = resp.json()
        
        # scale [1, 5] -> [0, 100]
        return (score_dict["mos"] - 1) / 4 * 100
    