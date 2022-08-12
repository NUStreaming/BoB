# 通过接收端反馈的收包信息来估算本端发送的有效码率
import numpy as np

k_initial_rate_wnd_ms = 500
k_rate_wnd_ms = 150


class Ack_bitrate_estimator:
    def __init__(self):
        self.alr_ended_ts = -1
        self.cur_win_ms = -1
        self.prev_ts = -1
        self.sum = 0
        self.bitrate_estimate = -1.0
        self.bitrate_estimate_var = 50

    # 将码率设置到一个变化比较大的范围因子，这个和pacer有关
    def __ack_estimator_mybe_expect_fast_change(self, packet_send_ts):
        if self.alr_ended_ts >= 0 and packet_send_ts > self.alr_ended_ts:
            self.bitrate_estimate_var += 200
            self.alr_ended_ts = -1

    def __ack_estimator_update_window(self, now_ts, size, rate_wnd_ms):
        if now_ts < self.prev_ts:
            self.prev_ts = -1
            self.sum = 0
            self.cur_win_ms = 0
        if self.prev_ts >= 0:
            self.cur_win_ms += now_ts - self.prev_ts
            #跳跃时间超过了一个窗口周期，将统计数据情况重新计算
            if now_ts - self.prev_ts > rate_wnd_ms:
                self.sum = 0
                self.cur_win_ms %= rate_wnd_ms

        self.prev_ts = now_ts
        bitrate_sample = -1.0
        if self.cur_win_ms > -rate_wnd_ms:  #刚好一个窗口周期，进行码率计算
            bitrate_sample = 8.0 * self.sum / rate_wnd_ms
            self.cur_win_ms -= rate_wnd_ms
            self.sum = 0

        self.sum += size
        return bitrate_sample

    def __ack_estimator_update(self, arrival_ts, paylaod_size):
        rate_windows_ms = k_rate_wnd_ms
        if self.bitrate_estimate < 0:
            rate_windows_ms = k_initial_rate_wnd_ms

        bitrate_sample = self.__ack_estimator_update_window(
            arrival_ts, paylaod_size, rate_windows_ms)

        if bitrate_sample < 1.0:
            return
        if self.bitrate_estimate < 0.0:
            self.bitrate_estimate = bitrate_sample
            return

        # 引入逼近计算
        sample_uncertainty = 10.0 * np.abs(
            self.bitrate_estimate - bitrate_sample) / self.bitrate_estimate
        sample_var = sample_uncertainty * sample_uncertainty

        pred_bitrate_estimate_var = self.bitrate_estimate_var + 5

        self.bitrate_estimate = (sample_var * self.bitrate_estimate +
                                 pred_bitrate_estimate_var * bitrate_sample
                                 ) / (sample_var + pred_bitrate_estimate_var)
        self.bitrate_estimate_var = sample_var * pred_bitrate_estimate_var / (
            sample_var + pred_bitrate_estimate_var)

    def ack_estimator_incoming(self, packet_list):
        #根据接收方的estimator proxy反馈过来的feedback来迭代码率
        for pkt in packet_list:
            if pkt["send_time_ms"] >= 0:
                self.__ack_estimator_mybe_expect_fast_change(
                    pkt["send_time_ms"])
                self.__ack_estimator_update(pkt["arrival_time_ms"],
                                            pkt["payload_size"])

    def ack_estimator_bitrate_bps(self):
        if self.bitrate_estimate < 0:
            return 0

        return self.bitrate_estimate * 1000
