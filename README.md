# Challenge-Example

This repository is an example about the submission of challenge https://2021.acmmmsys.org/rtc_challenge.php. Its zip package(https://github.com/OpenNetLab/Challenge-Example/archive/refs/heads/master.zip) can be directly uploaded as a bandwidth estimator to [OpenNetLab](https://opennetlab.org/) platform for this challenge.

## Challenge Manual

You need to design and implement a python class `Estimator` in the file, `BandwidthEstimator.py`, that is the interface to predict the bandwidth for AlphaRTC https://github.com/OpenNetLab/AlphaRTC#pyinfer.

```python
class Estimator(object):
    def report_states(self, stats: dict):
        '''
        stats is a dict with the following items
        {
            "send_time_ms": uint,
            "arrival_time_ms": uint,
            "payload_type": int,
            "sequence_number": uint,
            "ssrc": int,
            "padding_length": uint,
            "header_length": uint,
            "payload_size": uint
        }
        '''
        pass

    def get_estimated_bandwidth(self)->int:
        return int(1e6) # 1Mbps
```

### Notes

1. The `report_states` will be called by AlphaRTC core process and to tell the estimator RTC packets information with partial metadata above mentioned.
2. The `get_estimated_bandwidth` will also be called by AlphaRTC core process to fetch the predicted bandwidth by your estimator.
3. The two interfaces will be called in one thread and maybe get some side-effect if they take a long time to return.
4. The calling frequency of `report_states` is per RTC packet.
5. The calling frequency of `get_estimated_bandwidth` is about 200 milliseconds.
6. You can use any built-in library of `python 3.6.9` or third-parties libraries we pre-installed in [Challenge-Environment](https://github.com/OpenNetLab/Challenge-Environment).

## Submission Verification

```bash
# Pull the docker image of challenge environment
docker pull opennetlab.azurecr.io/challenge-env

# Download the configuration and test media
wget https://raw.githubusercontent.com/OpenNetLab/AlphaRTC/main/examples/peerconnection/serverless/corpus/receiver_pyinfer.json -O receiver_pyinfer.json
wget https://raw.githubusercontent.com/OpenNetLab/AlphaRTC/main/examples/peerconnection/serverless/corpus/sender_pyinfer.json -O sender_pyinfer.json
mkdir testmedia
wget https://github.com/OpenNetLab/AlphaRTC/raw/main/examples/peerconnection/serverless/corpus/testmedia/test.wav -O testmedia/test.wav
wget https://raw.githubusercontent.com/OpenNetLab/AlphaRTC/main/examples/peerconnection/serverless/corpus/testmedia/test.yuv -O testmedia/test.yuv

# Run your example
docker run -d --rm -v `pwd`:/app -w /app --name alphartc_pyinfer opennetlab.azurecr.io/challenge-env peerconnection_serverless receiver_pyinfer.json
docker exec alphartc_pyinfer peerconnection_serverless sender_pyinfer.json
```

If the `outvideo.yuv` and `outaudio.wav` are generated at the current folder, it means your bandwidth estimator has connected to AlphaRTC successfully.
