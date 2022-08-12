#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse, json
from eval_video import VideoEvaluation, init_video_argparse, get_video_score
from eval_audio import AudioEvaluation, init_audio_argparse, get_audio_score
from eval_network import NetworkEvaluation, init_network_argparse, get_network_score


description = \
'''
This script provide multi methods to evaluate quality of video, audio and network.
'''

def init_argparse():
    video_parser = init_video_argparse()
    audio_parser = init_audio_argparse()
    network_parser = init_network_argparse()
    parser = argparse.ArgumentParser(description=description, parents=[video_parser, audio_parser, network_parser], conflict_handler='resolve')

    args = parser.parse_args()

    return args

if __name__ == "__main__":
    
    args = init_argparse()
    out_dict = {}

    out_dict["video"] = get_video_score(args)
    out_dict["audio"] = get_audio_score(args)
    out_dict["network"] = get_network_score(args)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(json.dumps(out_dict))
    else:
        print(json.dumps(out_dict))
    