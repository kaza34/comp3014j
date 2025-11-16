import matplotlib.pyplot as plt
import numpy as np
import os
import statistics

def splitFile(filename):
    """Read and split a trace file into lines of lists."""
    lines = []
    with open(filename, 'r') as file:
        for line in file:
            lines.append(line.split())
    return lines

def calculate_packet_loss_rate(trace_lines):
    """Calculate packet loss rate for all TCP flows."""
    sent_packets = 0
    dropped_packets = 0
    for line in trace_lines:
        if len(line) < 5:
            continue
        event = line[0]
        pkt_type = line[4]
        # Count sent packets at the source queue and dropped packets
        if event == '+' and pkt_type == 'tcp':
            sent_packets += 1
        elif event == 'd' and pkt_type == 'tcp':
            dropped_packets += 1
    if sent_packets == 0:
        return 0.0
    return (dropped_packets / sent_packets) * 100

def calculate_jain_fairness_index(values):
    """Calculate Jain's fairness index for a set of values (e.g., throughputs)."""
    if not values or sum(values) == 0:
        return 0.0
    num_flows = len(values)
    sum_of_values = sum(values)
    sum_of_squares = sum(x ** 2 for x in values)
    return (sum_of_values ** 2) / (num_flows * sum_of_squares)

def calculate_coefficient_of_variation(data):
    """Calculate coefficient of variation (CoV) for stability analysis."""
    data = [x for x in data if x > 0]  # Filter out zero values
    if len(data) < 2:
        return 0.0  # Not enough data to calculate stdev
    mean = statistics.mean(data)
    stdev = statistics.stdev(data)
    return stdev / mean if mean > 0 else float('inf')

def extract_goodput_per_flow(trace_lines, flow_id, duration=100.0, time_window=0.1):
    """Extracts goodput in Mbps for a specific flow over time windows."""
    num_windows = int(duration / time_window)
    received_bytes = [0] * num_windows
    for line in trace_lines:
        if len(line) < 8:
            continue
        event, time, _, _, pkt_type, pkt_size, _, fid = line[:8]
        if event == 'r' and pkt_type == 'tcp' and fid == str(flow_id):
            try:
                time = float(time)
                pkt_size = int(pkt_size)
                window_index = int(time / time_window)
                if window_index < num_windows:
                    received_bytes[window_index] += pkt_size
            except (ValueError, IndexError):
                continue
    # Convert bytes per window to Mbps
    return [(bytes_in_window * 8) / (time_window * 1_000_000) for bytes_in_window in received_bytes]

def analyze_tcp_variants():
    """Main analysis function for Part A: Compare TCP variants."""
    tcp_variants = ['reno', 'cubic', 'yeah', 'vegas']
    trace_files = {v: f"{v}Trace.tr" for v in tcp_variants}

    results = {}

    print("Analyzing TCP Variants Performance...")
    print("=" * 50)

    for variant, filename in trace_files.items():
        if not os.path.exists(filename):
            print(f"Warning: Trace file {filename} not found for {variant}")
            continue

        lines = splitFile(filename)
        
        # --- CORE LOGIC ---
        # Extract goodput for each flow separately
        goodput_flow1 = extract_goodput_per_flow(lines, flow_id=1)
        goodput_flow2 = extract_goodput_per_flow(lines, flow_id=2)
        
        # Calculate total goodput by summing the windows
        total_goodput_over_time = [g1 + g2 for g1, g2 in zip(goodput_flow1, goodput_flow2)]
        
        # Calculate metrics
        avg_goodput = np.mean(total_goodput_over_time)
        plr = calculate_packet_loss_rate(lines)
        stability_cov = calculate_coefficient_of_variation(total_goodput_over_time)

        # For fairness, calculate the average goodput of each flow in the last third
        last_third_start_index = len(goodput_flow1) * 2 // 3
        avg_goodput_flow1_last_third = np.mean(goodput_flow1[last_third_start_index:])
        avg_goodput_flow2_last_third = np.mean(goodput_flow2[last_third_start_index:])
        
        jain_index = calculate_jain_fairness_index([avg_goodput_flow1_last_third, avg_goodput_flow2_last_third])
        
        results[variant] = {
            'goodput_ts': total_goodput_over_time,
            'avg_goodput': avg_goodput,
            'plr': plr,
            'stability': stability_cov,
            'fairness': jain_index
        }

        print(f"\n{variant.upper()} Results:")
        print(f"  Average Goodput (Mbps): {avg_goodput:.4f}")
        print(f"  Packet Loss Rate (%): {plr:.4f}")
        print(f"  Jain Fairness Index (Last Third): {jain_index:.4f}")
        print(f"  Stability (CoV): {stability_cov:.4f}")

    plot_results(results)
    return results

def plot_results(results):
    """Plot comparison charts with improved layout."""
    variants = list(results.keys())
    
    # 增大画布尺寸，给所有元素更多空间
    plt.figure(figsize=(15, 11)) 
    
    # --- Plot 1: Cumulative Goodput ---
    plt.subplot(2, 2, 1)
    for variant, data in results.items():
        time_steps = np.arange(len(data['goodput_ts'])) * 0.1
        cumulative_goodput = np.cumsum(data['goodput_ts']) * 0.1
        plt.plot(time_steps, cumulative_goodput, label=variant.upper())
    plt.title('Cumulative Goodput Over Time', fontsize=14)
    plt.xlabel('Time (seconds)', fontsize=12)
    plt.ylabel('Total Data Transmitted (Mbits)', fontsize=12)
    plt.legend()
    plt.grid(True, alpha=0.5)

    # --- Plot 2: Average Goodput ---
    plt.subplot(2, 2, 2)
    avg_goodputs = [d['avg_goodput'] for d in results.values()]
    bars = plt.bar(variants, avg_goodputs, color=['blue', 'green', 'red', 'purple'])
    plt.title('Average Goodput by TCP Variant', fontsize=14)
    plt.ylabel('Average Goodput (Mbps)', fontsize=12)
    # 为标签添加数值
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2.0, yval, f'{yval:.3f}', va='bottom', ha='center', fontsize=10)

    # --- Plot 3: Packet Loss Rate ---
    plt.subplot(2, 2, 3)
    plrs = [d['plr'] for d in results.values()]
    bars = plt.bar(variants, plrs, color=['blue', 'green', 'red', 'purple'])
    plt.title('Packet Loss Rate by TCP Variant', fontsize=14)
    plt.ylabel('Packet Loss Rate (%)', fontsize=12)
    # 为标签添加数值
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2.0, yval, f'{yval:.3f}%', va='bottom', ha='center', fontsize=10)

    # --- Plot 4: Jain Fairness Index ---
    plt.subplot(2, 2, 4)
    fairness_indices = [d['fairness'] for d in results.values()]
    bars = plt.bar(variants, fairness_indices, color=['blue', 'green', 'red', 'purple'])
    plt.title('Jain Fairness Index (Last Third)', fontsize=14)
    plt.ylabel('Fairness Index', fontsize=12)
    plt.ylim(0, 1.1)
    # 为标签添加数值
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2.0, yval, f'{yval:.3f}', va='bottom', ha='center', fontsize=10)

    # 关键：使用 tight_layout() 来自动调整，pad 参数增加边距
    plt.tight_layout(pad=3.0) 
    
    # 将图表保存为文件，这样就可以轻松地插入报告中
    plt.savefig('part_a_summary_plot.png', dpi=300)
    print("\nSaved summary plot to part_a_summary_plot.png")
    
    plt.show()
    
if __name__ == "__main__":
    analyze_tcp_variants()
    