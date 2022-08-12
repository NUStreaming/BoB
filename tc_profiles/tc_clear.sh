TC='/sbin/tc'
INTERFACE1=eth0

killall tc_policy.sh 1>/dev/null 2>&1
killall sleep 1>/dev/null 2>&1
killall tc 1>/dev/null 2>&1

$TC qdisc del dev $INTERFACE1 root handle 1:0 1>/dev/null 2>&1
$TC qdisc del dev $INTERFACE1 root 1>/dev/null 2>&1
$TC qdisc del dev lo root 1>/dev/null 2>&1
