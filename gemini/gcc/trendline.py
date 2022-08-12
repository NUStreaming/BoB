import numpy as np
'''

typedef struct
{
	double arrival_delta;
	double smoothed_delay;
}delay_hist_t;

'''
TRENDLINE_MAX_COUNT = 1000


class Trendline_estimator:
    def __init__(self, window_size=20, smoothing_coef=0.9, threshold_gain=4.0):
        #下面三个需要初始化处理
        #对累计延迟梯度平滑值进行最小二乘法线性回归之后求得延迟梯度趋势，会乘以增益并和阈值作比较，以检测带宽使用状态
        self.window_size = window_size  #窗口大小;窗口大小决定收到多少包组之后开始计算延迟梯度趋势
        #smoothed_delay_ = smoothing_coef_ * smoothed_delay_ +(1 - smoothing_coef_) * accumulated_delay_;
        self.smoothing_coef = smoothing_coef  # 平滑系数 平滑系数用于累计延迟梯度的一次指数平滑计算
        self.threshold_gain = threshold_gain  #延迟梯度趋势的增益

        self.num_of_deltas = 0
        self.first_arrival_ts = -1

        self.acc_delay = 0
        self.smoothed_delay = 0.0

        self.trendline = 0.0

        self.index = 0

        ## C版本：self.que=[] # 里面是一个二元组组成的:arrival_delta,smoothed_delay
        # 下面两个滑动窗口定长，初始化
        self.arrival_delta_list = [0.0 for _ in range(self.window_size)]
        self.smoothed_delay_list = [0.0 for _ in range(self.window_size)]

    def __linear_fit_slope(self):  #
        avg_x = avg_y = 0
        avg_x = np.mean(self.arrival_delta_list)
        avg_y = np.mean(self.smoothed_delay_list)

        numerator = np.sum(
            list(
                map(lambda x: (x[0] - avg_x) * (x[1] - avg_y),
                    zip(self.arrival_delta_list, self.smoothed_delay_list))))
        denominator = np.sum(
            list(
                map(lambda x: (x[0] - avg_x) * (x[0] - avg_x),
                    zip(self.arrival_delta_list, self.smoothed_delay_list))))
        if denominator != 0:
            return numerator / denominator
        else:
            return 0

    def trendline_update(self, recv_delta_ms, send_delta_ms, arrival_ts):
        delta_ms = recv_delta_ms - send_delta_ms
        self.num_of_deltas += 1
        if (self.num_of_deltas > TRENDLINE_MAX_COUNT):
            self.num_of_deltas = TRENDLINE_MAX_COUNT
        if (self.first_arrival_ts == -1):
            self.first_arrival_ts = arrival_ts

        self.acc_delay += delta_ms
        self.smoothed_delay = self.smoothing_coef + self.smoothed_delay + (
            1 - self.smoothing_coef) * self.acc_delay

        # 窗口更新；实际上只记录窗口里面的值
        self.index += 1

        hist_index = self.index % self.window_size
        self.arrival_delta_list[
            hist_index] = arrival_ts - self.first_arrival_ts
        self.smoothed_delay_list[
            hist_index] = self.smoothed_delay  # bug find,这块更新错误，之前self.smoothed_delay_list和self.smoothed混用

        if self.index >= self.window_size:
            self.trendline = self.__linear_fit_slope()
        # print("trendline",self.trendline)

        return

    def trendline_slope(self):
        return self.threshold_gain * self.trendline

    def reset(self, window_size=5, smoothing_coef=0.9, threshold_gain=1):
        # 重新初始化
        #下面三个需要初始化处理
        #对累计延迟梯度平滑值进行最小二乘法线性回归之后求得延迟梯度趋势，会乘以增益并和阈值作比较，以检测带宽使用状态
        self.window_size = window_size  #窗口大小;窗口大小决定收到多少包组之后开始计算延迟梯度趋势
        #smoothed_delay_ = smoothing_coef_ * smoothed_delay_ +(1 - smoothing_coef_) * accumulated_delay_;
        self.smoothing_coef = smoothing_coef  # 平滑系数 平滑系数用于累计延迟梯度的一次指数平滑计算
        self.threshold_gain = threshold_gain  #延迟梯度趋势的增益

        self.num_of_deltas = 0
        self.first_arrival_ts = -1

        self.acc_delay = 0
        self.smoothed_delay = 0.0

        self.trendline = 0.0

        self.index = 0

        ## C版本：self.que=[] # 里面是一个二元组组成的:arrival_delta,smoothed_delay
        # 下面两个滑动窗口定长，初始化
        self.arrival_delta_list = [0.0 for _ in range(self.window_size)]
        self.smoothed_delay_list = [0.0 for _ in range(self.window_size)]
