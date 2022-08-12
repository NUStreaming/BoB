#include <stdio.h>
#include <sys/time.h>
#include <stdlib.h>
//#define GET_SYS_MS()		(su_get_sys_time() / 1000) 毫秒

// int64_t su_get_sys_time()
// {
// 	struct timeval tv;
// 	gettimeofday(&tv, NULL);
// 	return tv.tv_usec + (int64_t)tv.tv_sec * 1000 * 1000; 微秒 + 1000*1000秒
// }
int main() //相当于su_get_sys_time()
{
    float time_use = 0;
    struct timeval start;
    struct timeval end;

    gettimeofday(&start, NULL); //gettimeofday(&start,&tz);结果一样 微秒，14位
    printf("start.tv_sec:%f\n", (start.tv_usec + (int64_t)start.tv_sec * 1000 * 1000) / 10e14);

    // struct timeval tv;
    // gettimeofday(&tv, NULL);
    // return tv.tv_usec + (int64_t)tv.tv_sec * 1000 * 1000;
}