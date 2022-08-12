## 接受上层的数据包packet_list进行带宽的估计;结合基于延迟的丢包估计和基于丢包的丢包估计
"""
The following is an example for the stats
[
    {
        'arrival_time_ms': 66113,
        'header_length': 24,
        'padding_length': 0,
        'payload_size': 1389,
        'payload_type': 126,
        'send_time_ms': 60999,
        'sequence_number': 54366,
        'ssrc': 12648429
    },
    {
        'arrival_time_ms': 66181,
        'header_length': 24,
        'padding_length': 0,
        'payload_size': 1389,
        'payload_type': 126,
        'send_time_ms': 61069,
        'sequence_number': 54411,
        'ssrc': 12648429}
]
        for pkt in packet_list:
            packet_info = PacketInfo()
            packet_info.payload_type = pkt["payload_type"]
            packet_info.ssrc = pkt["ssrc"]
            packet_info.sequence_number = pkt["sequence_number"]
            packet_info.send_timestamp = pkt["send_time_ms"]
            packet_info.receive_timestamp = pkt["arrival_time_ms"]
            packet_info.padding_length = pkt["padding_length"]
            packet_info.header_length = pkt["header_length"]
            packet_info.payload_size = pkt["payload_size"]
class PacketInfo:
    def __init__(self):
        self.payload_type = None
        self.sequence_number = None  # int
        self.send_timestamp = None  # int, ms
        self.ssrc = None  # int
        self.padding_length = None  # int, B
        self.header_length = None  # int, B
        self.receive_timestamp = None  # int, ms
        self.payload_size = None  # int, B
        self.bandwidth_prediction = None  # int, bps

    def __str__(self):
        return (
            f"receive_timestamp: { self.receive_timestamp }ms"
            f", send_timestamp: { self.send_timestamp }ms"
            f", payload_size: { self.payload_size }B"
        )

"""
from packet_info import PacketInfo


#### 发送端控制
class sender_Ratecontroller:
    def __init__(self):
        self.bwe = None

    def sender_on_feedback(self):
        ## 接受数据包进行速率更新
        self.tobedone = None
