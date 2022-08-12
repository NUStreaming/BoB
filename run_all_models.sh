MODELDIR="./model"
RESULTDIR=results
EVAL_LOGFILE="eval.log"
rm -rf ${EVAL_LOGFILE}
rm -rf $RESULTDIR
mkdir -p $RESULTDIR
for model in `ls $MODELDIR -tr`
do
    MODEL="${MODELDIR}/${model}"
    echo $MODEL >active_model
    rm -rf webrtc.log
    rm -rf bandwidth_estimator.log
    rm -rf plot.png
    docker run -d --rm -v `pwd`:/app -w /app --name alphartc_pyinfer challenge-env peerconnection_serverless receiver_pyinfer.json
    docker exec alphartc_pyinfer peerconnection_serverless sender_pyinfer.json
    python3 plot.py --title ${model}
    mv plot.png $RESULTDIR/${model%.*}.png
    ./eval.sh
    python3 log_eval.py --model ${model} --eval_log_file ${EVAL_LOGFILE}
done
mv ${EVAL_LOGFILE} $RESULTDIR/
