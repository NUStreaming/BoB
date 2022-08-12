#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse, json, subprocess
from tempfile import NamedTemporaryFile
from utils.video_info import VideoInfo
from utils.video_eval_method import VideoEvalMethodVmaf, VideoEvalMethod
from utils.video_align_method import VideoAlignMethodFfmpeg, VideoAlignMethod, VideoAlignMethodOcr


description = \
'''
This script provide multi methods to evaluate network quality.
For example, the method of Vmaf https://github.com/Netflix/vmaf.
'''


class VideoEvaluation(object):
    def __init__(self, eval_method : VideoEvalMethod, align_method : VideoAlignMethod, args):
        self.eval_method = eval_method
        self.align_method = align_method
        self.args = args

    ### ffmpeg orders below ###

    def change_video_type(self, video_info : VideoInfo, new_type):
        output = NamedTemporaryFile('w+t', suffix=".%s" % (new_type))
        cmd = ["ffmpeg"]
        if video_info.format_name == "rawvideo":
            cmd.extend(["-video_size", video_info.video_size])
        cmd.extend(["-i", video_info.video_path, "-y"])
        if new_type == "yuv":
            cmd.extend(["-video_size", video_info.video_size])
        cmd.append(output.name)
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf8")

        return output

    def eval(self, src_video_path, dst_video_path):
        # get the correspond VideoInfo according to path
        src_video_info = VideoInfo(src_video_path, self.args.video_size)
        dst_video_info = VideoInfo(dst_video_path, self.args.video_size)

        # init video size
        if not src_video_info.video_size and not dst_video_info.video_size:
            raise ValueError("Please specify the arguments --video_size")
 
        if not dst_video_info.video_size:
            dst_video_info.update_video_size(src_video_info.video_size)
        elif not src_video_info.video_size:
            src_video_info.update_video_size(dst_video_info.video_size)

        # update video info
        src_video_info.parse_video_by_ffprobe(video_size=src_video_info.video_size)
        dst_video_info.parse_video_by_ffprobe(video_size=dst_video_info.video_size)
        video_size = src_video_info.video_size

        # check video type
        if src_video_info.format_name not in self.eval_method.support_type:
            fo_new_src_video = self.change_video_type(src_video_info, self.eval_method.support_type_abbreviation[0])
            src_video_info = VideoInfo(fo_new_src_video.name)
        if dst_video_info.format_name not in self.eval_method.support_type:
            fo_new_dst_video = self.change_video_type(dst_video_info, self.eval_method.support_type_abbreviation[0])
            dst_video_info = VideoInfo(fo_new_dst_video.name)

        # keep same video type
        if src_video_info.format_abbreviation != "y4m":
            fo_new_src_video = self.change_video_type(src_video_info, "y4m")
            src_video_info = VideoInfo(fo_new_src_video.name, video_size=video_size)
        if dst_video_info.format_abbreviation != "y4m":
            fo_new_dst_video = self.change_video_type(dst_video_info, "y4m")
            dst_video_info = VideoInfo(fo_new_dst_video.name, video_size=video_size)

        if self.args.frame_align_method != "None":
            if not src_video_info.fps and not dst_video_info.fps:
                raise ValueError("Can't get fps from video")
            # get align video from src video
            tmp_fo = self.align_method.frame_align(src_video_info, dst_video_info)
            # update video if need to do align
            if tmp_fo:
                fo_new_src_video = tmp_fo
                src_video_info = VideoInfo(fo_new_src_video.name)

            tmp_fo = self.align_method.frame_align(dst_video_info, src_video_info)
            if tmp_fo:
                fo_new_dst_video = tmp_fo
                dst_video_info = VideoInfo(fo_new_dst_video.name)

        # Calculate video quality
        ret = self.eval_method.eval(src_video_info, dst_video_info)

        return ret


def get_video_score(args):
    eval_method = None
    align_method = None

    if args.video_eval_method == "vmaf":
        eval_method = VideoEvalMethodVmaf(args.model_path)
    else:
        raise ValueError("Not supoort such method to evaluate video")
    
    if args.frame_align_method == "ffmpeg":
        align_method = VideoAlignMethodFfmpeg()
    elif args.frame_align_method == "ocr":
        align_method = VideoAlignMethodOcr()
    elif args.frame_align_method != "None":
        raise ValueError("Not supoort such method to align video")

    video_eval_tool = VideoEvaluation(eval_method, align_method, args)
    video_out = video_eval_tool.eval(args.src_video, args.dst_video)
    
    return video_out


def init_video_argparse():
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--output", type=str, default=None, help="the path of output file")
    # for video evaluation
    parser.add_argument("--video_eval_method", type=str, default="vmaf", choices=["vmaf"], help="the method to evaluate video, like vmaf")
    parser.add_argument("--src_video", type=str, required=True, default=None, help="the path of source video")
    parser.add_argument("--dst_video", type=str, required=True, default=None, help="the path of destination video")
    parser.add_argument("--frame_align_method", type=str, default="ffmpeg", choices=["None", "ffmpeg", "ocr"], help="how to do frame alignment. None means not to do frame align")
    parser.add_argument("--model_path", type=str, default=None, help="the path of vmaf model")
    # required by the video format of yuv raw video
    parser.add_argument("--video_size", type=str, default=None, help="the size of video, like 1920x1080. Required by the video format of yuv")
    parser.add_argument("--pixel_format", type=str, default=None, choices=["420", "422", "444"], help="pixel format (420/422/444)")
    parser.add_argument("--bitdepth", type=str, default=None, choices=["8", "10", "12"], help="bitdepth (8/10/12)")

    return parser


if __name__ == "__main__":
    parser = init_video_argparse()
    args = parser.parse_args()
    out_dict = {}  
    out_dict["video"] = get_video_score(args)
        
    if args.output:
        with open(args.output, 'w') as f:
            f.write(json.dumps(out_dict))
    else:
        print(json.dumps(out_dict))
