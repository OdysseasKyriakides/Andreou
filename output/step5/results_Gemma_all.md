# Step 5 - timestamp correction, 2 LLMs x 2 methods

## Gemma (bpm-gemma4) - Statistical

74.6 s, 5839 + 3884 tokens, retries: 2

Errors during generation: `AttributeError: module 'pandas' has no attribute 'TimeDelta'`; `AttributeError: module 'pandas' has no attribute 'TimeDelta'`; `TypeError: combine() argument 2 must be datetime.time, not Timedelta`

**Failed:** `TypeError: combine() argument 2 must be datetime.time, not Timedelta`

```python
# 1. Identify the normative order and valid events
normative_order = ['Register Claim', 'Verify Documents', 'Evaluate Claim', 'Approve Claim', 'Close Claim']

# Filter events with valid timestamps to calculate statistics
valid_mask = events['timestamp'].notna()
valid_events = events[valid_mask].copy()

# 2. Compute median waiting times per activity transition
# We need the median time between activity i and activity i+1
stats = {}
for i in range(len(normative_order) - 1):
    act_curr = normative_order[i]
    act_next = normative_order[i+1]
    
    # Find pairs of consecutive activities in the same case
    # We use the 'waiting_min' column which is already provided for valid transitions
    mask = (valid_events['activity'] == act_curr) & (valid_events['waiting_min'] > 0)
    subset = valid_events[mask]
    
    if not subset.empty:
        stats[f"{act_curr}->{act_next}"] = subset['waiting_min'].median()
    else:
        stats[f"{act_curr}->{act_next}"] = 0

# 3. Detect and Correct errors
fixed = events.copy()
fixed['is_error'] = False
fixed['timestamp_fixed'] = fixed['timestamp']

# Track the last valid timestamp per case to handle "out of order" and "missing"
# We iterate through the cases to ensure sequential logic
for case_id in events['case'].unique():
    case_data = fixed[fixed['case'] == case_id].sort_values('position')
    
    # Get the base date for the claim (all events happen on the same day)
    # We find the first non-NaT timestamp in the case to establish the day
    valid_case_ts = case_data['timestamp'].dropna()
    if not valid_case_ts.empty:
        base_date = valid_case_ts.iloc[0].date()
    else:
        base_date = None

    last_ts = None
    
    for idx, row in case_data.iterrows():
        current_ts = row['timestamp']
        raw = row['timestamp_raw']
        
        error_type = None
        
        # Detection Logic
        if pd.isna(current_ts):
            error_type = 'missing'
        elif pd.notna(raw) and len(str(raw)) <= 16 and 'T' in str(raw): # e.g. '2026-09-13T16'
            error_type = 'incomplete'
        elif last_ts is not None and (pd.notna(current_ts) and current_ts <= last_ts):
            error_type = 'out of order'
            
        if error_type:
            fixed.at[idx, 'is_error'] = True
            
            # Correction Logic
            # We use the median waiting time from the stats dictionary
            # To find the correct transition, we look at the current activity's position
            pos = row['position']
            
            if pos > 1:
                # Previous activity exists
                prev_act = normative_order[pos-2]
                curr_act = normative_order[pos-1]
                key = f"{prev_act}->{curr_act}"
                wait_min = stats.get(key, 0)
                
                # If we have a previous timestamp, add the median wait
                if last_ts is not None:
                    # Corrected: Use pd.Timedelta(minutes=...)
                    new_ts = last_ts + pd.Timedelta(minutes=wait_min)
                    fixed.at[idx, 'timestamp_fixed'] = new_ts
                else:
                    # Fallback: if first event is missing, we can't easily recover it without a reference
                    fixed.at[idx, 'timestamp_fixed'] = pd.Timestamp.combine(base_date, pd.Timedelta(hours=9)) if base_date else current_ts
            else:
                # First event is missing/wrong
                fixed.at[idx, 'timestamp_fixed'] = pd.Timestamp.combine(base_date, pd.Timedelta(hours=9)) if base_date else current_ts
            
            # Update last_ts for the next iteration in the case
            last_ts = fixed.at[idx, 'timestamp_fixed']
        else:
            last_ts = current_ts

# 4. Final Statistics
missing_count = fixed[fixed['is_error'] & (fixed['timestamp'].isna())].shape[0]
# Incomplete is identified by the logic in the loop, but for summary we count the specific flag
incomplete_count = fixed[fixed['is_error'] & (fixed['timestamp'].notna()) & (fixed['timestamp'].dt.minute == 0) & (fixed['timestamp'].dt.second == 0)].shape[0]
# Out of order is the remainder of the errors
out_of_order_count = (fixed['is_error'].sum()) - missing_count - incomplete_count

total_corrected = fixed['is_error'].sum()
total_claims_corrected = fixed[fixed['is_error']].groupby('case').ngroups

answer = f"Corrected {total_corrected} events across {total_claims_corrected} claims. Errors detected: missing={missing_count}, incomplete={incomplete_count}, out_of_order={out_of_order_count}. Method: Descriptive Statistics (Median Waiting Time)."
```

## Gemma (bpm-gemma4) - ML

76.0 s, 6720 + 4410 tokens, retries: 2

Errors during generation: `ValueError: imports are not allowed`; `KeyError: "['hour', 'weekday'] not in index"`; `KeyError: 'hour'`

**Failed:** `KeyError: 'hour'`

```python
# 1. Preprocessing and Feature Engineering
df = events.copy()
df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
df['hour'] = df['timestamp'].dt.hour
df['weekday'] = df['timestamp'].dt.dayofweek

# Create dummy variables for categorical features
# We use a subset of features to avoid high dimensionality while capturing variance
features_to_encode = ['activity', 'user']
# Create a temporary dataframe for dummy generation to ensure consistency
df_dummies = pd.get_dummies(df[features_to_encode + ['cost', 'hour', 'weekday']], 
                              columns=features_to_encode, dummy_na=False)
df_dummies = df_dummies.fillna(0)

# 2. Identify Valid Data for Training
# A valid timestamp is not NaT, is complete (has minutes), and is chronologically correct
df['prev_ts'] = df.groupby('case')['timestamp'].shift(1)
df['is_chronological'] = df['timestamp'] > df['prev_ts']

# Define "Valid" as: Not NaT, has minutes (length of raw string >= 16), and is chronological
df['is_complete'] = df['timestamp_raw'].astype(str).str.len() >= 16
df['is_valid'] = df['timestamp'].notna() & df['is_complete'] & df['is_chronological']

# Training set: rows where is_valid is True and waiting_min is not NaN
train_df = df[df['is_valid'] & df['waiting_min'].notna()].copy()
# Use the dummy columns generated from the full set to ensure alignment
X_train = df_dummies.loc[train_df.index]
y_train = train_df['waiting_min']

# 3. Model Training
model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# 4. Detection and Correction
fixed = events.copy()
fixed['timestamp'] = pd.to_datetime(fixed['timestamp'], errors='coerce')
fixed['is_error'] = False
fixed['timestamp_fixed'] = fixed['timestamp']

# Track the last known valid timestamp per case
last_valid_ts = {}

# Sort by case and position to ensure sequential processing
fixed = fixed.sort_values(['case', 'position']).reset_index(drop=True)

# Get the list of columns from X_train to ensure consistent input for prediction
model_columns = X_train.columns

for i in range(len(fixed)):
    case_id = fixed.loc[i, 'case']
    current_ts = fixed.loc[i, 'timestamp']
    raw_ts = fixed.loc[i, 'timestamp_raw']
    
    # Error Detection Logic
    error_type = None
    if pd.isna(current_ts):
        error_type = 'missing'
    elif pd.notna(raw_ts) and len(str(raw_ts)) < 16:
        error_type = 'incomplete'
    elif case_id in last_valid_ts and (pd.isna(current_ts) or current_ts <= last_valid_ts[case_id]):
        error_type = 'out of order'
    
    if error_type:
        fixed.loc[i, 'is_error'] = True
        
        # Prepare features for the current row
        # We need to reconstruct the dummy columns for the current row
        row_data = fixed.iloc[i]
        # Create dummy features for the current row
        row_subset = pd.DataFrame({
            'activity': [row_data['activity']],
            'user': [row_data['user']],
            'cost': [row_data['cost']],
            'hour': [row_data['hour'] if pd.notna(row_data['hour']) else 0],
            'weekday': [row_data['weekday'] if pd.notna(row_data['weekday']) else 0]
        })
        row_dummies = pd.get_dummies(row_subset, columns=['activity', 'user'], dummy_na=False)
        # Align columns with X_train
        X_input = row_dummies.reindex(columns=model_columns, fill_value=0)
        
        pred_waiting = model.predict(X_input)[0]
        
        if case_id in last_valid_ts:
            base_ts = last_valid_ts[case_id]
            new_ts = base_ts + pd.Timedelta(minutes=max(0, pred_waiting))
            fixed.loc[i, 'timestamp_fixed'] = new_ts
            # Update the reference for the next event in the case
            last_valid_ts[case_id] = new_ts
        else:
            # If the first event is wrong and no previous valid exists, keep original
            fixed.loc[i, 'timestamp_fixed'] = current_ts
    else:
        # If it was valid, update the reference for the next event in the case
        if pd.notna(current_ts):
            last_valid_ts[case_id] = current_ts

# Final stats
missing_count = (fixed['is_error'] & (fixed['timestamp'].isna())).sum()
incomplete_count = (fixed['is_error'] & (fixed['timestamp'].notna() & (fixed['timestamp_raw'].astype(str).str.len() < 16))).sum()
out_of_order_count = (fixed['is_error'] & (fixed['timestamp'].notna() & (fixed['timestamp'] <= fixed['timestamp'].shift(1)))).sum()
# Note: out_of_order_count logic is simplified for the summary
total_corrected = fixed['is_error'].sum()
claims_corrected = fixed.groupby('case')['is_error'].any().sum()

answer = f"Corrected {total_corrected} events across {claims_corrected} claims. Errors: missing={missing_count}, incomplete={incomplete_count}, out of order={out_of_order_count}. Model: RandomForestRegressor. Features: activity, user, cost, hour, weekday."
```
