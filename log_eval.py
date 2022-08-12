import argparse
import json
import os.path


def log_eval(model, network_profile, network_out_file, video_out_file,log_file):
    #network score
    with open(network_out_file, 'r') as f:
        network_eval_content=f.read().strip()
        json_network = json.loads(network_eval_content)
        network_score=float(json_network["network"])
        recv_rate_score=float(json_network["recv_rate_score"])
        delay_score=float(json_network["delay_score"])
        loss_rate=float(json_network["loss_rate"])

    #video score
    with open(video_out_file, 'r') as f:
        video_eval_content=f.read().strip()
        json_video = json.loads(video_eval_content)
        video_score=float(json_video["video"])

    if os.path.isfile(log_file):
        f=open(log_file, "a")
    else:
        f=open(log_file, "w")
        f.write("model\tnetwork_profile\tnetwork_score\trecv_rate_score\tdelay_score\tloss_rate\tvideo_score\n")
    f.write(model+"\t"+network_profile+"\t"+str(network_score)+"\t"+str(recv_rate_score)+"\t"+str(delay_score)+"\t"+str(loss_rate)+"\t"+str(video_score)+"\n")
    f.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Log network and video evaluations")
    parser.add_argument("--model", type=str, default="pre_trained.pth", help="model name")
    parser.add_argument("--network_profile", type=str, default="", help="network profile")
    parser.add_argument("--eval_network_file", type=str, default="out_eval_network.json", help="network output json file")
    parser.add_argument("--eval_video_file", type=str, default="out_eval_video.json", help="video output json file")
    parser.add_argument("--eval_log_file", type=str, default="eval.log", help="csv output log file")
    args = parser.parse_args()
    log_eval(model=args.model, network_profile=args.network_profile,network_out_file=args.eval_network_file, video_out_file=args.eval_video_file, log_file=args.eval_log_file)