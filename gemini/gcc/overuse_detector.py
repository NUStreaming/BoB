# 网络过载检测器
import numpy as np

kMaxAdaptOffsetMs = 15.0
kOverUsingTimeThreshold = 20
kMinNumDeltas = 60
kMaxTimeDeltaMs = 100

kBwNormal = 0
kBwUnderusing = 1
kBwOverusing = 2


class Overdetector:
    def __init__(self):
        self.k_up = 0.0187
        self.k_down = 0.039
        self.overusing_time_threshold = kOverUsingTimeThreshold
        self.threshold = 12.5
        self.time_over_using = -1
        self.prev_offset = 0

        self.update_ts = -1
        self.overuse_counter = 0

        self.state = kBwNormal

    # 更新过载的阈值
    def __overuse_update_threshold(self, modified_offset, cur_ts):
        if self.update_ts == -1:
            self.update_ts = cur_ts

        if np.fabs(modified_offset) > self.threshold + kMaxAdaptOffsetMs:
            self.update_ts = cur_ts
            return

        k = self.k_down if np.fabs(
            modified_offset) < self.threshold else self.k_up
        time_delta = min(cur_ts - self.update_ts, kMaxTimeDeltaMs)

        self.threshold += k * (np.fabs(modified_offset) -
                               self.threshold) * time_delta
        self.threshold = np.clip(self.threshold, 6, 600)

        self.update_ts = cur_ts

    def overuse_detect(self, offset, ts_delta, num_of_deltas, cur_ts):

        if num_of_deltas < 2:
            return kBwNormal

        T = min(num_of_deltas, kMinNumDeltas) * offset
        # print("T offset",T,offset,self.threshold)

        if T > self.threshold:  #计算累计的overusing值
            if self.time_over_using == -1:
                self.time_over_using = ts_delta / 2
            else:
                self.time_over_using += ts_delta

            self.overuse_counter += 1

            if self.time_over_using > self.overusing_time_threshold and self.overuse_counter > 1:
                if offset >= self.prev_offset:  #连续两次以上传输延迟增量增大，表示网络已经过载了，需要进行带宽减小
                    self.time_over_using = 0
                    self.overuse_counter = 0
                    self.state = kBwOverusing
        elif T < -self.threshold:  #网络延迟增量逐步缩小，需要加大带宽码率
            self.time_over_using = -1
            self.overuse_counter = 0
            self.state = kBwUnderusing
        else:
            self.time_over_using = -1
            self.overuse_counter = 0
            self.state = kBwNormal

        self.prev_offset = offset

        self.__overuse_update_threshold(T, cur_ts)
        return self.state