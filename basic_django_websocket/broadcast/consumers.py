from channels.generic.websocket import AsyncWebsocketConsumer
import pandas as pd
import numpy as np
from scipy.signal import find_peaks, butter, filtfilt
import joblib
import json


class ReadConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """
        Connect a client to the websocket.
        Specific actions to be performed when a client gets connected is also defined here.
        """
        await self.accept()

    async def disconnect(self, code):
        """
        Actions to be performed when a client disconnects
        """
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.imu_buffer = []  # buffer for incoming IMU samples
        self.FEATURE_WINDOW_SIZE = 20  # number of rows needed per feature window
        self.SAMPLING_RATE_HZ = 100
        self.STEP_LENGTH_METERS = 0.6

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return

        try:
            # Parse incoming IMU JSON data
            imu_data = json.loads(text_data)

            # Add the new IMU sample to the buffer
            self.imu_buffer.append(imu_data)

            # Only process when enough samples are collected
            if len(self.imu_buffer) >= self.FEATURE_WINDOW_SIZE:


                # Convert buffer to DataFrame
                df = pd.DataFrame(self.imu_buffer[-self.FEATURE_WINDOW_SIZE:])  # sliding window

                # --- Feature extraction ---
                def extract_features(df, window_size=self.FEATURE_WINDOW_SIZE):
                    features_list = []
                    expected_raw_cols = ['acc_x', 'acc_y', 'acc_z', 'gyro_x', 'gyro_y', 'gyro_z', 'mag_x', 'mag_y',
                                         'mag_z']
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
                        sample_merged_df = pd.read_csv(
                            r'C:\Users\zaidd\OneDrive\Desktop\machine learning\all_features_with_labels.csv')
                        expected_cols = sample_merged_df.drop('Label', axis=1).columns.tolist()
                        extracted_df = extracted_df.reindex(columns=expected_cols, fill_value=0.0)
                    except FileNotFoundError:
                        pass
                    return extracted_df

                # --- Step counting ---
                def count_steps(acc_data, sampling_rate=self.SAMPLING_RATE_HZ, window_size=self.FEATURE_WINDOW_SIZE):
                    if len(acc_data) < window_size or acc_data.isnull().any().any():
                        return 0
                    magnitude = np.sqrt(acc_data['acc_x'] ** 2 + acc_data['acc_y'] ** 2 + acc_data['acc_z'] ** 2)
                    cutoff_freq = 4.2
                    nyquist_freq = 0.5 * sampling_rate
                    normal_cutoff = min(cutoff_freq / nyquist_freq, 0.99)
                    b, a = butter(4, normal_cutoff, btype='low', analog=False)
                    filtered = filtfilt(b, a, magnitude)
                    min_peak_height = np.mean(filtered)
                    min_peak_distance = int(sampling_rate / 2.5)
                    peaks, _ = find_peaks(filtered, height=min_peak_height, distance=min_peak_distance)
                    return len(peaks)

                # --- Load model (if not already loaded) ---
                if not hasattr(self, 'loaded_model'):
                    model_filename = r'C:\Users\zaidd\OneDrive\Desktop\machine learning\random_forest_model3.joblib'
                    self.loaded_model = joblib.load(model_filename)

                # --- Extract features and predict ---
                features_df = extract_features(df)
                if features_df.empty:
                    await self.send(text_data=json.dumps({"error": "No features extracted"}))
                    return

                prediction = self.loaded_model.predict(features_df)[0]

                if {'acc_x', 'acc_y', 'acc_z'}.issubset(df.columns):
                    steps = count_steps(df[['acc_x', 'acc_y', 'acc_z']])
                else:
                    steps = 0

                if prediction == 'Walking' and steps == 0:
                    prediction = 'Standing'

                # Send prediction back to client
                await self.send(text_data=json.dumps({
                    "activity": prediction
                }))

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({"error": "Invalid JSON"}))
        except Exception as e:
            await self.send(text_data=json.dumps({"error": str(e)}))


"""
To send data from websocket use: 
    "await self.send(<message>)" if self.send is being used in async function
    OR
    from asgiref.sync import async_to_sync
    async_to_sync(self.send)(<message>) if self.send is being used in sync function
"""
