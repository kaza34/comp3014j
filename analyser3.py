import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from math import ceil
import os
import statistics

def splitFile(filename):
    """Read and split a trace file into lines of lists"""
    lines = []
    with open(filename, 'r') as file:
        for line in file:
            lines.append(line.split())
    return lines

def extract_throughput_data(trace_lines, flow_id, total_time=1000):
    """Extract throughput data from trace file for a specific flow"""
    # Initialize arrays to store received packet counts
    packet_count = [0] * (total_time + 1)  # Packets received per second
    
    for line in trace_lines:
        if len(line) < 4:
            continue
            
        # Check for received packets ('r' for receive)
        if line[0] == 'r' and line[7] == 'tcp':
            try:
                time = float(line[1])
                src_node = line[2]
                dst_node = line[3]
                
                # Assuming flow_id identifies the flow we're interested in
                # This may need adjustment depending on your specific topology
                if src_node == '0' or src_node == '1':  # Nodes of interest
                    sec = int(time)
                    if sec <= total_time:
                        packet_count[sec] += 1
            except (ValueError, IndexError):
                continue
    
    # Convert to throughput (packets per second) over time
    throughput = [count for count in packet_count]
    return throughput

def calculate_goodput(trace_lines, flow_id, total_time=1000):
    """Calculate goodput in Mbps for a specific flow"""
    # Calculate the total data transmitted for goodput
    time_data = []  # List of (time, bytes) tuples
    
    for line in trace_lines:
        if len(line) < 4:
            continue
            
        # Check for received packets ('r' for receive)
        if line[0] == 'r' and line[7] == 'tcp':
            try:
                time = float(line[1])
                packet_size = int(line[5])  # Size in bytes
                
                time_data.append((time, packet_size))
            except (ValueError, IndexError):
                continue
    
    # Calculate goodput per second 
    bytes_per_second = [0] * (total_time + 1)
    
    for time, bytes_val in time_data:
        sec = int(time)
        if sec <= total_time:
            bytes_per_second[sec] += bytes_val
    
    # Convert bytes to Mbps
    goodput_mbps = [bytes_sec * 8 / 1e6 for bytes_sec in bytes_per_second]
    return goodput_mbps

def calculate_packet_loss_rate(trace_lines):
    """Calculate packet loss rate"""
    total_sent = 0
    total_dropped = 0
    
    for line in trace_lines:
        if len(line) < 4:
            continue
            
        # Count sent packets
        if line[0] == '+' and line[7] == 'tcp':  # Packet sent
            total_sent += 1
        elif line[0] == 'd' and line[7] == 'tcp':  # Packet dropped
            total_dropped += 1
    
    if total_sent == 0:
        return 0.0
    
    loss_rate = (total_dropped / total_sent) * 100  # As percentage
    return loss_rate

def calculate_jain_fairness_index(values):
    """Calculate Jain's fairness index for a set of values"""
    if len(values) == 0 or all(v == 0 for v in values):
        return 0.0
    
    sum_squared = sum([v**2 for v in values])
    squared_sum = sum(values)**2
    
    if sum_squared == 0:
        return 0.0
    
    jain_index = squared_sum / (len(values) * sum_squared)
    return jain_index

def calculate_coefficient_of_variation(data):
    """Calculate coefficient of variation (CoV) for stability analysis"""
    if not data or len(data) == 0:
        return 0.0
    
    # Filter out zero values for stability calculation
    filtered_data = [x for x in data if x > 0]
    if not filtered_data:
        return float('inf')  # High instability if no valid data
    
    mean = statistics.mean(filtered_data)
    if mean == 0:
        return float('inf')
    
    std_dev = statistics.stdev(filtered_data) if len(filtered_data) > 1 else 0
    cov = std_dev / mean
    
    return cov

def extract_flow_data(trace_lines, node_id, total_time=1000):
    """Extract data specifically for a given node"""
    received_bytes = [0] * (total_time + 1)  # Bytes received per second
    
    for line in trace_lines:
        if len(line) < 8:
            continue
            
        event_type = line[0]  # +, -, r, d
        time = float(line[1])
        src_node = line[2]
        dst_node = line[3]
        packet_type = line[7]  # tcp, ack, etc.
        packet_size = int(line[5])  # Size in bytes
        
        if event_type == 'r' and packet_type == 'tcp':  # Received TCP packet
            # If interested in packets going to a specific node
            if dst_node == str(node_id):
                sec = int(time)
                if 0 <= sec <= total_time:
                    received_bytes[sec] += packet_size
    
    # Convert bytes to Mbps per second
    goodput_mbps = [bytes_sec * 8 / 1e6 for bytes_sec in received_bytes]
    return goodput_mbps

def analyze_tcp_variants():
    """Main analysis function for Part A: Compare TCP variants"""
    
    # TCP variants to analyze
    tcp_variants = ['reno', 'cubic', 'yeah', 'vegas']
    trace_files = {variant: f"{variant}Trace.tr" for variant in tcp_variants}
    
    # Data structures to store results
    goodputs = {}
    plrs = {}  # Packet Loss Rates
    final_third_goodputs = {}  # For fairness analysis
    
    print("Analyzing TCP Variants Performance...")
    print("="*50)
    
    # Analyze each TCP variant
    for variant in tcp_variants:
        trace_lines = splitFile(trace_files[variant])
        
        # Calculate goodput for node 4 and node 5 (assuming these are the receiver nodes)
        goodput_node4 = extract_flow_data(trace_lines, 4)
        goodput_node5 = extract_flow_data(trace_lines, 5)
        
        # Total goodput is sum of both flows
        total_goodput = [g4 + g5 for g4, g5 in zip(goodput_node4, goodput_node5)]
        
        goodputs[variant] = total_goodput
        plrs[variant] = calculate_packet_loss_rate(trace_lines)
        
        # Extract final third data for fairness analysis
        third_point = len(total_goodput) // 3 * 2  # Start of last third
        final_third_data = total_goodput[third_point:]
        
        # Calculate per-node goodput for fairness
        final_third_node4 = goodput_node4[third_point:]
        final_third_node5 = goodput_node5[third_point:]
        
        # Average goodput for each flow in the final third
        avg_node4 = sum(final_third_node4) / len(final_third_node4) if len(final_third_node4) > 0 else 0
        avg_node5 = sum(final_third_node5) / len(final_third_node5) if len(final_third_node5) > 0 else 0
        
        final_third_goodputs[variant] = [avg_node4, avg_node5]
        
        print(f"\n{variant.upper()} Results:")
        print(f"  Total Goodput (Mbps): {sum(total_goodput):.4f}")
        print(f"  Average Goodput (Mbps): {sum(total_goodput)/len(total_goodput):.4f}")
        print(f"  Packet Loss Rate (%): {plrs[variant]:.4f}")
        print(f"  Final Third Average Goodput - Node 4: {avg_node4:.4f} Mbps")
        print(f"  Final Third Average Goodput - Node 5: {avg_node5:.4f} Mbps")
    
    # Task 1: Create table of goodput and PLR
    print("\n" + "="*50)
    print("TASK 1: Total Goodput and Packet Loss Rate Table")
    print("="*50)
    print(f"{'TCP Variant':<10} {'Total Goodput (Mbps)':<20} {'Avg Goodput (Mbps)':<20} {'PLR (%)':<10}")
    print("-" * 70)
    for variant in tcp_variants:
        total_goodput = sum(goodputs[variant])
        avg_goodput = total_goodput / len(goodputs[variant])
        plr = plrs[variant]
        print(f"{variant:<10} {total_goodput:<20.4f} {avg_goodput:<20.4f} {plr:<10.4f}")
    
    # Task 2: Jain Fairness Index for the last third
    print("\n" + "="*50)
    print("TASK 2: Jain Fairness Index (Last Third)")
    print("="*50)
    fairness_indices = {}
    for variant in tcp_variants:
        values = final_third_goodputs[variant]
        jain_index = calculate_jain_fairness_index(values)
        fairness_indices[variant] = jain_index
        print(f"{variant.upper()}: {jain_index:.4f}")
    
    # Task 3: Stability analysis (Coefficient of Variation)
    print("\n" + "="*50)
    print("TASK 3: Throughput Stability (Coefficient of Variation)")
    print("="*50)
    stabilities = {}
    for variant in tcp_variants:
        cov = calculate_coefficient_of_variation(goodputs[variant])
        stabilities[variant] = cov
        print(f"{variant.upper()}: {cov:.4f}")
    
    # Task 4: Overall summary
    print("\n" + "="*50)
    print("TASK 4: Overall Algorithm Performance Summary")
    print("="*50)
    
    # Find best algorithm based on multiple metrics
    best_goodput = max(goodputs.keys(), key=lambda k: sum(goodputs[k]))
    best_fairness = max(fairness_indices.keys(), key=lambda k: fairness_indices[k])
    best_stability = min(stabilities.keys(), key=lambda k: stabilities[k])
    lowest_plr = min(plrs.keys(), key=lambda k: plrs[k])
    
    print(f"Best Total Goodput: {best_goodput.upper()}")
    print(f"Best Fairness: {best_fairness.upper()}")
    print(f"Best Stability: {best_stability.upper()}")
    print(f"Lowest Packet Loss Rate: {lowest_plr.upper()}")
    
    # Visualization
    plot_results(goodputs, plrs, fairness_indices, stabilities)
    
    return goodputs, plrs, fairness_indices, stabilities

def plot_results(goodputs, plrs, fairness_indices, stabilities):
    """Plot comparison charts for goodput and PLR"""
    tcp_variants = list(goodputs.keys())
    
    # Plot 1: Goodput over time
    plt.figure(figsize=(14, 10))
    
    plt.subplot(2, 2, 1)
    for variant in tcp_variants:
        cumulative_goodput = np.cumsum(goodputs[variant])
        plt.plot(cumulative_goodput[:500], label=f'{variant.upper()}', linewidth=1.5)  # Limit to first 500 seconds to see trend
    plt.title('Cumulative Goodput Over Time')
    plt.xlabel('Time (seconds)')
    plt.ylabel('Cumulative Goodput (Mbps)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # Plot 2: Average Goodput per variant
    plt.subplot(2, 2, 2)
    avg_goodputs = [sum(goodputs[v])/len(goodputs[v]) for v in tcp_variants]
    bars = plt.bar(tcp_variants, avg_goodputs, color=['blue', 'green', 'red', 'purple'])
    plt.title('Average Goodput by TCP Variant')
    plt.xlabel('TCP Variant')
    plt.ylabel('Average Goodput (Mbps)')
    plt.grid(True, alpha=0.3, axis='y')
    
    # Add value labels on bars
    for bar, value in zip(bars, avg_goodputs):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(avg_goodputs)*0.01,
                 f'{value:.3f}', ha='center', va='bottom')
    
    # Plot 3: Packet Loss Rate
    plt.subplot(2, 2, 3)
    plr_values = [plrs[v] for v in tcp_variants]
    bars = plt.bar(tcp_variants, plr_values, color=['blue', 'green', 'red', 'purple'])
    plt.title('Packet Loss Rate by TCP Variant')
    plt.xlabel('TCP Variant')
    plt.ylabel('Packet Loss Rate (%)')
    plt.grid(True, alpha=0.3, axis='y')
    
    # Add value labels on bars
    for bar, value in zip(bars, plr_values):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(plr_values)*0.01,
                 f'{value:.3f}%', ha='center', va='bottom')
    
    # Plot 4: Jain Fairness Index
    plt.subplot(2, 2, 4)
    fairness_values = [fairness_indices[v] for v in tcp_variants]
    bars = plt.bar(tcp_variants, fairness_values, color=['blue', 'green', 'red', 'purple'])
    plt.title('Jain Fairness Index (Last Third)')
    plt.xlabel('TCP Variant')
    plt.ylabel('Fairness Index')
    plt.ylim(0, 1.1)
    plt.grid(True, alpha=0.3, axis='y')
    
    # Add value labels on bars
    for bar, value in zip(bars, fairness_values):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(fairness_values)*0.01,
                 f'{value:.3f}', ha='center', va='bottom')
    
    plt.tight_layout()
    plt.show()
    
    # Additional plot: Stability (Coefficient of Variation)
    plt.figure(figsize=(10, 6))
    stability_values = [stabilities[v] for v in tcp_variants]
    bars = plt.bar(tcp_variants, stability_values, color=['blue', 'green', 'red', 'purple'])
    plt.title('Throughput Stability (Coefficient of Variation)')
    plt.xlabel('TCP Variant')
    plt.ylabel('Coefficient of Variation (Lower is More Stable)')
    plt.grid(True, alpha=0.3, axis='y')
    
    # Add value labels on bars
    for bar, value in zip(bars, stability_values):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(stability_values)*0.01,
                 f'{value:.3f}', ha='center', va='bottom')
    
    plt.tight_layout()
    plt.show()

def part_b_analysis():
    """Analysis for Part B: DropTail vs RED queue management"""
    print("\n" + "="*60)
    print("PART B ANALYSIS: DropTail vs RED QUEUE MANAGEMENT")
    print("="*60)
    print("Note: For this analysis, you would need to run simulations with")
    print("both DropTail and RED queue management algorithms and compare:")
    print("- Goodput")
    print("- Packet Loss Rate (PLR)")
    print("- Fairness (Jain Index)")
    print("- Stability (Coefficient of Variation)")
    print("\nTo implement this, modify your .tcl files to use different")
    print("queue management algorithms and run this analysis on both sets")
    print("of trace files.")

def part_c_analysis():
    """Analysis for Part C: Repeatability with confidence intervals"""
    print("\n" + "="*60)
    print("PART C ANALYSIS: Repeatability and Confidence Intervals")
    print("="*60)
    print("Note: For this analysis, you would need to:")
    print("1. Run 5 simulations with different random seeds")
    print("2. Collect the metric of interest (e.g., average goodput)")
    print("3. Calculate mean and 95% confidence interval")
    print("4. Use the formula: X̄ ± 1.96 × (s / √n)")
    print("\nHere's an example implementation for confidence intervals:")
    
    # Example of how to calculate confidence interval
    sample_data = [1.2, 1.3, 1.1, 1.4, 1.25]  # Example goodput values from 5 runs
    n = len(sample_data)
    mean = sum(sample_data) / n
    std_dev = (sum([(x - mean)**2 for x in sample_data]) / (n-1))**0.5 if n > 1 else 0
    se = std_dev / (n**0.5)  # Standard error
    margin_error = 1.96 * se  # 95% CI
    
    print(f"Example: {n} simulation runs")
    print(f"Sample values: {sample_data}")
    print(f"Mean: {mean:.4f}")
    print(f"Standard error: {se:.4f}")
    print(f"95% Confidence Interval: {mean:.4f} ± {margin_error:.4f}")
    print(f"Range: [{mean-margin_error:.4f}, {mean+margin_error:.4f}]")

def create_automation_script():
    """Create a shell script to automate simulation and analysis"""
    script_content = '''#!/bin/bash
# Automated script for running TCP variant simulations and analysis

echo "Starting TCP variant simulations..."

# Run NS simulations for all TCP variants
echo "Running Reno simulation..."
ns renoCode.tcl

echo "Running Cubic simulation..."
ns cubicCode.tcl

echo "Running Yeah simulation..."
ns yeahCode.tcl

echo "Running Vegas simulation..."
ns vegasCode.tcl

echo "Simulations complete. Running analysis..."

# Run the Python analyzer
python analyser3.py

echo "Analysis complete."
'''
    
    with open('run_analysis.sh', 'w') as f:
        f.write(script_content)
    
    print("\nCreated automation script: run_analysis.sh")
    print("To use: chmod +x run_analysis.sh && ./run_analysis.sh")

def main():
    """Main function to run the analysis"""
    print("Starting TCP Variants Analysis")
    print("This script analyzes different TCP congestion control algorithms")
    print("including Reno, Cubic, Yeah, and Vegas")
    
    # Part A: Basic TCP variant comparison
    goodputs, plrs, fairness_indices, stabilities = analyze_tcp_variants()
    
    # Part B: Queue management analysis (placeholder)
    part_b_analysis()
    
    # Part C: Repeatability and confidence intervals (placeholder)
    part_c_analysis()
    
    # Create automation script
    create_automation_script()
    
    print("\nAnalysis complete!")
    print("\nSummary of findings:")
    print(f"- Best goodput: {max(goodputs.keys(), key=lambda k: sum(goodputs[k]))}")
    print(f"- Best fairness: {max(fairness_indices.keys(), key=lambda k: fairness_indices[k])}")
    print(f"- Best stability: {min(stabilities.keys(), key=lambda k: stabilities[k])}")
    print(f"- Lowest PLR: {min(plrs.keys(), key=lambda k: plrs[k])}")

if __name__ == "__main__":
    main()