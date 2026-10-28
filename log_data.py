"""
Prepares the event log for the assistant (Steps 3-5).

events  one row per event, in the order written in the file
cases   one row per claim (case) with totals
"""
import pandas as pd

CSV = "insurance_claims_log.csv"


def load_events(csv=CSV):
    df = pd.read_csv(csv, dtype={"CaseID": str})
    df = df.rename(columns={"CaseID": "case", "Activity": "activity", "Timestamp": "timestamp_raw",
                            "User": "user", "Cost": "cost"})
    df["timestamp"] = pd.to_datetime(df["timestamp_raw"], format="mixed", errors="coerce")
    df["case_num"] = df["case"].str.extract(r"(\d+)").astype(int)
    df["position"] = df.groupby("case").cumcount() + 1
    # minutes since the previous event of the same case (file order); can be negative or
    # missing where Step 1 found timestamp errors
    df["waiting_min"] = df.groupby("case")["timestamp"].diff().dt.total_seconds() / 60
    return df[["case", "case_num", "position", "activity", "timestamp", "timestamp_raw",
               "user", "cost", "waiting_min"]]


def build_cases(events):
    g = events.groupby("case")
    cases = pd.DataFrame({
        "case_num": g["case_num"].first(),
        "start": g["timestamp"].min(),
        "end": g["timestamp"].max(),
        "total_cost": g["cost"].sum(),
        "n_events": g.size(),
        "users": g["user"].apply(lambda s: ", ".join(sorted(s.unique()))),
        "variant": g["activity"].apply(" -> ".join),
        # process-mining convention: order by timestamp (events without one are left out)
        "variant_by_time": events.dropna(subset=["timestamp"]).sort_values(["case", "timestamp"])
                                 .groupby("case")["activity"].apply(" -> ".join),
    })
    cases["duration_h"] = (cases["end"] - cases["start"]).dt.total_seconds() / 3600
    return cases.reset_index().sort_values("case_num").reset_index(drop=True)


SCHEMA = """
DataFrame `events` (one row per event, 500 rows, ordered by case and position):
  case (str, e.g. 'Case_7'), case_num (int), position (int, 1 = first event of the case),
  activity (str: 'Register Claim', 'Verify Documents', 'Evaluate Claim', 'Approve Claim', 'Close Claim'),
  timestamp (datetime64, NaT if missing), timestamp_raw (str, as in the file),
  user (str: 'User_A' .. 'User_E'), cost (int, US dollars spent on this event),
  waiting_min (float, minutes since the previous event of the same case; NaN for the first event or a
               missing timestamp; can be negative because the log contains known timestamp errors)

DataFrame `cases` (one row per claim, 100 rows):
  case, case_num, start, end (datetime64), total_cost (int, $), n_events, users (str),
  variant (str, activities joined with ' -> ' in the order written in the file),
  variant_by_time (str, activities ordered by timestamp, events without timestamp left out - this is the
                   process-mining definition of a variant; use it for questions about variants),
  duration_h (float, hours from first to last event)
"""
