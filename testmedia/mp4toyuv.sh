#ffmpeg -i $1 -c:v rawvideo -r 30 -vf scale="1280:720" -vf trim="0:100" -pix_fmt yuv420p test.yuv
#ffmpeg -i $1 -c:v rawvideo -vf trim="0:100" -pix_fmt yuv420p test.yuv
#ffmpeg -i $1 -c:v rawvideo -pix_fmt yuv420p test.yuv
ffmpeg -i $1 -c:v rawvideo -r 24 -vf "scale=640:360, trim=0:100" -pix_fmt yuv420p test.yuv
ffmpeg -video_size 640x360 -i test.yuv -y test.y4m
