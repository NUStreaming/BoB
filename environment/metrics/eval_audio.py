#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess, json, argparse
from tempfile import NamedTemporaryFile
from utils.audio_info import AudioInfo
from utils.audio_eval_method import AudioEvalMethod, AudioEvalMethodDNSMOS


description = \
'''
This script provide multi methods to evaluate audio quality. 
For example, the method of DNSMOS https://github.com/microsoft/DNS-Challenge.
'''


class AudioEvaluation():
    def __init__(self, eval_method : AudioEvalMethod, args):
        self.eval_method = eval_method
        self.args = args

    def change_audio_config(self, audio_info : AudioInfo):
        if audio_info.sample_rate in self.eval_method.required_sample_rate and audio_info.channel in self.eval_method.required_channel:
            return None
        output = NamedTemporaryFile('w+t', suffix=".%s" % (audio_info.format_name))
        cmd = ["ffmpeg", "-i", audio_info.audio_path, "-ar", self.eval_method.required_sample_rate[0], \
                         "-ac", self.eval_method.required_channel[0], "-vn", "-y", output.name]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf8")

        return output

    def eval(self, dst_audio_path):
        dst_audio_info = AudioInfo(dst_audio_path)

        # check audio type
        fo_new_video = self.change_audio_config(dst_audio_info)
        dst_audio_info = AudioInfo(fo_new_video.name) if fo_new_video else dst_audio_info

        score_dict = self.eval_method.eval(dst_audio_info)

        return score_dict


def init_audio_argparse():
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--output", type=str, default=None, help="the path of output file")
    # for audio evaluation
    parser.add_argument("--audio_eval_method", type=str, default="dnsmos", choices=["dnsmos"], help="the method to evaluate audio, like DNSMOS")
    parser.add_argument("--dst_audio", type=str, default=None, required=True, help="the path of destination audio")
    parser.add_argument("--audio_sample_rate", type=str, default='16000', help="the sample rate of audio")
    parser.add_argument("--audio_channel", type=str, default='1', help="the numbers of audio channels")
    # for DNSMOS
    parser.add_argument("--dnsmos_uri", type=str, default=None, help="the uri to evaluate audio provided by DNSMOS")
    parser.add_argument("--dnsmos_key", type=str, default=None, help="the key to evaluate audio provided by DNSMOS")

    return parser


def get_audio_score(args):
    eval_method = None

    if args.audio_eval_method == "dnsmos":
        eval_method = AudioEvalMethodDNSMOS(args.dnsmos_uri, args.dnsmos_key)
    else:
        raise ValueError("Not supoort such method to evaluate audio")
        
    audio_eval_tool = AudioEvaluation(eval_method, args)
    audio_out = audio_eval_tool.eval(args.dst_audio)

    return audio_out


if __name__ == "__main__":
    parser = init_audio_argparse()
    args = parser.parse_args()
    out_dict = {}
    out_dict["audio"] = get_audio_score(args)
        
    if args.output:
        with open(args.output, 'w') as f:
            f.write(json.dumps(out_dict))
    else:
        print(json.dumps(out_dict))