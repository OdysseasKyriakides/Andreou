# Step 1: Compute typical waiting times between consecutive activities
valid_events = events.dropna(subset=['timestamp'])
valid_events['next_activity'] = valid_events.groupby('case')['activity'].shift(-1)
valid_events['waiting_time'] = (valid_events.groupby('case')['timestamp'].shift(-1) - valid_events['timestamp']).dt.total_seconds() / 60

# Compute median waiting times for each pair of consecutive activities
median_waiting_times = valid_events.groupby(['activity', 'next_activity'])['waiting_time'].median().reset_index()
median_waiting_times.columns = ['activity', 'next_activity', 'median_waiting_time']

# Step 2: Detect and correct wrong timestamps
events['is_error'] = False
events['timestamp_fixed'] = events['timestamp']

# Function to correct timestamps
def correct_timestamps(group):
    group = group.sort_values('position')
    for i in range(len(group)):
        if pd.isna(group.loc[group.index[i], 'timestamp']):
            group.loc[group.index[i], 'is_error'] = True
            if i == 0:
                # First event in the case, use the next valid timestamp
                next_timestamp = group.loc[group.index[i+1], 'timestamp']
                group.loc[group.index[i], 'timestamp_fixed'] = next_timestamp - pd.Timedelta(minutes=median_waiting_times.loc[(median_waiting_times['activity'] == group.loc[group.index[i], 'activity']) & (median_waiting_times['next_activity'] == group.loc[group.index[i+1], 'activity']), 'median_waiting_time'].values[0])
            elif i == len(group) - 1:
                # Last event in the case, use the previous valid timestamp
                prev_timestamp = group.loc[group.index[i-1], 'timestamp']
                group.loc[group.index[i], 'timestamp_fixed'] = prev_timestamp + pd.Timedelta(minutes=median_waiting_times.loc[(median_waiting_times['activity'] == group.loc[group.index[i-1], 'activity']) & (median_waiting_times['next_activity'] == group.loc[group.index[i], 'activity']), 'median_waiting_time'].values[0])
            else:
                # Middle event, use the average of the previous and next valid timestamps
                prev_timestamp = group.loc[group.index[i-1], 'timestamp']
                next_timestamp = group.loc[group.index[i+1], 'timestamp']
                group.loc[group.index[i], 'timestamp_fixed'] = (prev_timestamp + next_timestamp) / 2
    return group

# Apply the correction function to each case
fixed = events.groupby('case').apply(correct_timestamps).reset_index(drop=True)

# Step 3: Handle incomplete timestamps
incomplete_mask = events['timestamp'].isna() & events['timestamp_raw'].notna()
fixed.loc[incomplete_mask, 'timestamp_fixed'] = pd.to_datetime(events.loc[incomplete_mask, 'timestamp_raw'], errors='coerce') + pd.Timedelta(minutes=median_waiting_times.loc[(median_waiting_times['activity'] == events.loc[incomplete_mask, 'activity']) & (median_waiting_times['next_activity'] == events.loc[incomplete_mask, 'activity'].shift(1)), 'median_waiting_time'].values[0])
fixed.loc[incomplete_mask, 'is_error'] = True

# Step 4: Handle out of order timestamps
fixed['prev_timestamp'] = fixed.groupby('case')['timestamp_fixed'].shift(1)
out_of_order_mask = (fixed['timestamp_fixed'] <= fixed['prev_timestamp']) & ~fixed['is_error']
fixed.loc[out_of_order_mask, 'timestamp_fixed'] = fixed.loc[out_of_order_mask, 'prev_timestamp'] + pd.Timedelta(minutes=median_waiting_times.loc[(median_waiting_times['activity'] == fixed.loc[out_of_order_mask, 'activity']) & (median_waiting_times['next_activity'] == fixed.loc[out_of_order_mask, 'activity'].shift(1)), 'median_waiting_time'].values[0])
fixed.loc[out_of_order_mask, 'is_error'] = True

# Step 5: Summary
num_events_corrected = fixed['is_error'].sum()
num_claims_corrected = fixed['case'].nunique()
missing_count = fixed['timestamp'].isna().sum()
incomplete_count = (fixed['timestamp'].isna() & fixed['timestamp_raw'].notna()).sum()
out_of_order_count = (fixed['timestamp_fixed'] <= fixed['prev_timestamp']).sum()

answer = (
    f"Corrected {num_events_corrected} events across {num_claims_corrected} claims. "
    f"Missing timestamps: {missing_count}, Incomplete timestamps: {incomplete_count}, "
    f"Out of order timestamps: {out_of_order_count}. "
    f"Used median waiting times between consecutive activities for correction."
)