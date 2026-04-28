# Environmental Data vs N₂O Dashboard

A Dash-based interactive dashboard for comparing environmental sensor data with N₂O readings.

This project lets you:

- upload an **environment CSV** and an **N₂O CSV**
- merge both datasets by timestamp using a configurable tolerance
- smooth the data using a rolling window
- visualise humidity, temperature, IR temperature, and N₂O together on one dashboard
- view a quick summary of merged rows and latest values

---

## Project structure

Place the files like this:

```text
project_folder/
├── app.py
├── requirements.txt
├── assets/
│   └── style.css
├── readings22.csv
└── C2AE9F_data 16.03.2026.csv
```

### Important notes

- `requirements.txt` should stay in the **root folder**, beside `app.py`
- `style.css` should be inside the **assets** folder, because Dash automatically loads CSS from `assets/`
- the two CSV files are optional default files; users can also upload their own through the dashboard

---

## Requirements

Install Python dependencies using:

```bash
pip install -r requirements.txt
```

Example `requirements.txt`:

```text
dash>=2.4
pandas>=1.5
plotly>=5.0
```

---

## How to run

Open a terminal in the project folder and run:

```bash
python app.py
```

Then open this address in your browser:

```text
http://127.0.0.1:8050
```

---

## How the app works

The dashboard supports two ways of loading data:

### 1. Default CSV files
If these files are present in the same folder as `app.py`, the app will load them automatically on startup:

- `readings22.csv`
- `C2AE9F_data 16.03.2026.csv`

### 2. Upload your own CSV files
You can upload:

- one environment CSV
- one N₂O CSV

Then click **Update** to process and display the graph.

---

## Required CSV format

### Environment CSV must contain these columns

```text
Timestamp
humidity1
humidity2
humidity3
temperature1
temperature2
temperature3
irtemperature1
irtemperature2
irtemperature3
```

Optional column:

```text
humidity_status
```

### N₂O CSV must contain these columns

```text
timestamp
sample
```

---

## Data processing

The app performs the following steps:

1. reads both CSV files
2. converts timestamps into datetime format
3. averages the 3 humidity channels
4. averages the 3 temperature channels
5. averages the 3 IR temperature channels
6. matches environment rows with N₂O rows using nearest timestamp merge
7. applies merge tolerance, for example `10min`
8. applies rolling smoothing using the selected smoothing window
9. plots raw and smoothed values

---

## Dashboard features

- drag-and-drop CSV upload
- configurable **merge tolerance**
- configurable **smoothing window**
- interactive Plotly chart
- range slider on the time axis
- raw and smoothed traces for all main signals
- summary modal with row counts and merge information
- latest-value statistic cards

---

## User inputs

### Merge tolerance
Example values:

- `1min`
- `5min`
- `10min`
- `30min`
- `1h`

This controls how far apart timestamps are allowed to be when merging data.

### Smoothing window
This must be a positive integer.

Example:

- `1` = no effective smoothing
- `8` = smoother trend line using 8 samples

---

## Troubleshooting

### 1. Dashboard opens but has no styling
Check that the CSS file is here:

```text
assets/style.css
```

Not here:

```text
style.css
```

### 2. App says default CSV files were not found
Either:

- place the default CSV files beside `app.py`, or
- upload both CSV files manually in the dashboard

### 3. No overlapping data found
This usually means:

- the timestamps do not line up closely enough, or
- the merge tolerance is too small

Try increasing the merge tolerance.

### 4. Environment CSV is missing columns
Make sure the uploaded environment file includes all required column names exactly as expected.

### 5. N₂O CSV is missing columns
Make sure the N₂O file includes:

- `timestamp`
- `sample`

---

## Sharing this project with others

If someone else wants to use the project, give them:

- `app.py`
- `requirements.txt`
- `assets/style.css`
- optional sample CSV files
- this `README.md`

Then they only need to run:

```bash
pip install -r requirements.txt
python app.py
```

---

## Recommended setup for GitHub

If you upload this project to GitHub, keep this structure:

```text
project_folder/
├── app.py
├── README.md
├── requirements.txt
├── assets/
│   └── style.css
├── readings22.csv
└── C2AE9F_data 16.03.2026.csv
```

---

## License

Add a license if you plan to share or publish the project publicly.
