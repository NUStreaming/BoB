#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess, re, os


class AudioInfo(object):
    def __init__(self, audio_path):
        self.audio_path = audio_path
        self.sample_rate = None
        self.channel = None
        self.duration_sec = None
        self.format_name = None
        self.size = None
        self.bit_rate = None

        self.parse_audio_by_ffprobe()

    def parse_audio_by_ffprobe(self):
        if  not self.audio_path or not os.path.exists(self.audio_path):
            raise ValueError("Error audio path")
        cmd = ["ffprobe", "-show_format", self.audio_path]

        cmd_result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf8")

        sample_rate = re.search(r'Stream.*?([\d]+) Hz,', cmd_result.stdout)
        if sample_rate:
            self.sample_rate = sample_rate.group(1)

        channel = re.search(r'Stream.*?([\d]+) channels,', cmd_result.stdout)
        if channel:
            self.channel = channel.group(1)

        duration_sec = re.search(r'duration=([\d\.]+)', cmd_result.stdout)
        if duration_sec:
            self.duration_sec = duration_sec.group(1)
        
        format_name = re.search(r'format_name=([\w]+)', cmd_result.stdout)
        if format_name:
            self.format_name = format_name.group(1)

        size = re.search(r'size=([\d\.]+)', cmd_result.stdout)
        if size:
            self.size = size.group(1)

        bit_rate = re.search(r'bit_rate=([\d\.]+)', cmd_result.stdout)
        if bit_rate:
            self.bit_rate = bit_rate.group(1)

    def check_all_info(self):
        assert self.audio_path
        assert self.sample_rate
        assert self.channel
        assert self.duration_sec
        assert self.format_name
        assert self.size
        assert self.bit_rate
        print(self.audio_path, self.sample_rate, self.channel, self.duration_sec, self.format_name, self.size, self.bit_rate)
