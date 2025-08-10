#!/usr/bin/env python3
"""
Utility script to toggle between old and new recap sanitizer versions.
"""

import json
import sys
from pathlib import Path

def update_config(use_improved: bool, use_multi_stage: bool = False):
    """Update the configuration to use the specified sanitizer version."""
    config_file = "config.md"
    
    if not Path(config_file).exists():
        print(f"Error: {config_file} not found!")
        return
    
    print(f"Updating {config_file}...")
    
    # Read the current config
    with open(config_file, 'r') as f:
        content = f.read()
    
    # Find the YAML frontmatter section
    import re
    pattern = r'^---\s*\n(.*?)\n---\s*\n'
    match = re.search(pattern, content, re.DOTALL)
    
    if not match:
        print(f"Error: No YAML frontmatter found in {config_file}")
        return
    
    yaml_content = match.group(1)
    
    # Update both settings
    settings_to_update = {
        'use_improved_recap_sanitizer': use_improved,
        'use_multi_stage_recap_sanitizer': use_multi_stage
    }
    
    for setting_name, setting_value in settings_to_update.items():
        if f"{setting_name}:" in yaml_content:
            # Update existing setting
            yaml_content = re.sub(
                rf'{setting_name}:\s*(true|false)',
                f'{setting_name}: {str(setting_value).lower()}',
                yaml_content
            )
        else:
            # Add the setting to the generation section
            generation_pattern = r'(generation:\s*\n(?:  .*\n)*)'
            generation_match = re.search(generation_pattern, yaml_content)
            
            if generation_match:
                generation_section = generation_match.group(1)
                # Add the setting at the end of the generation section
                new_generation_section = generation_section.rstrip() + f'\n  {setting_name}: {str(setting_value).lower()}\n'
                yaml_content = yaml_content.replace(generation_section, new_generation_section)
            else:
                print(f"Error: Could not find generation section in YAML")
                return
    
    # Replace the YAML content in the original file
    new_content = content.replace(match.group(0), f"---\n{yaml_content}\n---\n\n")
    
    # Write back the config
    with open(config_file, 'w') as f:
        f.write(new_content)
    
    print(f"✓ Updated {config_file}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python toggle_recap_sanitizer.py [old|new|multi|status]")
        print("  old    - Use the original recap sanitizer")
        print("  new    - Use the improved single-stage recap sanitizer")
        print("  multi  - Use the multi-stage recap sanitizer pipeline")
        print("  status - Show current status")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "new":
        print("Switching to improved single-stage recap sanitizer...")
        update_config(True, False)
        print("\n✓ Switched to improved single-stage recap sanitizer")
        print("  - Uses simplified 3-section format")
        print("  - Includes clear examples and rules")
        print("  - Better date handling and deduplication")
        
    elif command == "multi":
        print("Switching to multi-stage recap sanitizer...")
        update_config(True, True)
        print("\n✓ Switched to multi-stage recap sanitizer")
        print("  - Uses 3-stage pipeline (extract → compact → format)")
        print("  - Better error handling and debugging")
        print("  - More reliable progressive compaction")
        print("  - Fallback to single-stage if needed")
        
    elif command == "old":
        print("Switching to original recap sanitizer...")
        update_config(False, False)
        print("\n✓ Switched to original recap sanitizer")
        print("  - Uses 5-section time-based format")
        print("  - Original complex template structure")
        
    elif command == "status":
        print("Checking current sanitizer configuration...")
        config_file = "config.md"
        if Path(config_file).exists():
            with open(config_file, 'r') as f:
                content = f.read()
            
            if "use_multi_stage_recap_sanitizer: true" in content:
                print("✓ Currently using MULTI-STAGE recap sanitizer")
                print("  - 3-stage pipeline with better error handling")
            elif "use_improved_recap_sanitizer: true" in content:
                print("✓ Currently using IMPROVED SINGLE-STAGE recap sanitizer")
                print("  - Simplified 3-section format with examples")
            elif "use_improved_recap_sanitizer: false" in content:
                print("✓ Currently using ORIGINAL recap sanitizer")
                print("  - 5-section time-based format")
            else:
                print("? Configuration not found, defaulting to ORIGINAL")
        else:
            print("? Config file not found")
            
    else:
        print(f"Unknown command: {command}")
        print("Use 'old', 'new', or 'status'")
        sys.exit(1)

if __name__ == "__main__":
    main() 