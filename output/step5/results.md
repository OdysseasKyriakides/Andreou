# Step 5 - timestamp correction, 2 LLMs x 2 methods

## Gemma (bpm-gemma4) - Statistical

44.3 s, 2647 + 2427 tokens, retries: 1

Errors during generation: `TypeError: operation 'or_' not supported for dtype 'datetime64[us]' with dtype 'bool' (line 91: fixed['is_error'] = fixed['timestamp_fixed'] != fixed['timestamp'] | fixed['timestamp'].isna())`

**Answer:** Corrected 15 events across 15 claims. Errors found: missing=5, incomplete=5, out_of_order=5. Method: Statistical (Median wait time per transition).

Real log - detection vs Step 1 (cases): precision 1.00, recall 0.68, F1 0.81; cases in normative order after fix 93%

Synthetic errors - F1 0.89, MAE 5363.4 min, order restored 81%

Contract: NaT left 0, silent changes 0, numbers in answer not matching 0/2

<details><summary>Corrected events (15)</summary>

| case    | activity         | original            | fixed            | case in Step 1 list   |
|:--------|:-----------------|:--------------------|:-----------------|:----------------------|
| Case_5  | Approve Claim    | 2026-09-05T13:55:00 | 2026-09-05 15:31 | True                  |
| Case_6  | Approve Claim    | 2026-09-06T11:32:00 | 2026-09-06 13:08 | True                  |
| Case_13 | Evaluate Claim   | 2026-09-13T16       | 2026-09-13 15:21 | True                  |
| Case_16 | Verify Documents | 2026-09-16T12       | 2026-09-16 10:54 | True                  |
| Case_20 | Register Claim   | 2026-09-20T10       | 2026-09-13 09:00 | True                  |
| Case_28 | Verify Documents | nan                 | 2026-09-28 09:35 | True                  |
| Case_31 | Approve Claim    | 2026-10-01T13:03:00 | 2026-10-01 14:39 | True                  |
| Case_34 | Evaluate Claim   | nan                 | 2026-10-04 15:35 | True                  |
| Case_60 | Approve Claim    | 2026-10-30T15:36:00 | 2026-10-30 17:12 | True                  |
| Case_70 | Evaluate Claim   | nan                 | 2026-11-09 13:54 | True                  |
| Case_75 | Close Claim      | 2026-11-14T16       | 2026-11-14 15:46 | True                  |
| Case_77 | Register Claim   | nan                 | 2026-09-13 09:00 | True                  |
| Case_81 | Approve Claim    | 2026-11-20T13:18:00 | 2026-11-20 14:54 | True                  |
| Case_84 | Evaluate Claim   | nan                 | 2026-11-23 13:45 | True                  |
| Case_93 | Close Claim      | 2026-12-02T15       | 2026-12-02 15:25 | True                  |

</details>

```python
# 1. Identify the normative order and valid events
normative_order = ['Register Claim', 'Verify Documents', 'Evaluate Claim', 'Approve Claim', 'Close Claim']

# Filter events with valid timestamps to calculate statistics
valid_mask = events['timestamp'].notna()
valid_events = events[valid_mask].copy()

# 2. Compute median waiting times per activity transition
# We calculate the actual difference between consecutive positions for valid events
valid_events = valid_events.sort_values(['case', 'position'])
valid_events['diff'] = valid_events.groupby('case')['timestamp'].diff().dt.total_seconds() / 60

# Map median wait times to the activity that precedes the next step
median_waits = {}
for i in range(len(normative_order) - 1):
    act_current = normative_order[i]
    # The diff for position i+1 corresponds to the transition from act_current
    mask = (valid_events['activity'] == act_current) & (valid_events['position'] == i + 1)
    m_val = valid_events.loc[mask, 'diff'].median()
    median_waits[act_current] = m_val if not np.isnan(m_val) else 0

# 3. Detect and Correct
fixed = events.copy()
fixed['is_error'] = False
fixed['timestamp_fixed'] = fixed['timestamp']

# Track errors for the summary
error_counts = {'missing': 0, 'incomplete': 0, 'out_of_order': 0}
corrected_claims = set()

# Sort to ensure we process in order for 'out_of_order' detection
fixed = fixed.sort_values(['case', 'position'])

for i in range(len(fixed)):
    row = fixed.iloc[i]
    case = row['case']
    pos = row['position']
    act = row['activity']
    
    is_err = False
    
    # Check Missing
    if pd.isna(row['timestamp']):
        is_err = True
        error_counts['missing'] += 1
    # Check Incomplete (timestamp_raw has only date and hour, e.g. '2026-09-13T16')
    elif pd.notna(row['timestamp_raw']) and len(str(row['timestamp_raw'])) <= 13:
        is_err = True
        error_counts['incomplete'] += 1
    # Check Out of Order
    elif i > 0 and fixed.iloc[i-1]['case'] == case:
        if row['timestamp'] <= fixed.iloc[i-1]['timestamp']:
            is_err = True
            error_counts['out_of_order'] += 1

    if is_err:
        fixed.at[fixed.index[i], 'is_error'] = True
        corrected_claims.add(case)
        
        # Correction Logic:
        # If it's the first position, we use a default start of day (09:00)
        if pos == 1:
            fixed.at[fixed.index[i], 'timestamp_fixed'] = pd.Timestamp('2026-09-13 09:00:00')
        else:
            prev_ts = fixed.iloc[i-1]['timestamp_fixed']
            prev_act = fixed.iloc[i-1]['activity']
            wait = median_waits.get(prev_act, 0)
            fixed.at[fixed.index[i], 'timestamp_fixed'] = prev_ts + pd.Timedelta(minutes=wait)
    else:
        fixed.at[fixed.index[i], 'timestamp_fixed'] = row['timestamp']

# Final cleanup: Ensure timestamp_fixed is datetime64 and is_error is correctly flagged
fixed['timestamp_fixed'] = pd.to_datetime(fixed['timestamp_fixed'])
# Correctly flag is_error: True if original was NaT OR if the value was changed
fixed['is_error'] = (fixed['timestamp'].isna()) | (fixed['timestamp'] != fixed['timestamp_fixed'])

# Summary
total_corrected_events = fixed['is_error'].sum()
total_corrected_claims = len(corrected_claims)
answer = f"Corrected {total_corrected_events} events across {total_corrected_claims} claims. Errors found: missing={error_counts['missing']}, incomplete={error_counts['incomplete']}, out_of_order={error_counts['out_of_order']}. Method: Statistical (Median wait time per transition)."
```

## Gemma (bpm-gemma4) - ML

84.7 s, 10655 + 4726 tokens, retries: 3

Errors during generation: `ValueError: imports are not allowed`; `KeyError: 'waiting_min' (line 40: y = train_features_df['waiting_min'])`; `DTypePromotionError: The DType <class 'numpy.dtypes.DateTime64DType'> could not be promoted by <class 'numpy.dtypes.Int64DType'>. This means that no common DType exists for the given inputs. For example they cannot be stored in a single array unless the dtype is `object`. The full list of DTypes is: (<class 'numpy.dtypes.Int64DType'>, <class 'numpy.dtypes.DateTime64DType'>, <class 'numpy.dtypes.BoolDType'>, <class 'numpy.dtypes.Int32DType'>, <class 'numpy.dtypes.Int32DType'>, <class 'numpy.dtypes.BoolDType'>, <class 'numpy.dtypes.BoolDType'>, <class 'numpy.dtypes.BoolDType'>, <class 'numpy.dtypes.BoolDType'>, <class 'numpy.dtypes.BoolDType'>, <class 'numpy.dtypes.BoolDType'>, <class 'numpy.dtypes.BoolDType'>, <class 'numpy.dtypes.BoolDType'>, <class 'numpy.dtypes.BoolDType'>) (line 47: model.fit(X, y))`; `TypeError: Invalid value '2037-01-08 22:40:38.462693568' for dtype 'datetime64[us]' (line 81: df.at[idx, 'timestamp_fixed'] = current_ts)`

**Failed:** `TypeError: Invalid value '2037-01-08 22:40:38.462693568' for dtype 'datetime64[us]' (line 81: df.at[idx, 'timestamp_fixed'] = current_ts)`

```python
# The prompt states pd, np, and the models are already available.
# No imports are allowed.

# 1. Initial Setup and Error Detection
df = events.copy()
df['timestamp_fixed'] = df['timestamp']
df['is_error'] = False

# Identify missing/incomplete (NaT or short raw strings)
df.loc[df['timestamp'].isna(), 'is_error'] = True

# Identify out of order
# Sort to ensure we compare with the immediate predecessor in the process flow
df = df.sort_values(['case', 'position'])
df['prev_ts'] = df.groupby('case')['timestamp_fixed'].shift(1)
df.loc[df['timestamp'] < df['prev_ts'], 'is_error'] = True

# 2. Model Training
# Valid events: not an error and has a valid waiting_min
valid_mask = (~df['is_error']) & (df['waiting_min'].notna()) & (df['waiting_min'] >= 0)
train_df = df[valid_mask].copy()

# Feature Engineering for training
def get_features(data_subset):
    temp = data_subset.copy()
    # Ensure timestamp is datetime for extraction
    temp['timestamp'] = pd.to_datetime(temp['timestamp'])
    temp['hour'] = temp['timestamp'].dt.hour
    temp['weekday'] = temp['timestamp'].dt.dayofweek
    # Use get_dummies for categorical variables
    temp = pd.get_dummies(temp, columns=['activity', 'user'], prefix=['act', 'usr'])
    # Drop non-predictive columns
    drop_cols = ['timestamp', 'timestamp_raw', 'case', 'case_num', 'position', 'waiting_min', 'prev_ts']
    existing_drop = [c for c in drop_cols if c in temp.columns]
    return temp.drop(columns=existing_drop)

# Prepare training data
train_features_df = get_features(train_df)

# Ensure waiting_min is preserved for y
y = train_df['waiting_min']
# X is everything in train_features_df except the target (which was already dropped in get_features)
# We must ensure X contains only numeric types to avoid DTypePromotionError
X = train_features_df.copy()
# Ensure all columns in X are numeric (get_dummies handles most, but we double check)
X = X.apply(pd.to_numeric, errors='coerce').fillna(0)

# Train the model
model = LinearRegression()
model.fit(X, y)

# 3. Correction Logic
# We iterate through cases to reconstruct timestamps sequentially
for case_id, group in df.groupby('case', sort=False):
    last_ts = None
    
    for idx, row in group.iterrows():
        if row['position'] == 1:
            # Anchor for the first event
            if row['is_error']:
                # If first event is missing, we use a default start of day for the claim
                current_ts = pd.Timestamp('2026-09-13 00:00:00')
            else:
                current_ts = row['timestamp_fixed']
        else:
            if row['is_error']:
                # Predict waiting_min using the model
                # Create a single-row dataframe to pass to the feature extractor
                row_df = pd.DataFrame([row])
                row_df['timestamp'] = pd.to_datetime(row_df['timestamp'])
                row_feat_df = get_features(row_df)
                
                # Align columns with the training set X
                row_feat_df = row_feat_df.reindex(columns=X.columns, fill_value=0)
                # Ensure numeric types for prediction
                row_feat_df = row_feat_df.apply(pd.to_numeric, errors='coerce').fillna(0)
                
                pred_wait = model.predict(row_feat_df)[0]
                # Correct timestamp: previous timestamp + predicted minutes
                current_ts = last_ts + pd.Timedelta(minutes=max(0, pred_wait))
                df.at[idx, 'timestamp_fixed'] = current_ts
            else:
                current_ts = row['timestamp_fixed']
        
        last_ts = current_ts

# Finalize the dataframe
fixed = df.copy()
# Ensure no NaT remains
fixed['timestamp_fixed'] = fixed['timestamp_fixed'].fillna(pd.Timestamp('2026-09-13 00:00:00'))

# Statistics
total_corrected = fixed['is_error'].sum()
# Count unique cases that had at least one error
claims_with_errors = fixed[fixed['is_error']]['case'].nunique()

answer = f"Corrected {total_corrected} events across {claims_with_errors} claims. Model: LinearRegression. Features: activity, user, cost, hour, weekday."
```

## Qwen (bpm-qwen) - Statistical

358.6 s, 8506 + 3965 tokens, retries: 3

Errors during generation: `ValueError: imports are not allowed`; `ValueError: imports are not allowed`; `ValueError: cannot insert activity, already exists (line 7: median_waiting_times = valid_events.groupby(['activity', valid_events['activity'].shift(1)])['waiting_time'].median().reset_index())`; `TypeError: unsupported operand type(s) for +: 'Timestamp' and 'Timestamp' (line 32: group.loc[group.index[i], 'timestamp_fixed'] = (prev_timestamp + next_timestamp) / 2)`

**Failed:** `TypeError: unsupported operand type(s) for +: 'Timestamp' and 'Timestamp' (line 32: group.loc[group.index[i], 'timestamp_fixed'] = (prev_timestamp + next_timestamp) / 2)`

```python
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
```

## Qwen (bpm-qwen) - ML

112.5 s, 6472 + 2476 tokens, retries: 3

Errors during generation: `ValueError: imports are not allowed`; `ValueError: imports are not allowed`; `ValueError: imports are not allowed`; `ValueError: imports are not allowed`

**Failed:** `ValueError: imports are not allowed`

```python
import pandas as pd
import numpy as np

# Helper function to extract hour and weekday from timestamp
def extract_features(df):
    df['hour'] = df['timestamp'].dt.hour
    df['weekday'] = df['timestamp'].dt.weekday
    return df

# Extract features from valid timestamps
valid_events = events.dropna(subset=['timestamp'])
valid_events = extract_features(valid_events)

# Encode categorical features
valid_events = pd.get_dummies(valid_events, columns=['activity', 'user'])

# Prepare features and target
X = valid_events.drop(columns=['timestamp', 'timestamp_raw', 'case', 'case_num', 'position', 'cost', 'waiting_min', 'is_error', 'timestamp_fixed'])
y = valid_events['waiting_min']

# Train a RandomForestRegressor model
model = RandomForestRegressor(random_state=42)
model.fit(X, y)

# Function to predict waiting time and correct timestamps
def correct_timestamps(df):
    df = extract_features(df)
    df = pd.get_dummies(df, columns=['activity', 'user'])
    
    # Fill missing features with 0 for prediction
    missing_features = set(X.columns) - set(df.columns)
    for feature in missing_features:
        df[feature] = 0
    
    # Predict waiting time
    df['predicted_waiting_min'] = model.predict(df[X.columns])
    
    # Correct timestamps
    df['timestamp_fixed'] = df['timestamp'].copy()
    for case in df['case'].unique():
        case_df = df[df['case'] == case].sort_values('position')
        for i in range(1, len(case_df)):
            if pd.isna(case_df.iloc[i]['timestamp']):
                case_df.iloc[i, case_df.columns.get_loc('timestamp_fixed')] = case_df.iloc[i-1]['timestamp'] + pd.Timedelta(minutes=case_df.iloc[i]['predicted_waiting_min'])
    
    # Mark errors
    df['is_error'] = df['timestamp'] != df['timestamp_fixed']
    
    return df

# Apply timestamp correction
fixed = correct_timestamps(events)

# Summary
num_errors = fixed['is_error'].sum()
num_claims_corrected = fixed['case'].nunique()
num_missing = fixed[fixed['timestamp'].isna()]['is_error'].sum()
num_incomplete = fixed[fixed['timestamp_raw'].str.contains(r'\d{4}-\d{2}-\d{2}T\d{2}$')]['is_error'].sum()
num_out_of_order = fixed[fixed['waiting_min'] < 0]['is_error'].sum()

answer = (
    f"Corrected {num_errors} events across {num_claims_corrected} claims. "
    f"Missing timestamps: {num_missing}, Incomplete timestamps: {num_incomplete}, Out of order timestamps: {num_out_of_order}. "
    f"Used RandomForestRegressor with features: {', '.join(X.columns)}."
)
```
