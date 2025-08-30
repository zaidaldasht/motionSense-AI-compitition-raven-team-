import pandas as pd
import numpy as np
from scipy.signal import find_peaks, butter, filtfilt
import joblib
from collections import Counter
import os

# --- Configuration ---
SAMPLING_RATE_HZ = 100
FEATURE_WINDOW_SIZE = 20
STEP_LENGTH_METERS = 0.60  # average step length; adjust per person

# --- Feature Extraction Function ---
def extract_features(df, window_size=FEATURE_WINDOW_SIZE):
    features_list = []
    expected_raw_cols = ['acc_x', 'acc_y', 'acc_z', 'gyro_x', 'gyro_y', 'gyro_z', 'mag_x', 'mag_y', 'mag_z']

    for col in expected_raw_cols:
        if col not in df.columns:
            df[col] = 0.0

    for start in range(0, len(df) - window_size + 1, window_size):
        window = df.iloc[start:start + window_size]
        feature_row = {}
        for col in expected_raw_cols:
            values = window[col].values
            feature_row[f'{col}_mean'] = np.mean(values)
            feature_row[f'{col}_std'] = np.std(values)
            feature_row[f'{col}_min'] = np.min(values)
            feature_row[f'{col}_max'] = np.max(values)
            feature_row[f'{col}_range'] = np.max(values) - np.min(values)
            feature_row[f'{col}_peaks'] = len(find_peaks(values)[0]) if len(values) > 1 else 0
        features_list.append(feature_row)

    extracted_df = pd.DataFrame(features_list)

    try:
        sample_merged_df = pd.read_csv(r'C:\Users\Gamer\Downloads/all_features_with_labels.csv')
        expected_feature_cols = sample_merged_df.drop('Label', axis=1).columns.tolist()
        extracted_df = extracted_df.reindex(columns=expected_feature_cols, fill_value=0.0)
    except FileNotFoundError:
        print("⚠️ Could not find 'all_features_with_labels.csv'. Ensure the file is in the same directory.")
        return pd.DataFrame()

    return extracted_df

# --- Step Counting Function ---
def count_steps(accelerometer_data, sampling_rate, window_size):
    if len(accelerometer_data) < window_size or accelerometer_data.isnull().any().any():
        return 0

    magnitude = np.sqrt(
        accelerometer_data['acc_x'] ** 2 +
        accelerometer_data['acc_y'] ** 2 +
        accelerometer_data['acc_z'] ** 2
    )

    cutoff_freq = 4.2
    nyquist_freq = 0.5 * sampling_rate
    if nyquist_freq == 0:
        return 0
    normal_cutoff = cutoff_freq / nyquist_freq
    if normal_cutoff >= 1:
        normal_cutoff = 0.99

    try:
        b, a = butter(4, normal_cutoff, btype='low', analog=False)
        filtered_magnitude = filtfilt(b, a, magnitude)
    except ValueError:
        return 0

    min_peak_height = np.mean(filtered_magnitude)
    min_peak_distance_samples = int(sampling_rate / 2.5)

    try:
        peaks, _ = find_peaks(filtered_magnitude, height=min_peak_height, distance=min_peak_distance_samples)
    except ValueError:
        return 0

    return len(peaks)

# --- Magnetometer Heading Calculation ---
def calculate_magnetometer_heading(df):
    if 'mag_x' not in df.columns or 'mag_y' not in df.columns:
        return pd.Series(dtype=float)
    heading_rad = np.arctan2(df['mag_y'], df['mag_x'])
    heading_deg = np.degrees(heading_rad)
    return (heading_deg + 360) % 360

# --- Load Trained Model ---
model_filename = r'C:\Users\Gamer\Downloads\random_forest_model3.joblib'
try:
    loaded_model = joblib.load(model_filename)
    print(f"✅ Model '{model_filename}' loaded successfully.")
except Exception as e:
    print(f"❌ Failed to load model: {e}")
    exit()

# --- Load Raw IMU Data ---
raw_data_csv_path = r'C:\Users\Gamer\Downloads\testtest4.csv'
try:
    new_raw_data_df = pd.read_csv(raw_data_csv_path)
    print(f"✅ Raw IMU data loaded from '{raw_data_csv_path}'.")
except FileNotFoundError:
    print(f"❌ Failed to load raw data from '{raw_data_csv_path}'.")
    exit()

print("\n📊 First 5 rows of raw IMU data:")
print(new_raw_data_df.head())

# --- Feature Extraction ---
features_df = extract_features(new_raw_data_df, window_size=FEATURE_WINDOW_SIZE)
if features_df.empty:
    print("⚠️ No features extracted. Not enough data or missing files.")
    exit()

print("\n📐 First 5 rows of extracted features:")
print(features_df.head())

# --- Make Predictions ---
try:
    predictions = list(loaded_model.predict(features_df))

    # ==== REMOVE SHORT "Standing" SEGMENTS ====
    min_standing_windows = int((1000 * SAMPLING_RATE_HZ) / FEATURE_WINDOW_SIZE)  # 2 seconds
    i = 0
    while i < len(predictions):
        if predictions[i] == "Standing":
            start = i
            while i < len(predictions) and predictions[i] == "Standing":
                i += 1
            length = i - start
            if length < min_standing_windows:
                replace_label = predictions[start - 1] if start > 0 else predictions[i] if i < len(predictions) else "Unknown"
                for j in range(start, start + length):
                    predictions[j] = replace_label
        else:
            i += 1
    # ==========================================

    print("\n🤖 Predictions and Activity Details:")
    global_step_counter = 0
    total_rotation_degrees_right = 0.0
    total_rotation_degrees_left = 0.0

    for i, pred in enumerate(predictions):
        window_start_idx = i * FEATURE_WINDOW_SIZE
        window_end_idx = window_start_idx + FEATURE_WINDOW_SIZE
        current_raw_window = new_raw_data_df.iloc[window_start_idx:window_end_idx].copy()

        steps_in_window = 0
        if {'acc_x', 'acc_y', 'acc_z'}.issubset(current_raw_window.columns):
            steps_in_window = count_steps(
                current_raw_window[['acc_x', 'acc_y', 'acc_z']],
                SAMPLING_RATE_HZ,
                FEATURE_WINDOW_SIZE
            )

        if pred == 'Walking' and steps_in_window == 0:
            pred = 'Standing'

        print(f"\n🪟 Window {i + 1} → Prediction: {pred}")

        if pred == 'Walking':
            if steps_in_window > 0:
                distance_m = steps_in_window * STEP_LENGTH_METERS
                distance_km = distance_m / 1000

                print(f" 🚶 Detected {steps_in_window} steps in this window.")
                print(f" 📏 Distance in this window: {distance_m:.2f} m ({distance_km:.3f} km)")

                global_step_counter += steps_in_window
        elif pred in ['Rotation Left', 'Rotation Right']:
            if not current_raw_window.empty and {'mag_x', 'mag_y'}.issubset(current_raw_window.columns):
                heading_values = calculate_magnetometer_heading(current_raw_window)
                if len(heading_values) > 1:
                    start_heading = heading_values.iloc[0]
                    end_heading = heading_values.iloc[-1]
                    angle_diff = (end_heading - start_heading + 180) % 360 - 180
                    rotation_in_window = abs(angle_diff)
                    print(f" ↪️ Rotation: {rotation_in_window:.1f}°")
                    if pred == 'Rotation Right':
                        total_rotation_degrees_right += rotation_in_window
                    else:
                        total_rotation_degrees_left += rotation_in_window
                else:
                    print(" Rotation: N/A (not enough data)")
            else:
                print(" Rotation: N/A (missing mag data)")
        else:
            print(" No specific details to report for this activity.")

    # --- Final Summary ---
    overall_pred = Counter(predictions).most_common(1)[0][0]
    total_distance_m = global_step_counter * STEP_LENGTH_METERS
    total_distance_km = total_distance_m / 1000

    print(f"\n🏁 Overall predicted activity: {overall_pred}")
    print(f"✅ Total steps detected: {global_step_counter}")
    print(f"📏 Total estimated distance: {total_distance_m:.2f} m ({total_distance_km:.3f} km)")
    print(f"✅ Total estimated rotation to the right: {total_rotation_degrees_right:.1f}°")
    print(f"✅ Total estimated rotation to the left: {total_rotation_degrees_left:.1f}°")

except Exception as e:
    print(f"❌ Prediction or activity detail calculation failed: {e}")

print("\n--- Process Complete ---")
