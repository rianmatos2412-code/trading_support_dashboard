import pandas as pd
import numpy as np

    
def calculate_swing_points(df, window=2):
    """
    Calculates swing highs and swing lows in a DataFrame.

    Args:
        df (pd.DataFrame): DataFrame with 'High' and 'Low' columns.
        window (int): Number of bars to look back and forward for comparison.
                      A window of 2 means 2 bars before and 2 bars after.

    Returns:
        pd.DataFrame: Original DataFrame with 'SwingHigh' and 'SwingLow' columns.
    """
    df['SwingHigh'] = False
    df['SwingLow'] = False

    # Identify Swing Highs
    # A swing high is a high that is higher than 'window' bars before and after it.
    df['SwingHigh'] = np.where(
        (df['high'] == df['high'].rolling(window=2*window+1, center=True).max()) &
        (df['high'].shift(window).notna()) &
        (df['high'].shift(-window).notna()),
        df['high'],
        False
    )

    # Identify Swing Lows
    # A swing low is a low that is lower than 'window' bars before and after it.
    df['SwingLow'] = np.where(
        (df['low'] == df['low'].rolling(window=2*window+1, center=True).min()) &
        (df['low'].shift(window).notna()) &
        (df['low'].shift(-window).notna()),
        df['low'],
        False
    )
    swing_high_list = []
    swing_low_list = []
    for idx in range(len(df["SwingHigh"])):
        # Use .iloc for positional access to avoid index label issues after dataframe reversal
        swing_high_value = df["SwingHigh"].iloc[idx]
        swing_low_value = df["SwingLow"].iloc[idx]
        
        if swing_high_value != 0:
            swing_high_list.append((idx, swing_high_value))
        if swing_low_value != 0:
            swing_low_list.append((idx, swing_low_value))
    return swing_high_list, swing_low_list

def filter_between(points_main, points_other, keep="min"):
    """
    Generic filtering:
    - points_main : list of (idx, value) -> high or low list (the boundary points)
    - points_other: the opposite list to filter inside the boundaries
    - keep       : "min" → keep lowest inside   OR   "max" → keep highest inside
    """

    filtered = []

    for i in range(len(points_main) - 1):
        start_idx = points_main[i][0]
        end_idx = points_main[i + 1][0]

        # collect opposite points inside (start, end)
        inside = [
            p for p in points_other 
            if start_idx < p[0] < end_idx
        ]

        if len(inside) == 0:
            continue

        if keep == "min":
            selected = min(inside, key=lambda x: x[1])
        else:
            selected = max(inside, key=lambda x: x[1])

        filtered.append(selected)

    # --- NEW: ensure outermost points are preserved ---
    if points_other:
        # Add left-most point if not included
        if points_other[0] not in filtered:
            filtered.insert(0, points_other[0])

        # Add right-most point if not included
        if points_other[-1] not in filtered:
            filtered.append(points_other[-1])

    return filtered

def enforce_strict_alternation(highs, lows):
    highs = sorted(highs)
    lows = sorted(lows)

    # merge lists
    merged = [(i, v, 'H') for i, v in highs] + \
             [(i, v, 'L') for i, v in lows]
    merged.sort()

    final_highs = []
    final_lows = []

    last_type = None

    for idx, val, t in merged:
        # if two highs in a row → keep only the higher one
        if t == last_type:
            if t == 'H':
                if val > final_highs[-1][1]:
                    final_highs[-1] = (idx, val)
            else:
                if val < final_lows[-1][1]:
                    final_lows[-1] = (idx, val)
        else:
            if t == 'H':
                final_highs.append((idx, val))
            else:
                final_lows.append((idx, val))

        last_type = t

    return final_highs, final_lows


def filter_rate(highs, lows, rate=0.03):
    """
    - Always keep the first and last swing points.
    - For each swing high, compare with nearest left/right lows.
    - Remove swing high when low-to-high move is < rate.
    - Remove only the low that fails the rule.
    - If both lows fail, remove high and keep the LOWER of the two lows.
    """

    highs = highs.copy()
    lows = lows.copy()

    # We build new clean lists
    clean_highs = []
    clean_lows = lows.copy()

    for h_idx, h_val in highs:

        # find nearest left low
        left_candidates = [l for l in clean_lows if l[0] < h_idx]
        left_low = left_candidates[-1] if left_candidates else None

        # find nearest right low
        right_candidates = [l for l in clean_lows if l[0] > h_idx]
        right_low = right_candidates[0] if right_candidates else None

        # Edge case: keep if no left OR right low
        if left_low is None or right_low is None:
            clean_highs.append((h_idx, h_val))
            continue

        # compute % move
        left_rate  = (h_val - left_low[1])  / left_low[1]
        right_rate = (h_val - right_low[1]) / right_low[1]

        # CASE 1: both sides < rate
        if left_rate < rate and right_rate < rate:
            # remove the HIGH completely
            # keep the lower of the two lows
            lower_low = left_low if left_low[1] < right_low[1] else right_low
            clean_lows = [l for l in clean_lows if l == lower_low or l not in (left_low, right_low)]
            continue

        # CASE 2: left < rate only
        if left_rate < rate:
            clean_lows.remove(left_low)
            continue  # remove high too

        # CASE 3: right < rate only
        if right_rate < rate:
            clean_lows.remove(right_low)
            continue  # remove high too

        # CASE 4: both rates OK → keep high
        clean_highs.append((h_idx, h_val))

    # Final step: enforce alternation (optional but recommended)
    clean_highs, clean_lows = enforce_strict_alternation(clean_highs, clean_lows)

    return clean_highs, clean_lows
