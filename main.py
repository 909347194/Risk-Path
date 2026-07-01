"""
Risk-Path: Unified Entry Point for UAV Path Planning Systems

This script provides a unified interface to access both:
1. EDA-CostA* Path Planning System
2. Air Corridor Design System
"""

import sys
from pathlib import Path

# Add src directories to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))


def run_eda_astar_experiment(experiment_num: int = 1):
    """Run EDA-CostA* experiments"""
    print(f"\n{'='*60}")
    print(f"Running EDA-CostA* Experiment {experiment_num}")
    print(f"{'='*60}\n")
    
    experiment_map = {
        1: "experiments/experiment_01_standard_astar.py",
        2: "experiments/experiment_02_original_eda.py",
        3: "experiments/experiment_03_two_stage_eda.py",
        4: "experiments/experiment_04_comparison.py",
    }
    
    if experiment_num not in experiment_map:
        print(f"Error: Invalid experiment number {experiment_num}")
        print(f"Available experiments: {list(experiment_map.keys())}")
        return
    
    experiment_file = src_path / "eda_astar" / experiment_map[experiment_num]
    
    if not experiment_file.exists():
        print(f"Error: Experiment file not found: {experiment_file}")
        return
    
    # Execute the experiment
    import subprocess
    subprocess.run([sys.executable, str(experiment_file)])


def run_air_corridor(task: str = "main"):
    """Run Air Corridor Design tasks"""
    print(f"\n{'='*60}")
    print(f"Running Air Corridor Design: {task}")
    print(f"{'='*60}\n")
    
    task_map = {
        "main": "main.py",
        "performance": "main_algorithm_performance.py",
        "preparemap": "main_preparemap.py",
        "sensitivity_risk": "main_sensitivity_riskweight.py",
        "sensitivity_tradeoff": "main_sensitivity_tradeoffweight.py",
    }
    
    if task not in task_map:
        print(f"Error: Invalid task '{task}'")
        print(f"Available tasks: {list(task_map.keys())}")
        return
    
    task_file = src_path / "air_corridor" / task_map[task]
    
    if not task_file.exists():
        print(f"Error: Task file not found: {task_file}")
        return
    
    # Execute the task
    import subprocess
    subprocess.run([sys.executable, str(task_file)])


def show_menu():
    """Display interactive menu"""
    print("\n" + "="*60)
    print("Risk-Path: UAV Path Planning System")
    print("="*60)
    print("\nSelect a system to run:")
    print("\n[1] EDA-CostA* Path Planning")
    print("    [1.1] Experiment 1: Standard Cost A*")
    print("    [1.2] Experiment 2: Original EDA-A*")
    print("    [1.3] Experiment 3: Two-Stage EDA-CostA*")
    print("    [1.4] Experiment 4: Algorithm Comparison")
    print("\n[2] Air Corridor Design")
    print("    [2.1] Main Procedure")
    print("    [2.2] Algorithm Performance")
    print("    [2.3] Map Preparation")
    print("    [2.4] Sensitivity Analysis (Risk Weight)")
    print("    [2.5] Sensitivity Analysis (Trade-off Weight)")
    print("\n[0] Exit")
    print("="*60)


def main():
    """Main entry point with interactive menu"""
    while True:
        show_menu()
        choice = input("\nEnter your choice: ").strip()
        
        if choice == "0":
            print("\nGoodbye!")
            break
        elif choice.startswith("1."):
            try:
                exp_num = int(choice.split(".")[1])
                run_eda_astar_experiment(exp_num)
            except (ValueError, IndexError):
                print("Invalid experiment number")
        elif choice.startswith("2."):
            try:
                task_num = int(choice.split(".")[1])
                task_map = {
                    1: "main",
                    2: "performance",
                    3: "preparemap",
                    4: "sensitivity_risk",
                    5: "sensitivity_tradeoff",
                }
                if task_num in task_map:
                    run_air_corridor(task_map[task_num])
                else:
                    print("Invalid task number")
            except (ValueError, IndexError):
                print("Invalid task number")
        else:
            print("Invalid choice. Please try again.")
        
        input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()
