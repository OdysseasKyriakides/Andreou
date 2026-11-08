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