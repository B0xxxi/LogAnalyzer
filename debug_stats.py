from src.main import load_config, parse_log, extract_target_steps, extract_warnings
from src.comparator import compare_logs

def debug_stats():
    config = load_config(None)
    old_log = "D7OrionPro_DevelopBuild_24782.log"
    new_log = "D7OrionPro_DevelopBuild_24787.log"
    
    print(f"Parsing {old_log}...")
    old_steps = parse_log(old_log, config)
    old_target_steps = extract_target_steps(old_steps, config)
    old_warnings = []
    for step in old_target_steps:
        old_warnings.extend(extract_warnings(step, config))
        
    print(f"Parsing {new_log}...")
    new_steps = parse_log(new_log, config)
    new_target_steps = extract_target_steps(new_steps, config)
    new_warnings = []
    for step in new_target_steps:
        new_warnings.extend(extract_warnings(step, config))
        
    print(f"Old warnings: {len(old_warnings)}")
    print(f"New warnings: {len(new_warnings)}")
    
    summary = compare_logs(old_warnings, new_warnings)
    
    print("\nSummary by stage:")
    for result in summary.by_stage:
        print(f"Stage: '{result.stage_name}'")
        print(f"  Added: {len(result.added)}")
        print(f"  Removed: {len(result.removed)}")
        print(f"  Unchanged: {result.unchanged_count}")
        
    print("\nTotal from Summary:")
    print(f"  Added: {summary.total_added}")
    print(f"  Removed: {summary.total_removed}")
    print(f"  Unchanged: {summary.total_unchanged}")

if __name__ == "__main__":
    debug_stats()
