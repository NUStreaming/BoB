import numpy as np
from .aimdcontrol import Aimd_rate_controller
import time
from .trendline import Trendline_estimator
from .overuse_detector import Overdetector
from .inter_arrival import Interval_arrival
# 发送端基于延迟的带宽预测，通过接收端发聩回来的arrival time以及send time进行trendline 滤波评估当前的带宽预测
k_trendline_window_size = 20
k_trendline_smoothing_coeff = 0.9
k_trendline_threshold_gain = 4.0

k_group_time = 5
k_max_failed_count = 5

# k_min_bitrate = 10000  #64000 #64kbps 需要修改
# k_max_bitrate = 8000000  #12800000 #1.6MB/s 12800 kbps 需要修改
k_min_bitrate = 80000  #64000 #64kbps 需要修改
k_max_bitrate = 20000000  #12800000 #1.6MB/s 12800 kbps 需要修改


k_timestamp_ms = 2000

kBwNormal = 0,
kBwUnderusing = 1,
kBwOverusing = 2,
"""


class PacketInfo:
    def __init__(self):
        self.payload_type = None
        self.sequence_number = None  # int 发送通道的报文序号
        self.send_timestamp = None  # int, ms 发送时间戳
        self.ssrc = None  # int
        self.padding_length = None  # int, B
        self.header_length = None  # int, B
        self.receive_timestamp = None  # int, ms 到达时间戳
        self.payload_size = None  # int, B  包数据大小
        self.bandwidth_prediction = None  # int, bps

    def __str__(self):
        return (
            f"receive_timestamp: { self.receive_timestamp }ms"
            f", send_timestamp: { self.send_timestamp }ms"
            f", payload_size: { self.payload_size }B"
        )

typedef struct
{
	int64_t			create_ts;			/*创建时间戳*/毫秒
	int64_t			arrival_ts;			/*到达时间戳*/毫秒
	int64_t			send_ts;			/*发送时间戳*/ 毫秒

	uint16_t		sequence_number;	/*发送通道的报文序号*/
	size_t			payload_size;		/*包数据大小*/
}packet_feedback_t;

"""


def get_time_ms():
    return int(time.time() * 1000)


class bwe_result:
    def __init__(self):
        self.updated = -1
        self.probe = -1
        self.bitrate = 0
        self.recovered_from_overuse = -1

    def reset(self):
        self.updated = -1
        self.probe = -1
        self.bitrate = 0
        self.recovered_from_overuse = -1


class delay_base_bwe:
    def __init__(self):
        self.inter_arrival = Interval_arrival()  # Tobedone
        self.rate_control = Aimd_rate_controller(k_max_bitrate, k_min_bitrate)
        self.trendline_estimator = Trendline_estimator()
        self.detector = Overdetector()

        self.last_seen_ms = -1  #毫秒
        self.first_ts = get_time_ms()  # 这个需要暴露一个接口后续外部更改
        self.trendline_window_size = k_trendline_window_size
        self.trendline_smoothing_coeff = k_trendline_smoothing_coeff
        self.trendling_threshold_gain = k_trendline_threshold_gain

        self.consecutive_delayed_feedbacks = 0

    # def __delay_bwe_reset(self):
    #     Tobedone=True #interval相关
    def reset(self):
        self.inter_arrival = Interval_arrival()  # Tobedone
        self.rate_control = Aimd_rate_controller(k_max_bitrate, k_min_bitrate)
        self.trendline_estimator = Trendline_estimator()
        self.detector = Overdetector()

        self.last_seen_ms = -1  #毫秒
        self.first_ts = get_time_ms()  # 这个需要暴露一个接口后续外部更改
        self.trendline_window_size = k_trendline_window_size
        self.trendline_smoothing_coeff = k_trendline_smoothing_coeff
        self.trendling_threshold_gain = k_trendline_threshold_gain

        self.consecutive_delayed_feedbacks = 0
        return

    def set_time(self, first_time):
        self.first_ts = np.abs(first_time - self.first_ts)
        return

    def set_start_bitrate(self, bitrate):
        self.rate_control.aimd_set_start_bitrate(bitrate=bitrate)
        return

    def __delay_bwe_process(self, packet, now_ts):

        ts_delta = 0
        t_delta = 0
        size_delta = 0

        # if self.last_seen_ms==-1 or now_ts>self.last_seen_ms+k_timestamp_ms:
        #     Tobedone=True # 初始化相关

        self.last_seen_ms = now_ts
        packet_arrival_ts = packet["arrival_time_ms"]
        packet_payload_size = packet["payload_size"]

        timestamp = packet["send_time_ms"] - self.first_ts
        ret, ts_delta, t_delta, size_delta = self.inter_arrival.inter_arrival_compute_deltas(
            timestamp, packet_arrival_ts, now_ts, packet_payload_size,
            ts_delta, t_delta, size_delta)
        if ret == 0:
            # 进行斜率计算
            self.trendline_estimator.trendline_update(t_delta, ts_delta,
                                                      packet_arrival_ts)
            # 进行过载检查
            self.detector.overuse_detect(
                self.trendline_estimator.trendline_slope(), ts_delta,
                self.trendline_estimator.num_of_deltas, packet_arrival_ts)
        return

    def __delay_bwe_long_feedback_delay(self, arrival_ts):
        result = bwe_result()
        self.rate_control.aimd_set_estimate(
            self.rate_control.curr_rate * 1 / 2, arrival_ts)
        result.updated = 0
        result.probe = -1
        result.bitrate = self.rate_control.curr_rate
        return result

    def __delay_bwe_update(self, now_ts, acked_bitrate, overusing):
        input_state = kBwOverusing if overusing == 0 else self.detector.state

        input_noise_var = 0
        input_incoming_bitrate = acked_bitrate
        self.rate_control.input_data(input_state, input_noise_var,
                                     input_incoming_bitrate)

        prev_bitrate = self.rate_control.curr_rate

        target_bitrate = self.rate_control.aimd_update(now_ts)
        result = 0 if self.rate_control.inited == 0 and prev_bitrate != target_bitrate else -1
        # if self.rate_control.inited==0 and prev_bitrate!=target_bitrate:
        #     result=0
        # else:
        #     result=-1
        # print("target:",target_bitrate)
        # print("now_ts",now_ts)
        return result, target_bitrate

    def __delay_bwe_maybe_update(self, overusing, acked_bitrate,
                                 recovered_from_overuse, now_ts):
        result = bwe_result()
        if overusing == 0:
            if acked_bitrate > 0 and self.rate_control.aimd_time_reduce_further(
                    now_ts, acked_bitrate) == 0:
                #带宽过载，进行aimd方式减小
                result.updated, result.bitrate = self.__delay_bwe_update(
                    now_ts, acked_bitrate, overusing)
            elif acked_bitrate==0 and self.rate_control.inited==0 \
                and self.rate_control.aimd_time_reduce_further(now_ts,self.rate_control.curr_rate*3/4-1)==0:
                self.rate_control.aimd_set_estimate(
                    self.rate_control.curr_rate * 3 / 4, now_ts)
                result.updated = 0
                result.probe = -1
                result.bitrate = self.rate_control.curr_rate
        else:  #未过载，进行aimd方式判断是否要加大码率
            result.updated, result.bitrate = self.__delay_bwe_update(
                now_ts, acked_bitrate, overusing)
            result.recovered_from_overuse = recovered_from_overuse

        return result

    # acked_bitrate相当于接受速率 源文件本质上通过C函数gettimeofday获得；python可以import time获得;源代码的实现类似于time.c的实现;
    def delay_bwe_incoming(self, packet_list, acked_bitrate, now_ts):
        result = bwe_result()

        packet_num = len(packet_list)

        if packet_num <= 0:
            return result

        overusing = -1
        delay_feedback = 0
        recovered_from_overuse = -1
        prev_state = self.detector.state

        for pkt in packet_list:
            # 这个可能需要修改
            # print("here",pkt["send_time_ms"],self.first_ts)
            if pkt["send_time_ms"] < self.first_ts:

                continue
            delay_feedback = -1

            #通过发包和收包间隔差计算延迟斜率，通过斜率判断是否过载
            self.__delay_bwe_process(pkt, now_ts)

            if prev_state == kBwUnderusing and self.detector.state == kBwNormal:
                recovered_from_overuse = 0

            prev_state = self.detector.state

        if self.detector.state == kBwOverusing:
            overusing = 0

        if delay_feedback == 0:  #太多次网络feedback事件出现重复，强制的带宽减半并返回
            self.consecutive_delayed_feedbacks += 1
            if self.consecutive_delayed_feedbacks > k_max_failed_count:
                return self.__delay_bwe_long_feedback_delay(
                    packet_list[packet_num - 1]["arrival_time_ms"])
        else:  #进行aimd方式码率计算

            self.consecutive_delayed_feedbacks = 0
            return self.__delay_bwe_maybe_update(overusing, acked_bitrate,
                                                 recovered_from_overuse,
                                                 now_ts)

        return result
