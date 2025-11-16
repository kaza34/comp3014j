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
        if line[0] == 'r' and line[4] == 'tcp':
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
        if line[0] == 'r' and line[4] == 'tcp':
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
        if line[0] == '+' and line[4] == 'tcp':  # Packet sent
            total_sent += 1
        elif line[0] == 'd' and line[4] == 'tcp':  # Packet dropped
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

def extract_flow_data(trace_lines, flow_id, total_time=1000, time_window=1.0):
    """Extract data specifically for a given flow with configurable time window"""
    # Calculate number of time windows
    num_windows = int(total_time / time_window) + 1
    received_bytes = [0] * num_windows  # Bytes received per time window

    for line in trace_lines:
        if len(line) < 8:  # Need at least 8 elements to access flow_id at index 7
            continue

        event_type = line[0]  # +, -, r, d
        time = float(line[1])
        packet_type = line[4]  # tcp, ack, etc.
        packet_size = int(line[5])  # Size in bytes
        trace_flow_id = line[7]  # Flow ID is in index 7

        if event_type == 'r' and packet_type == 'tcp' and trace_flow_id == str(flow_id):
            # Received TCP packet for the specific flow
            window_index = int(time / time_window)
            if 0 <= window_index < num_windows:
                received_bytes[window_index] += packet_size

    # Convert bytes to Mbps per time window
    time_window_seconds = time_window
    goodput_mbps = [bytes_window * 8 / (1e6 * time_window_seconds) for bytes_window in received_bytes]
    return goodput_mbps

def analyze_tcp_variants():
    """Main analysis function for Part A: Compare TCP variants"""

    # TCP variants to analyze
    tcp_variants = ['reno', 'cubic', 'yeah', 'vegas']

    # Correct trace file naming - check which naming convention is used
    trace_files = {}
    for variant in tcp_variants:
        # Check if trace files exist with "Trace.tr" or "Code.tr" naming
        trace_filename = f"{variant}Trace.tr"
        # If the file doesn't exist, try alternative naming
        if not os.path.exists(trace_filename):
            trace_filename = f"{variant}Code.tr"
        trace_files[variant] = trace_filename

    # Data structures to store results
    goodputs = {}
    plrs = {}  # Packet Loss Rates
    final_third_goodputs = {}  # For fairness analysis

    print("Analyzing TCP Variants Performance...")
    print("="*50)

    # Analyze each TCP variant
    for variant in tcp_variants:
        if not os.path.exists(trace_files[variant]):
            print(f"Warning: Trace file {trace_files[variant]} not found for {variant}")
            continue

        trace_lines = splitFile(trace_files[variant])

        # Calculate goodput for flows 1 and 2 (using flow IDs instead of destination nodes)
        # Using a 0.1 second time window for better precision
        goodput_flow1 = extract_flow_data(trace_lines, 1, time_window=0.1)
        goodput_flow2 = extract_flow_data(trace_lines, 2, time_window=0.1)

        # Total goodput is sum of both flows
        total_goodput = [g1 + g2 for g1, g2 in zip(goodput_flow1, goodput_flow2)]

        goodputs[variant] = total_goodput
        plrs[variant] = calculate_packet_loss_rate(trace_lines)

        # Extract final third data for fairness analysis
        third_point = len(total_goodput) // 3 * 2  # Start of last third
        final_third_data = total_goodput[third_point:]

        # Calculate per-flow goodput for fairness
        final_third_flow1 = goodput_flow1[third_point:]
        final_third_flow2 = goodput_flow2[third_point:]

        # Average goodput for each flow in the final third
        avg_flow1 = sum(final_third_flow1) / len(final_third_flow1) if len(final_third_flow1) > 0 else 0
        avg_flow2 = sum(final_third_flow2) / len(final_third_flow2) if len(final_third_flow2) > 0 else 0

        final_third_goodputs[variant] = [avg_flow1, avg_flow2]

        print(f"\n{variant.upper()} Results:")
        print(f"  Total Goodput (Mbps): {sum(total_goodput):.4f}")
        print(f"  Average Goodput (Mbps): {sum(total_goodput)/len(total_goodput):.4f}")
        print(f"  Packet Loss Rate (%): {plrs[variant]:.4f}")
        print(f"  Final Third Average Goodput - Flow 1: {avg_flow1:.4f} Mbps")
        print(f"  Final Third Average Goodput - Flow 2: {avg_flow2:.4f} Mbps")

    # Only process variants that had trace files found
    available_variants = [v for v in tcp_variants if v in goodputs]

    # Task 1: Create table of goodput and PLR
    print("\n" + "="*50)
    print("TASK 1: Total Goodput and Packet Loss Rate Table")
    print("="*50)
    print(f"{'TCP Variant':<10} {'Total Goodput (Mbps)':<20} {'Avg Goodput (Mbps)':<20} {'PLR (%)':<10}")
    print("-" * 70)
    for variant in available_variants:
        total_goodput = sum(goodputs[variant])
        avg_goodput = total_goodput / len(goodputs[variant])
        plr = plrs[variant]
        print(f"{variant:<10} {total_goodput:<20.4f} {avg_goodput:<20.4f} {plr:<10.4f}")

    # Task 2: Jain Fairness Index for the last third
    print("\n" + "="*50)
    print("TASK 2: Jain Fairness Index (Last Third)")
    print("="*50)
    fairness_indices = {}
    for variant in available_variants:
        values = final_third_goodputs[variant]
        jain_index = calculate_jain_fairness_index(values)
        fairness_indices[variant] = jain_index
        print(f"{variant.upper()}: {jain_index:.4f}")

    # Task 3: Stability analysis (Coefficient of Variation)
    print("\n" + "="*50)
    print("TASK 3: Throughput Stability (Coefficient of Variation)")
    print("="*50)
    stabilities = {}
    for variant in available_variants:
        cov = calculate_coefficient_of_variation(goodputs[variant])
        stabilities[variant] = cov
        print(f"{variant.upper()}: {cov:.4f}")

    # Task 4: Overall summary
    print("\n" + "="*50)
    print("TASK 4: Overall Algorithm Performance Summary")
    print("="*50)

    if available_variants:
        # Find best algorithm based on multiple metrics
        best_goodput = max(available_variants, key=lambda k: sum(goodputs[k]))
        best_fairness = max(available_variants, key=lambda k: fairness_indices[k])
        best_stability = min(available_variants, key=lambda k: stabilities[k])
        lowest_plr = min(available_variants, key=lambda k: plrs[k])

        print(f"Best Total Goodput: {best_goodput.upper()}")
        print(f"Best Fairness: {best_fairness.upper()}")
        print(f"Best Stability: {best_stability.upper()}")
        print(f"Lowest Packet Loss Rate: {lowest_plr.upper()}")

        # Visualization
        plot_results({k: goodputs[k] for k in available_variants},
                   {k: plrs[k] for k in available_variants},
                   {k: fairness_indices[k] for k in available_variants},
                   {k: stabilities[k] for k in available_variants})

    return goodputs, plrs, fairness_indices, stabilities

def plot_results(goodputs, plrs, fairness_indices, stabilities):
    """Plot comparison charts for goodput and PLR"""
    tcp_variants = list(goodputs.keys())

    # Plot 1: Goodput over time - Increase figure size and adjust spacing
    plt.figure(figsize=(16, 12))

    plt.subplot(2, 2, 1)
    for variant in tcp_variants:
        cumulative_goodput = np.cumsum(goodputs[variant])
        plt.plot(cumulative_goodput[:500], label=f'{variant.upper()}', linewidth=1.5)  # Limit to first 500 seconds to see trend
    plt.title('Cumulative Goodput Over Time', fontsize=12)
    plt.xlabel('Time (seconds)', fontsize=10)
    plt.ylabel('Cumulative Goodput (Mbps)', fontsize=10)
    plt.legend(fontsize=9)
    plt.grid(True, alpha=0.3)
    plt.xticks(fontsize=9)
    plt.yticks(fontsize=9)

    # Plot 2: Average Goodput per variant
    plt.subplot(2, 2, 2)
    avg_goodputs = [sum(goodputs[v])/len(goodputs[v]) for v in tcp_variants]
    bars = plt.bar(tcp_variants, avg_goodputs, color=['blue', 'green', 'red', 'purple'])
    plt.title('Average Goodput by TCP Variant', fontsize=12)
    plt.xlabel('TCP Variant', fontsize=10)
    plt.ylabel('Average Goodput (Mbps)', fontsize=10)
    plt.grid(True, alpha=0.3, axis='y')
    plt.xticks(rotation=15, fontsize=9)  # Rotate x-axis labels to prevent overlap
    plt.yticks(fontsize=9)

    # Add value labels on bars
    for bar, value in zip(bars, avg_goodputs):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(avg_goodputs)*0.01,
                 f'{value:.3f}', ha='center', va='bottom', fontsize=8)

    # Plot 3: Packet Loss Rate
    plt.subplot(2, 2, 3)
    plr_values = [plrs[v] for v in tcp_variants]
    bars = plt.bar(tcp_variants, plr_values, color=['blue', 'green', 'red', 'purple'])
    plt.title('Packet Loss Rate by TCP Variant', fontsize=12)
    plt.xlabel('TCP Variant', fontsize=10)
    plt.ylabel('Packet Loss Rate (%)', fontsize=10)
    plt.grid(True, alpha=0.3, axis='y')
    plt.xticks(rotation=15, fontsize=9)  # Rotate x-axis labels to prevent overlap
    plt.yticks(fontsize=9)

    # Add value labels on bars
    for bar, value in zip(bars, plr_values):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(plr_values)*0.01,
                 f'{value:.3f}%', ha='center', va='bottom', fontsize=8)

    # Plot 4: Jain Fairness Index
    plt.subplot(2, 2, 4)
    fairness_values = [fairness_indices[v] for v in tcp_variants]
    bars = plt.bar(tcp_variants, fairness_values, color=['blue', 'green', 'red', 'purple'])
    plt.title('Jain Fairness Index (Last Third)', fontsize=12)
    plt.xlabel('TCP Variant', fontsize=10)
    plt.ylabel('Fairness Index', fontsize=10)
    plt.ylim(0, 1.1)
    plt.grid(True, alpha=0.3, axis='y')
    plt.xticks(rotation=15, fontsize=9)  # Rotate x-axis labels to prevent overlap
    plt.yticks(fontsize=9)

    # Add value labels on bars
    for bar, value in zip(bars, fairness_values):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(fairness_values)*0.01,
                 f'{value:.3f}', ha='center', va='bottom', fontsize=8)

    # Adjust spacing between subplots to prevent overlap
    plt.subplots_adjust(hspace=0.4, wspace=0.3)
    plt.tight_layout()
    plt.show()

    # Additional plot: Stability (Coefficient of Variation)
    plt.figure(figsize=(12, 7))
    stability_values = [stabilities[v] for v in tcp_variants]
    bars = plt.bar(tcp_variants, stability_values, color=['blue', 'green', 'red', 'purple'])
    plt.title('Throughput Stability (Coefficient of Variation)', fontsize=12)
    plt.xlabel('TCP Variant', fontsize=10)
    plt.ylabel('Coefficient of Variation (Lower is More Stable)', fontsize=10)
    plt.grid(True, alpha=0.3, axis='y')
    plt.xticks(rotation=15, fontsize=9)  # Rotate x-axis labels to prevent overlap
    plt.yticks(fontsize=9)

    # Add value labels on bars
    for bar, value in zip(bars, stability_values):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(stability_values)*0.01,
                 f'{value:.3f}', ha='center', va='bottom', fontsize=8)

    plt.tight_layout()
    plt.show()

def part_b_analysis():
    """Analysis for Part B: DropTail vs RED queue management"""
    print("\n" + "="*60)
    print("PART B ANALYSIS: DropTail vs RED QUEUE MANAGEMENT")
    print("="*60)

    # Define queue management algorithms and TCP variants to analyze
    queue_algorithms = ['DropTail', 'RED']
    tcp_variants = ['reno', 'cubic', 'yeah', 'vegas']

    # Result structure: [algorithm][variant] = {metric: value}
    results = {}

    print("Comparing DropTail vs RED queue management algorithms...")

    # For each algorithm, we would need trace files with different queue management
    # This would require running simulations with modified TCL files
    for algorithm in queue_algorithms:
        results[algorithm] = {}
        for variant in tcp_variants:
            # Look for trace files with the specific queue algorithm
            # For example: renoDropTail.tr, renoRED.tr, etc.
            trace_filename = f"{variant}{algorithm}.tr"
            if os.path.exists(trace_filename):
                trace_lines = splitFile(trace_filename)

                # Calculate goodput for flows 1 and 2 (using flow IDs instead of destination nodes)
                goodput_flow1 = extract_flow_data(trace_lines, 1, time_window=0.1)
                goodput_flow2 = extract_flow_data(trace_lines, 2, time_window=0.1)

                # Total goodput is sum of both flows
                total_goodput = [g1 + g2 for g1, g2 in zip(goodput_flow1, goodput_flow2)]

                # Calculate metrics
                avg_goodput = sum(total_goodput) / len(total_goodput) if len(total_goodput) > 0 else 0
                plr = calculate_packet_loss_rate(trace_lines)

                # Calculate fairness in the last third
                third_point = len(total_goodput) // 3 * 2
                final_third_flow1 = goodput_flow1[third_point:]
                final_third_flow2 = goodput_flow2[third_point:]
                avg_flow1 = sum(final_third_flow1) / len(final_third_flow1) if len(final_third_flow1) > 0 else 0
                avg_flow2 = sum(final_third_flow2) / len(final_third_flow2) if len(final_third_flow2) > 0 else 0
                fairness_values = [avg_flow1, avg_flow2]
                jain_index = calculate_jain_fairness_index(fairness_values)

                # Calculate stability (CoV)
                stability = calculate_coefficient_of_variation(total_goodput)

                results[algorithm][variant] = {
                    'goodput': avg_goodput,
                    'plr': plr,
                    'fairness': jain_index,
                    'stability': stability
                }
            else:
                # If specific file doesn't exist, note that we would need it
                print(f"Trace file {trace_filename} not found. This would be needed for {algorithm} analysis.")
                results[algorithm][variant] = {
                    'goodput': None,
                    'plr': None,
                    'fairness': None,
                    'stability': None
                }

    # Compare algorithms if we have data
    if results[queue_algorithms[0]] and results[queue_algorithms[1]]:
        print(f"\n{'Metric':<12} {'Algorithm':<10} {'Reno':<10} {'Cubic':<10} {'Yeah':<10} {'Vegas':<10}")
        print("-" * 70)

        metrics = ['goodput', 'plr', 'fairness', 'stability']
        metric_names = ['Goodput', 'PLR (%)', 'Fairness', 'Stability']

        for i, metric in enumerate(metrics):
            print(f"{metric_names[i]:<12}")
            for algorithm in queue_algorithms:
                values = []
                for variant in tcp_variants:
                    val = results[algorithm][variant][metric]
                    values.append(f"{val:.3f}" if val is not None else "N/A")
                print(f"{'':<12} {algorithm:<10} {values[0]:<10} {values[1]:<10} {values[2]:<10} {values[3]:<10}")

    print("\nTo properly complete Part B:")
    print("1. Modify your .tcl files to use either DropTail or RED queue management")
    print("2. Run separate simulations for each algorithm")
    print("3. Name the trace files appropriately (e.g., renoDropTail.tr, renoRED.tr)")
    print("4. Run this analysis again with the new trace files")

    # Sensitivity analysis placeholder
    print("\nSENSITIVITY ANALYSIS (Task 2):")
    print("Congestion level affects queue algorithm choice as follows:")
    print("- DropTail: Simpler but can cause global synchronization")
    print("- RED: Better for high congestion, prevents global sync but adds complexity")

def calculate_confidence_interval(data, confidence=0.95):
    """Calculate confidence interval for a dataset"""
    import math

    n = len(data)
    if n <= 1:
        return sum(data) if data else 0, 0, (0, 0)

    mean = sum(data) / n

    # Calculate sample standard deviation
    variance = sum((x - mean) ** 2 for x in data) / (n - 1)
    std_dev = math.sqrt(variance)

    # Z-score for confidence level: 1.96 for 95%, 2.576 for 99%
    if confidence == 0.95:
        z_score = 1.96
    elif confidence == 0.99:
        z_score = 2.576
    else:
        z_score = 1.96  # Default to 95%

    # Calculate margin of error
    se = std_dev / math.sqrt(n)  # Standard error
    margin_error = z_score * se

    # Confidence interval
    ci_lower = mean - margin_error
    ci_upper = mean + margin_error

    return mean, margin_error, (ci_lower, ci_upper)

def run_repeatability_analysis():
    """Run 5 simulations with different seeds and calculate confidence intervals"""
    print("\n" + "="*60)
    print("PART C ANALYSIS: Repeatability and Confidence Intervals")
    print("="*60)

    tcp_variants = ['reno', 'cubic', 'yeah', 'vegas']

    # This would require running simulations with different random seeds
    # In practice, you'd run the same simulation with 5 different random seeds
    # Here's how you would structure it:

    print("For proper repeatability analysis, you would need to:")
    print("1. Run 5 simulations of each TCP variant with different random seeds")
    print("2. Extract the metric of interest (e.g., average goodput) from each run")
    print("3. Calculate confidence intervals using the results")

    # Example implementation with simulated data
    print("\nExample confidence interval calculation (using simulated data):")

    # Simulate results from 5 runs of Cubic algorithm
    # Each run would give us an average goodput value
    cubic_goodputs = [1.82, 1.79, 1.85, 1.81, 1.83]  # Example values from 5 runs
    reno_goodputs = [1.65, 1.68, 1.62, 1.69, 1.66]   # Example values from 5 runs
    vegas_goodputs = [1.72, 1.70, 1.75, 1.73, 1.71]  # Example values from 5 runs
    yeah_goodputs = [1.78, 1.76, 1.80, 1.77, 1.79]   # Example values from 5 runs

    algorithms = {
        'Cubic': cubic_goodputs,
        'Reno': reno_goodputs,
        'Vegas': vegas_goodputs,
        'Yeah': yeah_goodputs
    }

    print(f"\n{'Algorithm':<10} {'Mean':<10} {'Std Dev':<12} {'CI Lower':<12} {'CI Upper':<12} {'Range':<10}")
    print("-" * 70)

    for algorithm, data in algorithms.items():
        mean, margin_error, (ci_lower, ci_upper) = calculate_confidence_interval(data)
        std_dev = (sum((x - mean) ** 2 for x in data) / (len(data) - 1))**0.5 if len(data) > 1 else 0

        print(f"{algorithm:<10} {mean:.4f}     {std_dev:.4f}      {ci_lower:.4f}      {ci_upper:.4f}      ±{margin_error:.4f}")

    print(f"\nActual implementation requires:")
    print(f"1. Modify the .tcl files to use different random seeds")
    print(f"2. Run each TCP variant simulation 5 times with different seeds")
    print(f"3. Name the output files as variant_seed.tr (e.g., cubic_1.tr, cubic_2.tr, etc.)")
    print(f"4. Extract the same metric from each run")
    print(f"5. Apply confidence interval calculation to the results")

    return algorithms

def part_c_analysis():
    """Analysis for Part C: Repeatability with confidence intervals"""
    run_repeatability_analysis()

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
    print("\n" + "="*70)
    print("PART A: TCP VARIANTS COMPARISON (Fixed Topology)")
    print("="*70)
    goodputs, plrs, fairness_indices, stabilities = analyze_tcp_variants()

    # Part B: Queue management analysis
    print("\n" + "="*70)
    print("PART B: DropTail vs RED QUEUE MANAGEMENT")
    print("="*70)
    part_b_analysis()

    # Part C: Repeatability and confidence intervals
    print("\n" + "="*70)
    print("PART C: REPEATABILITY WITH CONFIDENCE INTERVALS")
    print("="*70)
    part_c_analysis()

    # Create automation script
    create_automation_script()

    print("\n" + "="*70)
    print("ANALYSIS COMPLETE!")
    print("="*70)

    # Final summary
    if goodputs:  # Only print summary if Part A ran successfully
        available_variants = [k for k in goodputs.keys() if k in fairness_indices and k in stabilities]
        if available_variants:
            print("\nSummary of findings:")
            try:
                print(f"- Best Total Goodput: {max(available_variants, key=lambda k: sum(goodputs[k])).upper()}")
            except:
                pass
            try:
                print(f"- Best Fairness: {max(available_variants, key=lambda k: fairness_indices[k]).upper()}")
            except:
                pass
            try:
                print(f"- Best Stability: {min(available_variants, key=lambda k: stabilities[k]).upper()}")
            except:
                pass
            try:
                print(f"- Lowest PLR: {min(available_variants, key=lambda k: plrs[k]).upper()}")
            except:
                pass

if __name__ == "__main__":
    main()