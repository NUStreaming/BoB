GROUND_RECV_RATE=500
if [ -n "$1" ]; then
  GROUND_RECV_RATE=$1
fi
echo "using ground_recv_rate=${GROUND_RECV_RATE}"

#docker run --rm -v `pwd`:/app -it challenge-env /bin/bash
docker run --rm -v `pwd`:/app -w /home/onl/metrics --name eval challenge-env python3 eval_network.py --dst_network_log /app/webrtc.log  --output /app/out_eval_network.json --ground_recv_rate ${GROUND_RECV_RATE} --max_delay 2000
docker run --rm -v `pwd`:/app -w /home/onl/metrics --name eval challenge-env python3 eval_video.py --src_video /app/testmedia/test.yuv --dst_video /app/outvideo.yuv --frame_align_method ocr --output /app/out_eval_video.json
