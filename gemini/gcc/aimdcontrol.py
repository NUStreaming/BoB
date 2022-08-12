# aimd控制器  Additive Increase Multiplicative Decrease 和式增加，积式减少
import numpy as np

kBwNormal = 0
kBwUnderusing = 1
kBwOverusing = 2

kRcHold = 0
kRcIncrease = 1
kRcDecrease = 2

kRcNearMax = 0
kRcAboveMax = 1
kRcMaxUnknown = 2

k_initialization_ts = 5000
kDefaultPacketSize = (1200 * 8)

DEFAULT_RTT = 200  #默认RTT 可能要修改

# class rate_control_input:
#     def __init__(self):
#         self.state=0
#         self.incoming_bitrate=0
#         self.noise_var=0


class Aimd_rate_controller:
    def __init__(self, max_rate, min_rate):
        self.max_rate = max_rate
        self.min_rate = min_rate
        self.curr_rate = 0

        self.avg_max_bitrate_kbps = -1.0  #kbps
        self.var_max_bitrate_kbps = 0.4

        self.state = kRcHold
        self.region = kRcMaxUnknown

        self.time_last_bitrate_change = -1
        self.time_first_incoming_estimate = -1

        self.rtt = DEFAULT_RTT

        self.inited = -1
        self.in_experiment = 0

        self.beta = 0.85

        self.last_decrease = 0

        # 给外部修改的接口 input：
        self.input_state = 0
        self.input_noise_var = 0
        self.input_incoming_bitrate = 0

    def __update_max_bitrate_estimate(self, incoming_bitrate_kps):
        alpha = 0.05
        if self.avg_max_bitrate_kbps == -1.0:
            self.avg_max_bitrate_kbps = incoming_bitrate_kps
        else:
            self.avg_max_bitrate_kbps = (
                1 - alpha
            ) * self.avg_max_bitrate_kbps + alpha * incoming_bitrate_kps
        # Estimate the max bit rate variance and normalize the variance with the average max bit rate
        # 估计最大比特率方差，并将方差与平均最大比特率归一化

        norm = max(self.avg_max_bitrate_kbps, 1.0)
        self.var_max_bitrate_kbps = (
            1 - alpha) * self.var_max_bitrate_kbps + alpha * (
                self.avg_max_bitrate_kbps - incoming_bitrate_kps) * (
                    self.avg_max_bitrate_kbps - incoming_bitrate_kps) / norm
        # 这部分可能需要更改
        # 0.4 ~= 14 kbit/s at 500 kbit/s
        if self.var_max_bitrate_kbps < 0.4:
            self.var_max_bitrate_kbps = 0.4

        # 2.5f ~= 35 kbit/s at 500 kbit
        if self.var_max_bitrate_kbps > 2.5:
            self.var_max_bitrate_kbps = 2.5

        return

    def __clamp_bitrate(self, new_bitrate, coming_rate):
        # print("clamp",new_bitrate,coming_rate)
        new_bitrate = new_bitrate
        max_bitrate_bps = 3 * coming_rate / 2 + 300000
        if new_bitrate > self.curr_rate and new_bitrate > max_bitrate_bps:
            new_bitrate = max(self.curr_rate, max_bitrate_bps)
        #print("clip",np.clip(new_bitrate,self.min_rate,self.max_rate),self.min_rate,self.max_rate,new_bitrate)

        return np.clip(new_bitrate, self.min_rate, self.max_rate)

    def __aimd_change_region(self, region):
        self.region = region
        return

    def __aimd_get_near_max_inc_rate(self):
        '''
        该函数会计算在当前码率下执行加性增大算法后增加的码率值。

        计算当前码率下每帧的大小，假设帧率为 30fps。
        '''
        bits_per_frame = self.curr_rate / 30.0
        packets_per_frame = np.ceil(bits_per_frame / kDefaultPacketSize)
        avg_packet_size_bits = bits_per_frame / packets_per_frame
        #Approximate the over-use estimator delay to 100 ms*
        response_time = (self.rtt + 100) * 2
        return max(8000, (avg_packet_size_bits * 1000) / response_time)

    def __additive_rate_increase(self, cur_ts, last_ts):
        '''
        计算一个在稳定期间的带宽增量
        '''
        result = (cur_ts -
                  last_ts) * self.__aimd_get_near_max_inc_rate() / 1000.0
        return result

    def __aimd_change_state(self, cur_ts):  # input的类型是rate_control_input

        state = self.input_state
        if state == kBwNormal:
            if self.state == kRcHold:
                self.time_last_bitrate_change = cur_ts
                self.state = kRcIncrease
        elif state == kBwOverusing:

            if self.state != kRcDecrease:
                self.state = kRcDecrease
        elif state == kBwUnderusing:

            self.state = kRcHold

        return

    def __multiplicative_rate_increase(self, cur_ts, last_ts, curr_bitrate):
        '''
        计算一次带宽的增量,一般是用于初期增长阶段，有点象慢启动
        '''
        alpha = 1.08
        ts_since = 0
        if last_ts > -1:
            ts_since = min((cur_ts - last_ts), 1000)
            alpha = np.power(alpha, ts_since / 1000)
        # print("alpha",alpha)
        result = max(curr_bitrate * (alpha - 1.0), 1000.0)

        return result

    def __aimd_change_bitrate(self, new_bitrate, cur_ts):
        '''
        该函数为整个码率控制算法的核心实现函数，主要流程包括：

            1根据输入的带宽检测信号，更新码率控制状态，在 ChangeState 函数中实现。
            2根据新的码率控制状态和最大码率的标准差，进行相应的码率控制，计算新的码率。
                - 如果码率控制状态为 hold，码率保持不变。
                - 如果码率控制状态为 increase，根据当前码率是否接近网络链路容量对其进行 加性增大 或者 乘性增大。
                - 如果码率控制状态为 decrease，对码率进行 乘性减小，并更新当前网络链路容量估计值的方差，即最大码率的方差。
            3控制新的码率值在一定范围内
        '''

        if self.input_incoming_bitrate == 0:
            self.input_incoming_bitrate = self.curr_rate

        if self.inited == -1 and self.input_state != kBwOverusing:
            return self.curr_rate

        self.__aimd_change_state(cur_ts)
        incoming_kbitrate = self.input_incoming_bitrate / 1000  #这里改成了kbps
        # print("max_kbitrate",self.avg_max_bitrate_kbps,self.var_max_bitrate_kbps)
        if self.avg_max_bitrate_kbps != -1:
            max_kbitrate = np.sqrt(self.avg_max_bitrate_kbps *
                                   self.var_max_bitrate_kbps)
        else:
            max_kbitrate = 0

        if self.state == kRcHold:
            # print("kRcHold")
            nothing_happened = True
        elif self.state == kRcIncrease:
            # print("increase")

            if self.avg_max_bitrate_kbps >= 0 and incoming_kbitrate > self.avg_max_bitrate_kbps + 3 * max_kbitrate:  #当前码率比平均最大码率大很多，进行倍数增
                # print("倍数增")
                self.__aimd_change_region(kRcMaxUnknown)

            if self.region == kRcNearMax:  # 加性增
                # print("加性增")
                new_bitrate += self.__additive_rate_increase(
                    cur_ts, self.time_last_bitrate_change)
            else:  #起始阶段，进行倍数性增
                # print("start 倍数性增")
                new_bitrate += self.__multiplicative_rate_increase(
                    cur_ts, self.time_last_bitrate_change, new_bitrate)
            self.time_last_bitrate_change = cur_ts
        elif self.state == kRcDecrease:
            # print("Decrease")
            new_bitrate = (self.beta * self.input_incoming_bitrate + 0.5)
            if new_bitrate > self.curr_rate:
                if self.region != kRcMaxUnknown:
                    new_bitrate = self.avg_max_bitrate_kbps * 1000 * self.beta + 0.5
                new_bitrate = min(new_bitrate, self.curr_rate)
            self.__aimd_change_region(kRcNearMax)

            if self.inited == 0 and self.input_incoming_bitrate < self.curr_rate:
                self.last_decrease = self.curr_rate - new_bitrate

            if incoming_kbitrate < self.avg_max_bitrate_kbps - 3 * max_kbitrate:
                self.avg_max_bitrate_kbps = -1.0

            self.inited = 0
            self.__update_max_bitrate_estimate(incoming_kbitrate)

            self.state = kRcHold
            self.time_last_bitrate_change = cur_ts

        return self.__clamp_bitrate(new_bitrate, self.input_incoming_bitrate)

    def aimd_set_start_bitrate(self, bitrate):
        self.curr_rate = bitrate
        self.inited = 0
        return

    # 判断aimd控制器是否可以进行网络带宽调节 需要修改
    def aimd_time_reduce_further(self, cur_ts, incoming_rate):
        reduce_interval = max(min(200, self.rtt), 10)
        if cur_ts - self.time_last_bitrate_change >= reduce_interval:
            return 0
        if self.inited == 0 and self.curr_rate / 2 > incoming_rate:
            return 0
        return -1

    def aimd_set_rtt(self, rtt):
        self.rtt = rtt
        return

    def aimd_set_min_bitrate(self, bitrate):
        self.min_rate = bitrate
        self.curr_rate = max(self.min_rate, self.curr_rate)
        return

    def aimd_set_max_bitrate(self, bitrate):
        self.max_rate = bitrate
        self.curr_rate = min(self.max_rate, self.curr_rate)
        return

    def aimd_update(
            self, cur_ts
    ):  #该函数为驱动 AimdRateControl 工作的外部接口函数，其内部调用私有成员函数 ChangeBitrate。
        if self.inited == -1:
            if self.time_first_incoming_estimate < 0:
                if self.input_incoming_bitrate > 0:
                    self.time_first_incoming_estimate = cur_ts
            elif cur_ts - self.time_first_incoming_estimate > k_initialization_ts and self.input_incoming_bitrate > 0:
                self.curr_rate = self.input_incoming_bitrate
                self.inited = 0

        self.curr_rate = self.__aimd_change_bitrate(self.curr_rate, cur_ts)

        return self.curr_rate

    def aimd_set_estimate(self, bitrate, cur_ts):
        self.inited = 0
        self.curr_rate = self.__clamp_bitrate(bitrate, bitrate)
        self.time_last_bitrate_change = cur_ts
        return

    def aimd_get_expected_bandwidth_period(self):
        Tobedone = True
        return

    def input_data(self, state, noise_var, incoming_bitdate):
        self.input_state = state
        self.input_noise_var = noise_var
        self.input_incoming_bitrate = incoming_bitdate
        return

    def aimd_set_start_bitrate(self, bitrate):
        self.curr_rate = bitrate
        self.inited = 0
