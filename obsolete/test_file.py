print("Understanding List Order Preservation in Python")
print("=" * 50)

# Your original definition
id_groups = {
    'group1': [0x123, 0x124, 0x125],  # This is a LIST - order matters!
}

print("1. Original list definition:")
print(f"   id_groups['group1'] = {[hex(x) for x in id_groups['group1']]}")

print("\n2. What happens when we do:")
print("   ordered_ids = self.id_groups[group_name]")

ordered_ids = id_groups['group1']
print(f"   ordered_ids = {[hex(x) for x in ordered_ids]}")

print("\n3. The 'for can_id in ordered_ids' loop:")
print("   This traverses the list in INDEX ORDER (0, 1, 2, ...)")

for i, can_id in enumerate(ordered_ids):
    print(f"   Loop iteration {i}: can_id = {hex(can_id)}")

print("\n" + "=" * 50)
print("Comparison with different data structures:")

# If you used a SET instead (no order guarantee)
id_groups_set = {
    'group1': {0x123, 0x124, 0x125}  # SET - no guaranteed order!
}

print(f"\nWith a SET: {[hex(x) for x in id_groups_set['group1']]}")
print("Order could be: [0x124, 0x123, 0x125] or any other combination!")

# If you used a DICT (Python 3.7+ preserves insertion order)
id_groups_dict = {
    'group1': {0x123: 'first', 0x124: 'second', 0x125: 'third'}
}

print(f"\nWith a DICT: {[hex(x) for x in id_groups_dict['group1']]}")
print("Order preserved since Python 3.7+")

print("\n" + "=" * 50)
print("Why the LIST approach works:")
print("1. Lists in Python are ordered sequences")
print("2. They maintain insertion order ALWAYS")
print("3. for..in iterates through indices 0, 1, 2, ... in sequence")
print("4. So [0x123, 0x124, 0x125] ALWAYS processes as 0x123 → 0x124 → 0x125")

print("\n" + "=" * 50)
print("Demonstration with scrambled message arrival:")

# Simulate messages arriving out of order
message_buffer = {}
scrambled_arrivals = [
    (0x125, "data_from_125"),  # Third ID arrives first
    (0x123, "data_from_123"),  # First ID arrives second  
    (0x124, "data_from_124"),  # Second ID arrives third
]

print("\nMessages arrive in this order:")
for can_id, data in scrambled_arrivals:
    message_buffer[can_id] = data
    print(f"  Received: {hex(can_id)} -> {data}")

print(f"\nBuffer contents: {[(hex(k), v) for k, v in message_buffer.items()]}")

print("\nBut when we process using the ordered list:")
ordered_ids = [0x123, 0x124, 0x125]  # Your defined order
for can_id in ordered_ids:
    data = message_buffer[can_id]
    print(f"  Processing: {hex(can_id)} -> {data}")

print("\nResult: Always processed in YOUR defined order, not arrival order!")