#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess, os
from tempfile import NamedTemporaryFile
from utils.video_info import VideoInfo
from abc import ABC, abstractmethod


class VideoAlignMethod(ABC):
    @abstractmethod
    def __init__(self):
        self.align_method_name = "base"

    @abstractmethod
    def frame_align(self, src_video_info : VideoInfo, dst_video_info : VideoInfo):
        pass


class VideoAlignMethodFfmpeg(VideoAlignMethod):
    def __init__(self):
        super(VideoAlignMethodFfmpeg, self).__init__()
        self.align_method_name = "ffmpeg"

    def change_video_fps_by_ffmepg(self, video_info : VideoInfo, fps : int):
        output = NamedTemporaryFile('w+t', suffix=".%s" % (video_info.format_abbreviation))
        cmd = ["ffmpeg", "-i", video_info.video_path, "-r", str(fps), "-y"]
        if video_info.video_size:
            cmd.extend(["-s", video_info.video_size])
        cmd.append(output.name)
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf8")
        return output

    def frame_align(self, src_video_info : VideoInfo, dst_video_info : VideoInfo):

        fo_new_video = None
        # Frame alignment
        if not src_video_info.fps or \
                abs(src_video_info.get_frame_count() - dst_video_info.get_frame_count()) >= 0.000001:
            new_fps = dst_video_info.get_frame_count() / float(src_video_info.duration_sec)
            fo_new_video = self.change_video_fps_by_ffmepg(src_video_info, new_fps)

        return fo_new_video


class VideoAlignMethodOcr(VideoAlignMethod):
    def __init__(self):
        super(VideoAlignMethodOcr, self).__init__()
        self.align_method_name = "ocr"
        self.file_dir = os.path.dirname(os.path.abspath(__file__))
        self.file_path = os.path.join(self.file_dir, "ocr_frame_align.sh")

    def frame_align(self, src_video_info : VideoInfo, dst_video_info : VideoInfo):

        fo_new_src_video = NamedTemporaryFile('w+t', suffix=".%s" % (src_video_info.format_abbreviation))
        cmd = [self.file_path, "-p=%s" % (os.path.splitext(os.path.basename(src_video_info.video_path))[0]), "--src=%s" % (src_video_info.video_path), \
                "--src_out=%s" % (fo_new_src_video.name), "--fps=%s" % (src_video_info.fps), "-d=%s" % (src_video_info.duration_sec), \
                "-w=%s" % (src_video_info.width), "-h=%s" % (src_video_info.height), "--suffix=%s" % (src_video_info.format_abbreviation)]
        out = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf8")

        return fo_new_src_video