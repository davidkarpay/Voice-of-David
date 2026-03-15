# Read the current file
with open('finetune_verified.py', 'r') as f:
    lines = f.readlines()

# Find line 237 and insert eval_split_size before it
new_lines = []
for i, line in enumerate(lines):
    if 'eval_split_max_size=256,' in line:
        # Get indentation
        indent = ' ' * (len(line) - len(line.lstrip()))
        # Add eval_split_size BEFORE this line
        new_lines.append(indent + 'eval_split_size=0.1,  # 10% for evaluation = 4 samples\n')
    new_lines.append(line)

# Write back
with open('finetune_verified.py', 'w') as f:
    f.writelines(new_lines)

print('✅ Fixed! Added eval_split_size=0.1')
