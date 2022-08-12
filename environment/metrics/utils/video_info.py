#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess, tempfile, re, os


class VideoInfo(object):
    def __init__(self, video_path, video_size=None, bitdepth="8"):
        self.video_path = video_path
        self.video_size = video_size
        self.width = None
        self.height = None
        self.duration_sec = None
        self.format_name = None
        self.format_abbreviation = None
        self.fps = None
        self.size = None
        self.bit_rate = None
        self.pixel_format = None
        self.bitdepth = bitdepth

        self.parse_video_by_ffprobe(video_size)

    def parse_video_by_ffprobe(self, video_size=None):
        if  not self.video_path or not os.path.exists(self.video_path):
            raise ValueError("Error video path")
        cmd = ["ffprobe", "-show_format", self.video_path]

        cmd_result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf8")
        if cmd_result.returncode:
            if video_size:
                cmd.extend(["-video_size", video_size])
            cmd_result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf8")

        re_video_size = re.search(r'Stream.*?([\d]+x[\d]+),', cmd_result.stdout)
        if re_video_size:
            if video_size:
                assert re_video_size.group(1) == video_size.lower()
            self.video_size = re_video_size.group(1)
            self.width = self.video_size.split('x')[0]
            self.height = self.video_size.split('x')[1]

        duration_sec = re.search(r'duration=([\d\.]+)', cmd_result.stdout)
        if duration_sec:
            self.duration_sec = duration_sec.group(1)

        format_name = re.search(r'format_name=([\w\d]+)', cmd_result.stdout)
        if format_name:
            self.format_name = format_name.group(1)
            self.format_abbreviation = "yuv" if self.format_name == "rawvideo" else "y4m"

        fps = re.search(r'([\d]+)\sfps', cmd_result.stdout)
        if fps:
            self.fps = fps.group(1)

        size = re.search(r'size=([\d]+)', cmd_result.stdout)
        if size:
            self.size = size.group(1)

        bit_rate = re.search(r'bit_rate=([\d]+)', cmd_result.stdout)
        if bit_rate:
            self.bit_rate = bit_rate.group(1)

        pixel_format = re.search(r'Stream.*?(4[\d]+)p,', cmd_result.stdout)
        if pixel_format:
            self.pixel_format = pixel_format.group(1)

    def update_video_size(self, size):
        if self.video_size:
            assert self.video_size == size
            return 
        self.video_size = size
        re_result = re.search(r'([\d]+)[xX]([\d]+)', size)
        assert re_result
        self.width = re_result.group(1)
        self.height = re_result.group(2)

    def get_frame_count(self):
        assert self.duration_sec
        assert self.fps
        return float(self.duration_sec) * float(self.fps)

    def check_all_info(self):
        assert self.video_size
        assert self.duration_sec
        assert self.format_name
        if "rawvideo" != self.format_name:
            assert self.fps
        assert self.size
        assert self.bit_rate
        assert self.pixel_format
        print(self.video_size, self.duration_sec, self.format_name, self.fps, self.size, self.bit_rate, self.pixel_format)
