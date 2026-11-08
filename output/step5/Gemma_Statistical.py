import pandas as pd
import numpy as np
from datetime import datetime

# 1. Identify the normative order and valid events
# Normative order: Register Claim (1) -> Verify Documents (2) -> Evaluate Claim (3) -> Approve Claim (4) -> Close Claim (5)
normative_order = {1: 'Register Claim', 2: 'Verify Documents', 3: 'Evaluate Claim', 4: 'Approve Claim', 5: 'Close Claim'}

# A timestamp is "valid" if it is not NaT, not incomplete (length check), and follows chronological order
# Incomplete check: '2026-09-13T16' has length 13. Standard ISO '2026-09-13T16:00:00' is longer.
def is_incomplete(ts_raw):
    if pd.isna(ts_raw): return True
    return len(str(ts_raw)) <= 13

# Initial identification of errors
events['is_incomplete'] = events['timestamp_raw'].apply(is_incomplete)
events['is_missing'] = events['timestamp'].isna()

# 2. Calculate median waiting times for each position transition
# We only use events that are not missing and not incomplete as the "ground truth" for statistics
valid_mask = (~events['is_missing']) & (~events['is_incomplete'])
valid_events = events[valid_mask].copy()

# Calculate waiting_min for valid events (it's already provided, but we ensure it's valid)
# We need the median waiting time for each position (e.g., median time between pos 1 and 2)
# Since waiting_min is "minutes since previous event", we group by position
median_waits = valid_events.groupby('position')['waiting_min'].median().to_dict()

# 3. Detect "out of order" errors
# An event is out of order if its timestamp <= previous event's timestamp in the same case
events = events.sort_values(['case', 'position'])
events['prev_ts'] = events.groupby('case')['timestamp'].shift(1)
events['is_out_of_order'] = (events['timestamp'] <= events['prev_ts']) & (events['timestamp'].notna()) & (events['prev_ts'].notna())

# 4. Correction Logic
events['timestamp_fixed'] = events['timestamp']
events['is_error'] = events['is_missing'] | events['is_incomplete'] | events['is_out_of_order']

# We iterate to fix timestamps. For a claim, we need the start time (pos 1) and end time (pos 5)
# or we can propagate from the nearest valid neighbor.
for case, group in events.groupby('case'):
    # Find the first valid timestamp in the claim to anchor the timeline
    # If pos 1 is missing/incomplete, we look for the first valid one.
    # If all are missing, we'd need a global mean, but the prompt implies we use neighbors.
    
    # Let's find the first and last valid timestamps in this specific case
    valid_in_case = group[~group['is_missing'] & ~group['is_incomplete']]
    
    if not valid_in_case.empty:
        # Anchor: if pos 1 is valid, use it. Otherwise, use the first valid one found.
        first_valid = valid_in_case.iloc[0]
        base_ts = first_valid['timestamp']
        
        # If pos 1 was an error, we assume the claim started at the first valid event's time
        # and we'll adjust others relative to it.
        
        for i in range(len(group)):
            row = group.iloc[i]
            pos = row['position']
            
            # If this row is an error, we reconstruct it
            if row['is_error']:
                # If it's the first position, we use the first valid timestamp found in the claim
                if pos == 1:
                    events.loc[(events['case'] == case) & (events['position'] == 1), 'timestamp_fixed'] = base_ts
                else:
                    # Use the median wait time for this position
                    # We need the timestamp of the previous position (pos - 1)
                    # We use the fixed timestamp of the previous position if available, else the original
                    prev_pos_ts = events[(events['case'] == case) & (events['position'] == pos - 1)]['timestamp_fixed'].iloc[0]
                    
                    if pd.notna(prev_pos_ts):
                        wait_min = median_waits.get(pos, 0)
                        # Clip wait_min to a reasonable range (e.g., 0 to 480 mins) to avoid extreme outliers
                        wait_min = max(0, min(wait_min, 480))
                        events.loc[(events['case'] == case) & (events['position'] == pos), 'timestamp_fixed'] = prev_pos_ts + pd.Timedelta(minutes=wait_min)
                    else:
                        # Fallback if previous was also missing/invalid
                        events.loc[(events['case'] == case) & (events['position'] == pos), 'timestamp_fixed'] = base_ts
            else:
                # If not an error, timestamp_fixed is already set to original timestamp
                pass

# Final cleanup
events['timestamp_fixed'] = events['timestamp_fixed'].fillna(events['timestamp'].iloc[0]) # Safety
fixed = events.copy()
fixed['is_error'] = fixed['is_error'].astype(bool)

# Statistics
missing_count = fixed['is_missing'].sum()
incomplete_count = fixed['is_incomplete'].sum()
ooo_count = fixed['is_out_of_order'].sum()
total_corrected = fixed['is_error'].sum()
claims_corrected = fixed[fixed['is_error']].groupby('case').ngroups

answer = f"Corrected {total_corrected} events across {claims_corrected} claims. Errors detected: missing={missing_count}, incomplete={incomplete_count}, out_of_order={ooo_count}. Used median waiting times per position for reconstruction."