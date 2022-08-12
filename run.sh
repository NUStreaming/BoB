cp BandwidthEstimator_bob_heuristic.py BandwidthEstimator.py
#cp BandwidthEstimator_gemini.py BandwidthEstimator.py
#cp BandwidthEstimator_hrcc.py BandwidthEstimator.py
docker stop alphartc_pyinfer eval
docker stop $(docker ps -q --filter ancestor=challenge-env)
rm -rf webrtc.log
rm -rf bandwidth_estimator.log
rm -rf plot.png
docker run -d --rm -v `pwd`:/app -w /app --name alphartc_pyinfer challenge-env peerconnection_serverless receiver_pyinfer.json
docker exec alphartc_pyinfer peerconnection_serverless sender_pyinfer.json
bash ./eval.sh
python3 log_eval.py --model "SingleRun" --eval_log_file "eval.log"