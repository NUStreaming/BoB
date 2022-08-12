import collections

kMinNumDeltas = 60
threshold_gain_ = 4
kBurstIntervalMs = 5
kTrendlineWindowSize = 20
kTrendlineSmoothingCoeff = 0.9
kOverUsingTimeThreshold = 10
kMaxAdaptOffsetMs = 15.0
eta = 1.08 
alpha = 0.85  
k_up_ = 0.0087
k_down_ = 0.039
Time_Interval = 200


class HeuristicEstimator(object):
    def __init__(self):
        self.packets_list = []
        self.packet_group = []
        self.first_group_complete_time = -1

        self.acc_delay = 0
        self.smoothed_delay = 0
        self.acc_delay_list = collections.deque([])
        self.smoothed_delay_list = collections.deque([])

        self.state = 'Hold'
        self.last_bandwidth_estimation = 300 * 1000
        self.avg_max_bitrate_kbps_ = -1
        self.var_max_bitrate_kbps_ = -1
        self.rate_control_region_ = "kRcMaxUnknown"
        self.time_last_bitrate_change_ = -1 

        self.gamma1 = 12.5 
        self.num_of_deltas_ = 0
        self.time_over_using = -1 
        self.prev_trend = 0.0  
        self.overuse_counter = 0  
        self.overuse_flag = 'NORMAL'
        self.last_update_ms = -1
        self.last_update_threshold_ms = -1
        self.now_ms = -1

    # reset estimator according to rtc_env_gcc
    def reset(self):
        self.packets_list = []
        self.packet_group = []
        self.first_group_complete_time = -1

        self.acc_delay = 0
        self.smoothed_delay = 0
        self.acc_delay_list = collections.deque([])
        self.smoothed_delay_list = collections.deque([])

        self.state = 'Hold'
        self.last_bandwidth_estimation = 300 * 1000
        self.avg_max_bitrate_kbps_ = -1
        self.var_max_bitrate_kbps_ = -1
        self.rate_control_region_ = "kRcMaxUnknown"
        self.time_last_bitrate_change_ = -1 

        self.gamma1 = 12.5
        self.num_of_deltas_ = 0
        self.time_over_using = -1
        self.prev_trend = 0.0 
        self.overuse_counter = 0
        self.overuse_flag = 'NORMAL'
        self.last_update_ms = -1 
        self.last_update_threshold_ms = -1
        self.now_ms = -1

    def report_states(self, stats: dict):
        '''
        Store all packet header information for packets received within 200ms in packets_list
        '''
        pkt = stats
        packet_info = PacketInfo()
        packet_info.payload_type = pkt["payload_type"]
        packet_info.ssrc = pkt["ssrc"]
        packet_info.sequence_number = pkt["sequence_number"]
        packet_info.send_timestamp = pkt["send_time_ms"]
        packet_info.receive_timestamp = pkt["arrival_time_ms"]
        packet_info.padding_length = pkt["padding_length"]
        packet_info.header_length = pkt["header_length"]
        packet_info.payload_size = pkt["payload_size"]
        packet_info.size = pkt["header_length"] + pkt["payload_size"] + pkt["padding_length"]
        packet_info.bandwidth_prediction = self.last_bandwidth_estimation
        self.now_ms = packet_info.receive_timestamp  # use the arrival time of the last packet as the system time

        self.packets_list.append(packet_info)

    def get_estimated_bandwidth(self) -> int:
        '''
        Calculate estimated bandwidth
        '''
        BWE_by_delay, flag = self.get_estimated_bandwidth_by_delay()
        BWE_by_loss = self.get_estimated_bandwidth_by_loss()
        bandwidth_estimation = min(BWE_by_delay, BWE_by_loss)
        if flag == True:
            self.packets_list = []
        self.last_bandwidth_estimation = bandwidth_estimation
        return bandwidth_estimation,self.overuse_flag

    def get_inner_estimation(self):
        BWE_by_delay, flag = self.get_estimated_bandwidth_by_delay()
        BWE_by_loss = self.get_estimated_bandwidth_by_loss()
        bandwidth_estimation = min(BWE_by_delay, BWE_by_loss)
        if flag == True:
            self.packets_list = []
        return BWE_by_delay,BWE_by_loss

    def change_bandwidth_estimation(self,bandwidth_prediction):
        self.last_bandwidth_estimation = bandwidth_prediction

    def get_estimated_bandwidth_by_delay(self):
        '''
        Bandwidth estimation based on delay
        '''
        if len(self.packets_list) == 0:  # no packet is received within this time interval
            return self.last_bandwidth_estimation, False

        # 1. Divide packets
        pkt_group_list = self.divide_packet_group()
        if len(pkt_group_list) < 2: 
            return self.last_bandwidth_estimation, False

        # 2. Calculate the packet gradient
        send_time_delta_list, _, _, delay_gradient_list = self.compute_deltas_for_pkt_group(pkt_group_list)

        # 3. Calculate the trendline
        trendline = self.trendline_filter(delay_gradient_list, pkt_group_list)
        if trendline == None:
            return self.last_bandwidth_estimation, False

        # 4. Determine the current network status
        self.overuse_detector(trendline, sum(send_time_delta_list))

        # 5. Determine direction to bandwidth adjustment
        state = self.ChangeState()

        # 6. Adjust estimated bandwidth
        bandwidth_estimation = self.rate_adaptation_by_delay(state)

        return bandwidth_estimation, True

    def get_estimated_bandwidth_by_loss(self) -> int:
        '''
        Bandwidth estimation based on packet loss
        '''
        loss_rate = self.caculate_loss_rate()
        if loss_rate == -1:
            return self.last_bandwidth_estimation

        bandwidth_estimation = self.rate_adaptation_by_loss(loss_rate)
        return bandwidth_estimation

    def caculate_loss_rate(self):
        '''
        Calculate the packet loss rate in this time interval
        '''
        flag = False
        valid_packets_num = 0
        min_sequence_number, max_sequence_number = 0, 0
        if len(self.packets_list) == 0: # no packet is received within this time interval
            return -1
        for i in range(len(self.packets_list)):
            if self.packets_list[i].payload_type == 126:
                if not flag:
                    min_sequence_number = self.packets_list[i].sequence_number
                    max_sequence_number = self.packets_list[i].sequence_number
                    flag = True
                valid_packets_num += 1
                min_sequence_number = min(min_sequence_number, self.packets_list[i].sequence_number)
                max_sequence_number = max(max_sequence_number, self.packets_list[i].sequence_number)
        if (max_sequence_number - min_sequence_number) == 0:
            return -1
        receive_rate = valid_packets_num / (max_sequence_number - min_sequence_number)
        loss_rate = 1 - receive_rate
        return loss_rate

    def rate_adaptation_by_loss(self, loss_rate) -> int:
        '''
        Caculate Bandwidth estimation based on packet loss rate
        '''
        bandwidth_estimation = self.last_bandwidth_estimation
        if loss_rate > 0.1:
            bandwidth_estimation = self.last_bandwidth_estimation * (1 - 0.5 * loss_rate)
        elif loss_rate < 0.02:
            bandwidth_estimation = 1.05 * self.last_bandwidth_estimation
        return bandwidth_estimation

    def divide_packet_group(self):
        '''
        Divide packets
        '''
        pkt_group_list = []
        first_send_time_in_group = self.packets_list[0].send_timestamp

        pkt_group = [self.packets_list[0]]
        for pkt in self.packets_list[1:]:
            if pkt.send_timestamp - first_send_time_in_group <= kBurstIntervalMs:
                pkt_group.append(pkt)
            else:
                pkt_group_list.append(PacketGroup(pkt_group))
                if self.first_group_complete_time == -1:
                    self.first_group_complete_time = pkt_group[-1].receive_timestamp
                first_send_time_in_group = pkt.send_timestamp
                pkt_group = [pkt]
        return pkt_group_list

    def compute_deltas_for_pkt_group(self, pkt_group_list):
        '''
        Calculate the packet group time difference
        '''
        send_time_delta_list, arrival_time_delta_list, group_size_delta_list, delay_gradient_list = [], [], [], []
        for idx in range(1, len(pkt_group_list)): 
            send_time_delta = pkt_group_list[idx].send_time_list[-1] - pkt_group_list[idx - 1].send_time_list[-1]
            arrival_time_delta = pkt_group_list[idx].arrival_time_list[-1] - pkt_group_list[idx - 1].arrival_time_list[
                -1]
            group_size_delta = pkt_group_list[idx].pkt_group_size - pkt_group_list[idx - 1].pkt_group_size
            delay = arrival_time_delta - send_time_delta
            self.num_of_deltas_ += 1
            send_time_delta_list.append(send_time_delta)
            arrival_time_delta_list.append(arrival_time_delta)
            group_size_delta_list.append(group_size_delta)
            delay_gradient_list.append(delay)

        return send_time_delta_list, arrival_time_delta_list, group_size_delta_list, delay_gradient_list

    def trendline_filter(self, delay_gradient_list, pkt_group_list):
        '''
        Calculate the trendline from the delay gradient of the packet 
        '''
        for i, delay_gradient in enumerate(delay_gradient_list):
            accumulated_delay = self.acc_delay + delay_gradient
            smoothed_delay = kTrendlineSmoothingCoeff * self.smoothed_delay + (
                    1 - kTrendlineSmoothingCoeff) * accumulated_delay

            self.acc_delay = accumulated_delay
            self.smoothed_delay = smoothed_delay

            arrival_time_ms = pkt_group_list[i + 1].complete_time
            self.acc_delay_list.append(arrival_time_ms - self.first_group_complete_time)

            self.smoothed_delay_list.append(smoothed_delay)
            if len(self.acc_delay_list) > kTrendlineWindowSize:
                self.acc_delay_list.popleft()
                self.smoothed_delay_list.popleft()
        if len(self.acc_delay_list) == kTrendlineWindowSize:
            avg_acc_delay = sum(self.acc_delay_list) / len(self.acc_delay_list)
            avg_smoothed_delay = sum(self.smoothed_delay_list) / len(self.smoothed_delay_list)

            numerator = 0
            denominator = 0
            for i in range(kTrendlineWindowSize):
                numerator += (self.acc_delay_list[i] - avg_acc_delay) * (
                        self.smoothed_delay_list[i] - avg_smoothed_delay)
                denominator += (self.acc_delay_list[i] - avg_acc_delay) * (self.acc_delay_list[i] - avg_acc_delay)

            trendline = numerator / (denominator + 1e-05)
        else:
            trendline = None
            self.acc_delay_list.clear()
            self.smoothed_delay_list.clear()
            self.acc_delay = 0
            self.smoothed_delay = 0
        return trendline

    def overuse_detector(self, trendline, ts_delta):
        """
        Determine the current network status
        """
        # self.overuse_flag = 'NORMAL'
        now_ms = self.now_ms
        if self.num_of_deltas_ < 2:
            return

        modified_trend = trendline * min(self.num_of_deltas_, kMinNumDeltas) * threshold_gain_

        if modified_trend > self.gamma1:
            if self.time_over_using == -1:
                self.time_over_using = ts_delta / 2
            else:
                self.time_over_using += ts_delta
            self.overuse_counter += 1
            if self.time_over_using > kOverUsingTimeThreshold and self.overuse_counter > 1:
                if trendline > self.prev_trend:
                    self.time_over_using = 0
                    self.overuse_counter = 0
                    self.overuse_flag = 'OVERUSE'
        elif modified_trend < -self.gamma1:
            self.time_over_using = -1
            self.overuse_counter = 0
            self.overuse_flag = 'UNDERUSE'
        else:
            self.time_over_using = -1
            self.overuse_counter = 0
            self.overuse_flag = 'NORMAL'

        self.prev_trend = trendline
        self.update_threthold(modified_trend, now_ms)

    def update_threthold(self, modified_trend, now_ms):
        '''
        Update the threshold for determining overload
        '''
        if self.last_update_threshold_ms == -1:
            self.last_update_threshold_ms = now_ms
        if abs(modified_trend) > self.gamma1 + kMaxAdaptOffsetMs:
            self.last_update_threshold_ms = now_ms
            return
        if abs(modified_trend) < self.gamma1:
            k = k_down_
        else:
            k = k_up_
        kMaxTimeDeltaMs = 100
        time_delta_ms = min(now_ms - self.last_update_threshold_ms, kMaxTimeDeltaMs)
        self.gamma1 += k * (abs(modified_trend) - self.gamma1) * time_delta_ms
        if (self.gamma1 < 6):
            self.gamma1 = 6
        elif (self.gamma1 > 600):
            self.gamma1 = 600
        self.last_update_threshold_ms = now_ms

    def state_transfer(self):
        '''
        Update the direction of estimated bandwidth adjustment
        '''
        newstate = None
        overuse_flag = self.overuse_flag
        if self.state == 'Decrease' and overuse_flag == 'OVERUSE':
            newstate = 'Decrease'
        elif self.state == 'Decrease' and (overuse_flag == 'NORMAL' or overuse_flag == 'UNDERUSE'):
            newstate = 'Hold'
        elif self.state == 'Hold' and overuse_flag == 'OVERUSE':
            newstate = 'Decrease'
        elif self.state == 'Hold' and overuse_flag == 'NORMAL':
            newstate = 'Increase'
        elif self.state == 'Hold' and overuse_flag == 'UNDERUSE':
            newstate = 'Hold'
        elif self.state == 'Increase' and overuse_flag == 'OVERUSE':
            newstate = 'Decrease'
        elif self.state == 'Increase' and overuse_flag == 'NORMAL':
            newstate = 'Increase'
        elif self.state == 'Increase' and overuse_flag == 'UNDERUSE':
            newstate = 'Hold'
        else:
            print('Wrong state!')
        self.state = newstate
        return newstate

    def ChangeState(self):
        overuse_flag = self.overuse_flag
        if overuse_flag == 'NORMAL':
            if self.state == 'Hold':
                self.state = 'Increase'
        elif overuse_flag == 'OVERUSE':
            if self.state != 'Decrease':
                self.state = 'Decrease'
        elif overuse_flag == 'UNDERUSE':
            self.state = 'Hold'
        return self.state

    def rate_adaptation_by_delay(self, state):
        '''
        Determine the final bandwidth estimation
        '''
        estimated_throughput = 0
        for pkt in self.packets_list:
            estimated_throughput += pkt.size
        if len(self.packets_list) == 0:
            estimated_throughput_bps = 0
        else:
            time_delta = self.now_ms - self.packets_list[0].receive_timestamp
            time_delta = max(time_delta , Time_Interval)
            estimated_throughput_bps = 1000 * 8 * estimated_throughput / time_delta
        estimated_throughput_kbps = estimated_throughput_bps / 1000
     
        troughput_based_limit = 3 * estimated_throughput_bps + 10
        '''
        Calculate the standard deviation of the maximum throughput
        '''
        self.UpdateMaxThroughputEstimate(estimated_throughput_kbps)
        std_max_bit_rate = pow(self.var_max_bitrate_kbps_ * self.avg_max_bitrate_kbps_, 0.5)

        if state == 'Increase':
            if self.avg_max_bitrate_kbps_ >= 0 and \
                    estimated_throughput_kbps > self.avg_max_bitrate_kbps_ + 3 * std_max_bit_rate:
                self.avg_max_bitrate_kbps_ = -1.0
                self.rate_control_region_ = "kRcMaxUnknown"

            if self.rate_control_region_ == "kRcNearMax":
                # Already close to maximum, additivity increase
                additive_increase_bps = self.AdditiveRateIncrease(self.now_ms, self.time_last_bitrate_change_)
                bandwidth_estimation = self.last_bandwidth_estimation + additive_increase_bps
            elif self.rate_control_region_ == "kRcMaxUnknown":
                # Maximum value unknown, multiplicative increase
                multiplicative_increase_bps = self.MultiplicativeRateIncrease(self.now_ms,
                                                                              self.time_last_bitrate_change_)
                bandwidth_estimation = self.last_bandwidth_estimation + multiplicative_increase_bps
            else:
                print("error!")
            bandwidth_estimation = min(bandwidth_estimation,troughput_based_limit)
            self.time_last_bitrate_change_ = self.now_ms
        elif state == 'Decrease':
            beta = 0.85
            bandwidth_estimation = beta * estimated_throughput_bps + 0.5
            if bandwidth_estimation > self.last_bandwidth_estimation:
                if self.rate_control_region_ != "kRcMaxUnknown":
                    bandwidth_estimation = (beta * self.avg_max_bitrate_kbps_ * 1000 + 0.5)
                bandwidth_estimation = min(bandwidth_estimation, self.last_bandwidth_estimation)
            self.rate_control_region_ = "kRcNearMax"

            if estimated_throughput_kbps < self.avg_max_bitrate_kbps_-3*std_max_bit_rate:
                self.avg_max_bitrate_kbps_ = -1
            self.UpdateMaxThroughputEstimate(estimated_throughput_kbps)

            self.state='Hold'
            self.time_last_bitrate_change_ = self.now_ms
        elif state == 'Hold':
            bandwidth_estimation = self.last_bandwidth_estimation
        else:
            print('Wrong State!')
        return bandwidth_estimation

    def AdditiveRateIncrease(self, now_ms, last_ms):
        """
        Implementation of additive rate growth algorithm
        """
        sum_packet_size, avg_packet_size = 0, 0
        for pkt in self.packets_list:
            sum_packet_size += pkt.size
        avg_packet_size = 8 * sum_packet_size / len(self.packets_list)

        beta = 0.0
        RTT = 2 * (self.packets_list[-1].receive_timestamp - self.packets_list[-1].send_timestamp)
        response_time = 200

        if last_ms > 0:
            beta = min(((now_ms - last_ms) / response_time), 1.0)
        additive_increase_bps = max(800, beta * avg_packet_size)
        return additive_increase_bps

    def MultiplicativeRateIncrease(self, now_ms, last_ms):
        """
        Implementation of Multiplicative rate growth algorithm
        """
        alpha = 1.08
        if last_ms > -1:
            time_since_last_update_ms = min(now_ms - last_ms, 1000)
            alpha = pow(alpha, time_since_last_update_ms / 1000)
        multiplicative_increase_bps = max(self.last_bandwidth_estimation * (alpha - 1.0), 1000.0)
        return multiplicative_increase_bps

    def UpdateMaxThroughputEstimate(self, estimated_throughput_kbps):
        """
        Update estimates of the maximum throughput
        """
        alpha = 0.05
        if self.avg_max_bitrate_kbps_ == -1:
            self.avg_max_bitrate_kbps_ = estimated_throughput_kbps
        else:
            self.avg_max_bitrate_kbps_ = (1 - alpha) * self.avg_max_bitrate_kbps_ + alpha * estimated_throughput_kbps
        norm = max(self.avg_max_bitrate_kbps_, 1.0)
        var_value = pow((self.avg_max_bitrate_kbps_ - estimated_throughput_kbps), 2) / norm
        self.var_max_bitrate_kbps_ = (1 - alpha) * self.var_max_bitrate_kbps_ + alpha * var_value
        if self.var_max_bitrate_kbps_ < 0.4:
            self.var_max_bitrate_kbps_ = 0.4
        if self.var_max_bitrate_kbps_ > 2.5:
            self.var_max_bitrate_kbps_ = 2.5


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

class PacketGroup:
    def __init__(self, pkt_group):
        self.pkts = pkt_group
        self.arrival_time_list = [pkt.receive_timestamp for pkt in pkt_group]
        self.send_time_list = [pkt.send_timestamp for pkt in pkt_group]
        self.pkt_group_size = sum([pkt.size for pkt in pkt_group])
        self.pkt_num_in_group = len(pkt_group)
        self.complete_time = self.arrival_time_list[-1]
        self.transfer_duration = self.arrival_time_list[-1] - self.arrival_time_list[0]
