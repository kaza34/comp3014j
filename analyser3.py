import matplotlib.pyplot as plt
import numpy as np
import os
import statistics
from math import sqrt

# --- Configuration: Define paths to data folders ---
PATH_PART_A = 'partA/'
PATH_PART_B = 'partB/'
PATH_PART_C = 'partC/'
TCP_VARIANTS = ['reno', 'cubic', 'yeah', 'vegas']

# --- Core Utility Functions ---

def splitFile(filename):
    """Read a trace file and split it into a list of lists."""
    try:
        with open(filename, 'r') as file:
            return [line.split() for line in file]
    except FileNotFoundError:
        print(f"Error: Trace file not found at {filename}")
        return None

def extract_goodput_per_flow(trace_lines, flow_id, duration=100.0, time_window=0.1):
    """Extracts goodput in Mbps for a specific flow over time windows."""
    num_windows = int(duration / time_window)
    received_bytes = [0] * num_windows
    for line in trace_lines:
        if len(line) < 8: continue
        event, time, _, _, pkt_type, pkt_size, _, fid = line[:8]
        if event == 'r' and pkt_type == 'tcp' and fid == str(flow_id):
            try:
                time, pkt_size = float(time), int(pkt_size)
                window_index = int(time / time_window)
                if window_index < num_windows:
                    received_bytes[window_index] += pkt_size
            except (ValueError, IndexError): continue
    return [(bytes_in_window * 8) / (time_window * 1_000_000) for bytes_in_window in received_bytes]

def calculate_metrics(trace_lines):
    """Analyzes a single trace file's lines and returns a dictionary of metrics."""
    # Packet Loss Rate
    sent_packets, dropped_packets = 0, 0
    for line in trace_lines:
        if len(line) < 5: continue
        event, pkt_type = line[0], line[4]
        if event == '+' and pkt_type == 'tcp': sent_packets += 1
        elif event == 'd' and pkt_type == 'tcp': dropped_packets += 1
    plr = (dropped_packets / sent_packets) * 100 if sent_packets > 0 else 0.0

    # Per-flow and Total Goodput
    goodput_flow1 = extract_goodput_per_flow(trace_lines, flow_id=1)
    goodput_flow2 = extract_goodput_per_flow(trace_lines, flow_id=2)
    total_goodput_ts = [g1 + g2 for g1, g2 in zip(goodput_flow1, goodput_flow2)]
    
    avg_goodput = np.mean(total_goodput_ts) if total_goodput_ts else 0.0
    
    # Stability (CoV)
    stability_cov = statistics.stdev(total_goodput_ts) / avg_goodput if avg_goodput > 0 and len(total_goodput_ts) > 1 else float('inf')

    # Fairness (Jain's Index) on the last third of the simulation
    last_third_idx = len(goodput_flow1) * 2 // 3
    avg_flow1_last_third = np.mean(goodput_flow1[last_third_idx:]) if len(goodput_flow1) > last_third_idx else 0.0
    avg_flow2_last_third = np.mean(goodput_flow2[last_third_idx:]) if len(goodput_flow2) > last_third_idx else 0.0
    
    sum_sq = (avg_flow1_last_third**2 + avg_flow2_last_third**2)
    jain_index = (avg_flow1_last_third + avg_flow2_last_third)**2 / (2 * sum_sq) if sum_sq > 0 else 0.0
    
    return {
        'goodput_ts': total_goodput_ts,
        'avg_goodput': avg_goodput,
        'plr': plr,
        'stability': stability_cov,
        'fairness': jain_index
    }

# --- Analysis Functions for Each Part ---

def part_a_analysis():
    """Analysis for Part A: Compare TCP variants with DropTail."""
    print("\n" + "="*70)
    print("PART A: TCP VARIANTS COMPARISON (Fixed Topology, DropTail)")
    print("="*70)
    
    results = {}
    for variant in TCP_VARIANTS:
        filename = os.path.join(PATH_PART_A, f"{variant}Trace.tr")
        lines = splitFile(filename)
        if lines:
            print(f"Analyzing {filename}...")
            results[variant] = calculate_metrics(lines)

    if not results:
        print("No trace files found for Part A analysis.")
        return None

    print("\n--- Part A: Summary Table ---")
    print(f"{'Variant':<10} | {'Avg Goodput (Mbps)':<20} | {'PLR (%)':<10} | {'Fairness':<10} | {'Stability (CoV)':<15}")
    print("-" * 75)
    for variant, data in results.items():
        print(f"{variant:<10} | {data['avg_goodput']:<20.4f} | {data['plr']:<10.4f} | {data['fairness']:<10.4f} | {data['stability']:<15.4f}")

    plot_results(results, "Part A: TCP Variants Performance (DropTail)", "part_a_summary.png")
    return results

def part_b_analysis():
    """Analysis for Part B: DropTail vs RED."""
    print("\n" + "="*70)
    print("PART B: DROPTAIL vs RED QUEUE MANAGEMENT")
    print("="*70)
    
    results = {'DropTail': {}, 'RED': {}}
    
    # Analyze DropTail results (from partA folder)
    for variant in TCP_VARIANTS:
        filename = os.path.join(PATH_PART_A, f"{variant}Trace.tr")
        lines = splitFile(filename)
        if lines: 
            print(f"Analyzing {filename} for DropTail...")
            results['DropTail'][variant] = calculate_metrics(lines)

    # Analyze RED results (from partB folder)
    for variant in TCP_VARIANTS:
        filename = os.path.join(PATH_PART_B, f"{variant}RED.tr")
        lines = splitFile(filename)
        if lines: 
            print(f"Analyzing {filename} for RED...")
            results['RED'][variant] = calculate_metrics(lines)

    if not results['DropTail'] or not results['RED']:
        print("Could not find all trace files for Part B comparison.")
        return

    print("\n--- Part B: Comparison Table ---")
    print(f"{'TCP Variant':<12} | {'Queue':<10} | {'Avg Goodput (Mbps)':<20} | {'PLR (%)':<10} | {'Fairness':<10} | {'Stability (CoV)':<15}")
    print("-" * 90)
    for queue_type, variant_data in results.items():
        for variant, data in variant_data.items():
            print(f"{variant:<12} | {queue_type:<10} | {data['avg_goodput']:<20.4f} | {data['plr']:<10.4f} | {data['fairness']:<10.4f} | {data['stability']:<15.4f}")
    
    # Call the new plotting function for Part B
    plot_results_part_b(results)

def plot_results_part_b(results):
    """Plots grouped bar charts for Part B comparison."""
    variants = TCP_VARIANTS
    metrics_to_plot = {
        'avg_goodput': 'Average Goodput (Mbps)',
        'plr': 'Packet Loss Rate (%)',
        'fairness': 'Jain Fairness Index',
        'stability': 'Stability (CoV, Lower is Better)'
    }
    
    # Create a 2x2 subplot figure
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Part B: DropTail vs RED Performance Comparison', fontsize=16)
    
    # Flatten axes array for easy iteration
    axes = axes.flatten()

    for i, (metric, title) in enumerate(metrics_to_plot.items()):
        ax = axes[i]
        
        droptail_values = [results['DropTail'][v][metric] for v in variants if v in results['DropTail']]
        red_values = [results['RED'][v][metric] for v in variants if v in results['RED']]
        
        x = np.arange(len(variants))  # the label locations
        width = 0.35  # the width of the bars

        rects1 = ax.bar(x - width/2, droptail_values, width, label='DropTail')
        rects2 = ax.bar(x + width/2, red_values, width, label='RED')

        # Add some text for labels, title and axes ticks
        ax.set_ylabel(title)
        ax.set_title(f'Comparison of {title}')
        ax.set_xticks(x)
        ax.set_xticklabels(variants)
        ax.legend()
        ax.grid(True, axis='y', linestyle='--', alpha=0.6)

        # Attach a text label above each bar, displaying its height.
        ax.bar_label(rects1, padding=3, fmt='%.3f')
        ax.bar_label(rects2, padding=3, fmt='%.3f')

    fig.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig('part_b_summary.png', dpi=300)
    print("\nSaved Part B summary plot to part_b_summary.png")
    plt.show()


def part_c_analysis():
    """Analysis for Part C: Light Reproducibility."""
    print("\n" + "="*70)
    print("PART C: LIGHT REPRODUCIBILITY ANALYSIS")
    print("="*70)
    
    scenario = 'cubic'
    num_runs = 5
    goodput_results = []

    for i in range(1, num_runs + 1):
        filename = os.path.join(PATH_PART_C, f"{scenario}_seed{i}.tr")
        lines = splitFile(filename)
        if lines:
            run_metrics = calculate_metrics(lines)
            goodput_results.append(run_metrics['avg_goodput'])
    
    if len(goodput_results) == num_runs:
        mean = statistics.mean(goodput_results)
        stdev = statistics.stdev(goodput_results)
        margin_of_error = 1.96 * (stdev / sqrt(num_runs))
        ci_lower, ci_upper = mean - margin_of_error, mean + margin_of_error
        
        print(f"Analysis for '{scenario.upper()}' based on {num_runs} runs:")
        print(f"  - Recorded Avg Goodputs: {[f'{x:.4f}' for x in goodput_results]}")
        print(f"  - Mean: {mean:.4f} Mbps")
        print(f"  - Standard Deviation: {stdev:.4f}")
        print(f"  - 95% Confidence Interval: [{ci_lower:.4f}, {ci_upper:.4f}] Mbps")
    else:
        print(f"Error: Could not find all {num_runs} trace files for scenario '{scenario}'.")

def create_automation_script():
    """Creates a shell script to automate the entire workflow."""
    print("\n" + "="*70)
    print("PACKAGING: Creating Automation Script")
    print("="*70)
    script_content = f"""#!/bin/bash
# This script automates the simulation and analysis process.

echo "--- This script requires all .tcl files to be in the root directory ---"
echo "--- Make sure your Part B and C tcl files are properly named and placed ---"

# Note: This is a template. The user should ensure the .tcl files exist.
# For a fully automated script, it would need to handle file creation/modification.

echo "--- Running all simulations ---"
# Part A
ns partA/renoTrace.tcl
# ... add other simulation runs here ...

echo "--- Running analysis script ---"
python3 {os.path.basename(__file__)}

echo "--- Workflow complete ---"
"""
    with open('run_all.sh', 'w') as f:
        f.write(script_content)
    os.chmod('run_all.sh', 0o755)
    print("Created executable script 'run_all.sh'. Note: You may need to edit it to match your TCL file names.")

def plot_results(results, suptitle, save_filename):
    """Generic plotting function."""
    variants = list(results.keys())
    if not variants: return
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle(suptitle, fontsize=16)

    # Plot 1: Cumulative Goodput
    ax = axes[0, 0]
    for variant, data in results.items():
        time_steps = np.arange(len(data['goodput_ts'])) * 0.1
        cumulative_goodput = np.cumsum(data['goodput_ts']) * 0.1
        ax.plot(time_steps, cumulative_goodput, label=variant.upper())
    ax.set_title('Cumulative Goodput Over Time')
    ax.set_xlabel('Time (seconds)')
    ax.set_ylabel('Total Data Transmitted (Mbits)')
    ax.legend()
    ax.grid(True, alpha=0.5)

    # Plot 2: Average Goodput
    ax = axes[0, 1]
    avg_goodputs = [d['avg_goodput'] for d in results.values()]
    bars = ax.bar(variants, avg_goodputs, color=['blue', 'green', 'red', 'purple'])
    ax.set_title('Average Goodput by TCP Variant')
    ax.set_ylabel('Average Goodput (Mbps)')
    for bar in bars:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2.0, yval, f'{yval:.3f}', va='bottom', ha='center')

    # Plot 3: Packet Loss Rate
    ax = axes[1, 0]
    plrs = [d['plr'] for d in results.values()]
    bars = ax.bar(variants, plrs, color=['blue', 'green', 'red', 'purple'])
    ax.set_title('Packet Loss Rate by TCP Variant')
    ax.set_ylabel('Packet Loss Rate (%)')
    for bar in bars:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2.0, yval, f'{yval:.3f}%', va='bottom', ha='center')

    # Plot 4: Jain Fairness Index
    ax = axes[1, 1]
    fairness_indices = [d['fairness'] for d in results.values()]
    bars = ax.bar(variants, fairness_indices, color=['blue', 'green', 'red', 'purple'])
    ax.set_title('Jain Fairness Index (Last Third)')
    ax.set_ylabel('Fairness Index')
    ax.set_ylim(0, 1.1)
    for bar in bars:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2.0, yval, f'{yval:.3f}', va='bottom', ha='center')

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(save_filename, dpi=300)
    print(f"\nSaved summary plot to {save_filename}")
    plt.show()

def main():
    """Main function to orchestrate the analysis for all parts."""
    part_a_results = part_a_analysis()
    part_b_analysis()
    part_c_analysis()
    create_automation_script()

if __name__ == "__main__":
    main()