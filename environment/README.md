# Challenge Environment

This repository provides a container of the runtime environment for challenge https://2021.acmmmsys.org/rtc_challenge.php. It includes the RTC system, [AlphaRTC](https://github.com/OpenNetLab/AlphaRTC), and the evaluation system.

Because the challenge requires contestants to submit a bandwidth estimator for RTC system. Considering the tradeoff between resource limitation, efficiency and security, we will only provides pre-installed third-parties library in our challenge runtime environment that can be found at the [Dockerfile](dockers/Dockerfile).

If you want to add **more extensions** in the runtime environment, please create issue on this repository, we will discuss with OpenNetLab community about your proposal.

## Get the pre-provided docker image

```bash
run `make all` to create challenge-env docker image with tc in it
```
