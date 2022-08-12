#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess, tempfile, re
from utils.video_info import VideoInfo
from tempfile import NamedTemporaryFile
from abc import ABC, abstractmethod


class VideoEvalMethod(ABC):
    @abstractmethod
    def __init__(self):
        self.method_name = "base"
        self.support_type = []
        self.support_type_abbreviation = []

    @abstractmethod
    def eval(self, src_video_info : VideoInfo, dst_video_info : VideoInfo):  
        pass


class VideoEvalMethodVmaf(VideoEvalMethod):
    def __init__(self, model_path=None):
        super(VideoEvalMethodVmaf, self).__init__()
        self.method_name = "ffmpeg"
        self.support_type = ["yuv4mpegpipe", "rawvideo"]
        self.support_type_abbreviation = ["y4m", "yuv"]
        self.model_path = model_path

    def eval(self, src_video_info : VideoInfo, dst_video_info : VideoInfo):  
        if src_video_info.format_name != dst_video_info.format_name:
            raise ValueError("Can't compare bewteen different video type")
        if src_video_info.format_name not in self.support_type:
            raise ValueError("Video type don't support")

        cmd = ["vmaf", "--reference", src_video_info.video_path, "--distorted", dst_video_info.video_path]
        if self.model_path:
            cmd.extend(["-m", "path=%s" % (self.model_path)])

        if src_video_info.format_name == "rawvideo":
            cmd.extend(["--width", src_video_info.width, "--height", src_video_info.height, \
                "--pixel_format", src_video_info.pixel_format, "--bitdepth", src_video_info.bitdepth])
        
        with NamedTemporaryFile('w+t', suffix=".xml") as f:
            cmd.extend(["--output", f.name])
            cmd_result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf8")
            re_result = re.search(r'metric name="vmaf".*?mean="([\d]+\.[\d]+)"', f.read())
            if not re_result:
                raise ValueError("Can not get vmaf score from terminal output")
            vmaf_score = float(re_result.group(1))

        return vmaf_score
