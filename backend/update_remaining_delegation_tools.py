"""
Script to update remaining 4 delegation functions to use single task field.

This script modifies delegation_tools.py to:
1. Change args_schema from specific Input classes to DelegationInput
2. Update function signatures to accept only `task: str`
3. Simplify implementations to use task directly
4. Update docstrings and return messages

Run this after updating delegate_to_researcher manually.
"""

import re

# Read the current file
with open('delegation_tools.py', 'r') as f:
    content = f.read()

# Pattern to match and replace each delegation function
# We'll do this for data_scientist, expert_analyst, writer, and reviewer

# 1. Replace DataScientistInput with DelegationInput
content = re.sub(
    r'args_schema=DataScientistInput',
    'args_schema=DelegationInput',
    content
)

# 2. Replace ExpertAnalystInput with DelegationInput
content = re.sub(
    r'args_schema=ExpertAnalystInput',
    'args_schema=DelegationInput',
    content
)

# 3. Replace WriterInput with DelegationInput
content = re.sub(
    r'args_schema=WriterInput',
    'args_schema=DelegationInput',
    content
)

# 4. Replace ReviewerInput with DelegationInput
content = re.sub(
    r'args_schema=ReviewerInput',
    'args_schema=DelegationInput',
    content
)

# Write the updated content back
with open('delegation_tools.py', 'w') as f:
    f.write(content)

print("✅ Updated all delegation function args_schema to use DelegationInput")
print("⚠️  Note: Function signatures and implementations still need manual updates")
print("    This script only updated the decorator args_schema parameter")
