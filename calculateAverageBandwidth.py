import argparse

def calculateAverageBW(networkProfileFileName):

    with open(networkProfileFileName, 'r') as fp:
        networkProfileData = fp.readlines()

    sumBw = 0
    totalDuration = 0
    lastBw = 0

    for line in networkProfileData:
        if line.startswith("rate"):
            lastBw=float(line.split()[1].strip().replace("kbit",""))
        elif line.startswith("wait"):
            duration=float(line.split()[1].strip().replace("s",""))
            sumBw += float(duration) * float(lastBw)
            totalDuration += duration
        
    averageBandwidth = sumBw / totalDuration
    print("averageBandwidth: {}".format(averageBandwidth))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="calculate average bw for tc")
    parser.add_argument("--network_profile", type=str, default=None, help="network profile file")
    args = parser.parse_args()
    if args.network_profile == None:
        raise argparse.ArgumentError("--network_profile cannot be empty")
    calculateAverageBW(args.network_profile)
