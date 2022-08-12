BURST_THRESHOLD_MS = 5
OFFSET_THRESHOLD_MS = 3000  #3000ms
import copy


class Timestamp_group:
    def __init__(self):
        self.size = 0
        self.first_timestamp = 0
        self.timestamp = 0
        self.complete_ts = -1
        self.last_sys_ts = 0

    def reset(self):
        self.size = 0
        self.first_timestamp = 0
        self.timestamp = 0
        self.complete_ts = -1
        self.last_sys_ts = 0


class Interval_arrival:
    def __init__(self):
        self.prev_ts_group = Timestamp_group()
        self.cur_ts_group = Timestamp_group()

        self.num_consecutive = 0  # 连续的数量
        self.burst = 0

        self.time_group_len_ticks = 5  #*一个group的最大时间范围， 默认是5毫秒

    def __reset_group_ts(self):
        self.prev_ts_group.reset()
        self.cur_ts_group.reset()

    # 判断包是否是乱序，如果报文是前一个group的序列，不进行处理
    def __inter_arrival_in_order(self, ts):
        if self.cur_ts_group.complete_ts == -1:
            return 0
        if self.cur_ts_group.first_timestamp <= ts:
            return 0
        return -1

    def __belongs_to_burst(self, ts, arrival_ts):  #判断报文突发发送
        if self.burst == -1:
            return -1

        arrival_ts_delta = arrival_ts - self.cur_ts_group.complete_ts
        ts_delta = ts - self.cur_ts_group.timestamp
        if ts_delta == 0:
            return 0
        pro_delta = int(arrival_ts_delta - ts_delta)
        if pro_delta < 0 and arrival_ts_delta <= BURST_THRESHOLD_MS:
            return 0
        return -1

    def __inter_arrival_new_group(self, ts, arrival_ts):
        diff = 0
        if self.cur_ts_group.complete_ts == -1:
            return -1
        elif self.__belongs_to_burst(ts, arrival_ts) == 0:
            return -1
        else:
            diff = ts - self.cur_ts_group.first_timestamp
            return 0 if diff > self.time_group_len_ticks else -1
            # if diff > self.time_group_len_ticks:
            #     return 0
            # else:
            #     return -1


    def inter_arrival_compute_deltas(self,timestamp,arrival_ts,system_ts,size,\
        timestamp_delta,arrival_delta,size_delta):
        ret = -1
        timestamp_delta, arrival_delta, size_delta = timestamp_delta, arrival_delta, size_delta
        ts_delta = 0
        if (self.cur_ts_group.complete_ts == -1):

            self.cur_ts_group.timestamp = timestamp
            self.cur_ts_group.first_timestamp = timestamp
        elif self.__inter_arrival_in_order(timestamp) == -1:

            return ret, timestamp_delta, arrival_delta, size_delta
        elif self.__inter_arrival_new_group(timestamp, arrival_ts) == 0:

            if self.prev_ts_group.complete_ts >= 0:
                ts_delta = self.cur_ts_group.timestamp - self.prev_ts_group.timestamp
                arr_delta = self.cur_ts_group.complete_ts - self.prev_ts_group.complete_ts
                sys_delta = self.cur_ts_group.last_sys_ts - self.prev_ts_group.last_sys_ts

                if arr_delta > sys_delta + OFFSET_THRESHOLD_MS:
                    self.__reset_group_ts()
                    return ret, timestamp_delta, arrival_delta, size_delta
                if arr_delta < 0:
                    self.num_consecutive += 1
                    if self.num_consecutive > 3:
                        self.__reset_group_ts()
                    return ret, timestamp_delta, arrival_delta, size_delta
                else:
                    self.num_consecutive = 0
                size_delta = self.cur_ts_group.size - self.prev_ts_group.size
                timestamp_delta = ts_delta
                arrival_delta = arr_delta

                ret = 0
            # self.prev_ts_group=self.cur_ts_group # bug
            self.prev_ts_group = copy.deepcopy(self.cur_ts_group)  # 
            self.cur_ts_group.first_timestamp = timestamp
            self.cur_ts_group.timestamp = timestamp
            self.cur_ts_group.size = 0
        else:
            self.cur_ts_group.timestamp = max(self.cur_ts_group.timestamp,
                                              timestamp)

        self.cur_ts_group.size += size
        self.cur_ts_group.complete_ts = arrival_ts
        self.cur_ts_group.last_sys_ts = system_ts

        return ret, timestamp_delta, arrival_delta, size_delta
