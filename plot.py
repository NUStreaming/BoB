import argparse
import numpy as np
import matplotlib.pyplot as plt
import re
import matplotlib.ticker as mticker


def plot_prediction(log_file, title=""):
    log_regex=".*time:(\d+) actual_bw:(\d+(\.\d*)?) predicted_bw:(\d+(\.\d*)?)"
    log_pattern = re.compile(log_regex, re.IGNORECASE)

    time_array=[]
    actual_bw_array=[]
    predicted_bw_array=[]
    time=0
    with open(log_file, 'r') as f:
        for line in f.readlines():
            if ("_bw:" not in line):
                continue
            line_matched = log_pattern.match(line)
            if line_matched:
                time = line_matched.group(1)
                actual_bw = float(line_matched.group(2))
                predicted_bw = float(line_matched.group(4))
                time_array.append(time)
                actual_bw_array.append(actual_bw)
                predicted_bw_array.append(predicted_bw)

    #print("Time=",time_array)
    #print("Measure BW",actual_bw_array)
    #print(predicted_bw_array)

    plt.plot(time_array, actual_bw_array)
    plt.plot(time_array, predicted_bw_array)
    plt.title(title)
    plt.legend(["Measured BW", "Predicted BW"])
    ax = plt.gca()
    #myLocator = mticker.MultipleLocator(50)
    #ax.xaxis.set_major_locator(myLocator)
    plt.xticks(rotation=20)
    ax.xaxis.set_major_locator(plt.MaxNLocator(10))
    plt.savefig("plot.png")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plot prediction")
    parser.add_argument("--title", type=str, default="", help="Title of the plot")
    parser.add_argument("--bandwidth_log", type=str, default="bandwidth_estimator.log", help="Bandwidth prediction log file")
    args = parser.parse_args()
    plot_prediction(log_file=args.bandwidth_log, title=args.title)