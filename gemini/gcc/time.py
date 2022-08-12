import time

t0 = time.time() * 1000000  # 微妙 14位
t1 = int(t0 / 1000)  # 位数与 GET_SYS_MS()	相等
# 因此获取当前的毫秒大概就是time.time()*1000

print(t0)