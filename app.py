# Check before run: add data files before run
# Make sure file format is accepted by script algorithm
# N2O sensors data fill in exel down to bottom
# After running the script, copy the IP and open it in browser
# when adding the files, rename file name in script
import base64
import io
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, dcc, html, dash_table, no_update
from dash.exceptions import PreventUpdate

DEFAULT_ENV_FILE = "readings22.csv"
DEFAULT_N2O_FILE = "C2AE9F_data 16.03.2026.csv"
DEFAULT_MERGE_TOLERANCE = "10min"
DEFAULT_SMOOTHING_WINDOW = 8
APP_TITLE = "Environmental Data vs N₂O Dashboard"


def parse_uploaded_csv(contents, filename):
    if contents is None:
        return None
    try:
        _, content_string = contents.split(",", 1)
        decoded = base64.b64decode(content_string)
        return pd.read_csv(io.StringIO(decoded.decode("utf-8")))
    except UnicodeDecodeError:
        decoded = base64.b64decode(content_string)
        return pd.read_csv(io.BytesIO(decoded))
    except Exception as exc:
        raise ValueError(f"Could not read uploaded file '{filename}': {exc}") from exc


def load_default_csv(path_str):
    path = Path(path_str)
    if not path.exists():
        return None
    return pd.read_csv(path)


def build_merged_dataframe(env_df, n2o_df, merge_tolerance="10min", smoothing_window=8):
    env = env_df.copy()
    n2o = n2o_df.copy()

    required_env_cols = [
        "Timestamp",
        "humidity1", "humidity2", "humidity3",
        "temperature1", "temperature2", "temperature3",
        "irtemperature1", "irtemperature2", "irtemperature3",
    ]
    required_n2o_cols = ["timestamp", "sample"]

    missing_env = [c for c in required_env_cols if c not in env.columns]
    missing_n2o = [c for c in required_n2o_cols if c not in n2o.columns]

    if missing_env:
        raise ValueError(f"Environment CSV is missing columns: {', '.join(missing_env)}")
    if missing_n2o:
        raise ValueError(f"N₂O CSV is missing columns: {', '.join(missing_n2o)}")

    env["Timestamp"] = pd.to_datetime(env["Timestamp"], errors="coerce")
    n2o["timestamp"] = pd.to_datetime(n2o["timestamp"], dayfirst=True, errors="coerce")

    env = env.dropna(subset=["Timestamp"]).copy()
    n2o = n2o.dropna(subset=["timestamp"]).copy()

    if env.empty:
        raise ValueError("Environment CSV contains no valid timestamps.")
    if n2o.empty:
        raise ValueError("N₂O CSV contains no valid timestamps.")

    env = env.sort_values("Timestamp").reset_index(drop=True)
    n2o = n2o.sort_values("timestamp").reset_index(drop=True)

    env["humidity_avg"] = env[["humidity1", "humidity2", "humidity3"]].mean(axis=1)
    env["temperature_avg"] = env[["temperature1", "temperature2", "temperature3"]].mean(axis=1)
    env["irtemperature_avg"] = env[["irtemperature1", "irtemperature2", "irtemperature3"]].mean(axis=1)

    env = env.rename(columns={"Timestamp": "timestamp"})
    n2o = n2o.rename(columns={"sample": "n2o"})

    env_cols = [
        "timestamp",
        "humidity1", "humidity2", "humidity3", "humidity_avg",
        "temperature1", "temperature2", "temperature3", "temperature_avg",
        "irtemperature1", "irtemperature2", "irtemperature3", "irtemperature_avg",
    ]
    if "humidity_status" in env.columns:
        env_cols.append("humidity_status")

    merged = pd.merge_asof(
        env[env_cols],
        n2o[["timestamp", "n2o"]],
        on="timestamp",
        direction="nearest",
        tolerance=pd.Timedelta(merge_tolerance),
    )

    merged = merged.dropna(subset=["n2o"]).reset_index(drop=True)

    if merged.empty:
        raise ValueError("No overlapping data found. Increase merge tolerance or check timestamps.")

    window = max(1, int(smoothing_window))
    merged["humidity_avg_smooth"] = merged["humidity_avg"].rolling(window=window, min_periods=1).mean()
    merged["temperature_avg_smooth"] = merged["temperature_avg"].rolling(window=window, min_periods=1).mean()
    merged["irtemperature_avg_smooth"] = merged["irtemperature_avg"].rolling(window=window, min_periods=1).mean()
    merged["n2o_smooth"] = merged["n2o"].rolling(window=window, min_periods=1).mean()

    left_axis_max = max(
        merged["humidity_avg"].max(),
        merged["humidity_avg_smooth"].max(),
        merged["temperature_avg"].max(),
        merged["temperature_avg_smooth"].max(),
        merged["irtemperature_avg"].max(),
        merged["irtemperature_avg_smooth"].max(),
    ) + 10

    summary = {
        "env_rows": len(env),
        "n2o_rows": len(n2o),
        "merged_rows": len(merged),
        "merge_tolerance": merge_tolerance,
        "left_axis_max": left_axis_max,
    }

    return merged, summary


def build_figure(merged, summary):
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=merged["timestamp"],
        y=merged["humidity_avg"],
        mode="lines+markers",
        name="Humidity Avg (Raw)",
        line=dict(color="blue", width=1.5),
        opacity=0.40,
        customdata=merged[["humidity1", "humidity2", "humidity3"]],
        hovertemplate=(
            "<b>Time:</b> %{x|%Y-%m-%d %H:%M:%S}<br>"
            "<b>Humidity Avg:</b> %{y:.2f}%<br>"
            "<b>Humidity1:</b> %{customdata[0]:.2f}%<br>"
            "<b>Humidity2:</b> %{customdata[1]:.2f}%<br>"
            "<b>Humidity3:</b> %{customdata[2]:.2f}%<br>"
            "<extra></extra>"
        ),
        yaxis="y1",
    ))

    fig.add_trace(go.Scatter(
        x=merged["timestamp"],
        y=merged["humidity_avg_smooth"],
        mode="lines",
        name="Humidity Avg (Smoothed)",
        line=dict(color="blue", width=3),
        hovertemplate=(
            "<b>Time:</b> %{x|%Y-%m-%d %H:%M:%S}<br>"
            "<b>Humidity Avg Smoothed:</b> %{y:.2f}%<br>"
            "<extra></extra>"
        ),
        yaxis="y1",
    ))

    fig.add_trace(go.Scatter(
        x=merged["timestamp"],
        y=merged["temperature_avg"],
        mode="lines+markers",
        name="Temperature Avg (Raw)",
        line=dict(color="green", width=1.5),
        opacity=0.40,
        customdata=merged[["temperature1", "temperature2", "temperature3"]],
        hovertemplate=(
            "<b>Time:</b> %{x|%Y-%m-%d %H:%M:%S}<br>"
            "<b>Temperature Avg:</b> %{y:.2f} °C<br>"
            "<b>Temperature1:</b> %{customdata[0]:.2f} °C<br>"
            "<b>Temperature2:</b> %{customdata[1]:.2f} °C<br>"
            "<b>Temperature3:</b> %{customdata[2]:.2f} °C<br>"
            "<extra></extra>"
        ),
        yaxis="y1",
    ))

    fig.add_trace(go.Scatter(
        x=merged["timestamp"],
        y=merged["temperature_avg_smooth"],
        mode="lines",
        name="Temperature Avg (Smoothed)",
        line=dict(color="green", width=3),
        hovertemplate=(
            "<b>Time:</b> %{x|%Y-%m-%d %H:%M:%S}<br>"
            "<b>Temperature Avg Smoothed:</b> %{y:.2f} °C<br>"
            "<extra></extra>"
        ),
        yaxis="y1",
    ))

    fig.add_trace(go.Scatter(
        x=merged["timestamp"],
        y=merged["irtemperature_avg"],
        mode="lines+markers",
        name="IR Temp Avg (Raw)",
        line=dict(color="orange", width=1.5),
        opacity=0.40,
        customdata=merged[["irtemperature1", "irtemperature2", "irtemperature3"]],
        hovertemplate=(
            "<b>Time:</b> %{x|%Y-%m-%d %H:%M:%S}<br>"
            "<b>IR Temp Avg:</b> %{y:.2f} °C<br>"
            "<b>IR Temp1:</b> %{customdata[0]:.2f} °C<br>"
            "<b>IR Temp2:</b> %{customdata[1]:.2f} °C<br>"
            "<b>IR Temp3:</b> %{customdata[2]:.2f} °C<br>"
            "<extra></extra>"
        ),
        yaxis="y1",
    ))

    fig.add_trace(go.Scatter(
        x=merged["timestamp"],
        y=merged["irtemperature_avg_smooth"],
        mode="lines",
        name="IR Temp Avg (Smoothed)",
        line=dict(color="orange", width=3),
        hovertemplate=(
            "<b>Time:</b> %{x|%Y-%m-%d %H:%M:%S}<br>"
            "<b>IR Temp Avg Smoothed:</b> %{y:.2f} °C<br>"
            "<extra></extra>"
        ),
        yaxis="y1",
    ))

    fig.add_trace(go.Scatter(
        x=merged["timestamp"],
        y=merged["n2o"],
        mode="lines+markers",
        name="N₂O (Raw)",
        line=dict(color="red", width=1.5),
        opacity=0.40,
        hovertemplate=(
            "<b>Time:</b> %{x|%Y-%m-%d %H:%M:%S}<br>"
            "<b>N₂O Raw:</b> %{y:.2f} ppm<br>"
            "<extra></extra>"
        ),
        yaxis="y2",
    ))

    fig.add_trace(go.Scatter(
        x=merged["timestamp"],
        y=merged["n2o_smooth"],
        mode="lines",
        name="N₂O (Smoothed)",
        line=dict(color="red", width=3),
        hovertemplate=(
            "<b>Time:</b> %{x|%Y-%m-%d %H:%M:%S}<br>"
            "<b>N₂O Smoothed:</b> %{y:.2f} ppm<br>"
            "<extra></extra>"
        ),
        yaxis="y2",
    ))

    fig.update_layout(
        title=dict(
            text="Environmental Data vs N₂O",
            x=0.5,
            xanchor="center",
            y=0.97,
            yanchor="top",
            font=dict(size=26),
        ),
        template="plotly_white",
        height=820,
        hovermode="x unified",
        margin=dict(t=190, l=80, r=80, b=80),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=1.15,
            xanchor="center",
            x=0.5,
        ),
        xaxis=dict(
            title="Time",
            type="date",
            showgrid=True,
            rangeslider=dict(visible=True),
            domain=[0.0, 1.0],
        ),
        yaxis=dict(
            title="Humidity / Temperature / IR Temp",
            side="left",
            showgrid=True,
            zeroline=False,
            range=[0, summary["left_axis_max"]],
        ),
        yaxis2=dict(
            title="N₂O (ppm)",
            overlaying="y",
            side="right",
            showgrid=False,
            zeroline=False,
        ),
    )

    fig.add_annotation(
        xref="paper",
        yref="paper",
        x=0.5,
        y=1.25,
        showarrow=False,
        align="center",
        font=dict(size=14),
        text=(
            f"Env rows: {summary['env_rows']:,} | "
            f"N₂O rows: {summary['n2o_rows']:,} | "
            f"Merged rows: {summary['merged_rows']:,} | "
            f"Tolerance: {summary['merge_tolerance']}"
        ),
    )
    return fig


def build_stats_cards(merged):
    latest = merged.iloc[-1]
    return [
        stat_card("Latest N₂O", f"{latest['n2o']:.2f} ppm"),
        stat_card("Latest Humidity Avg", f"{latest['humidity_avg']:.2f}%"),
        stat_card("Latest Temperature Avg", f"{latest['temperature_avg']:.2f} °C"),
        stat_card("Latest IR Temp Avg", f"{latest['irtemperature_avg']:.2f} °C"),
    ]


def stat_card(label, value):
    return html.Div(
        className="stat-card",
        children=[
            html.Div(label, className="stat-label"),
            html.Div(value, className="stat-value"),
        ],
    )


def small_summary_table(summary):
    df = pd.DataFrame([
        {"Metric": "Environment rows", "Value": summary["env_rows"]},
        {"Metric": "N₂O rows", "Value": summary["n2o_rows"]},
        {"Metric": "Merged rows", "Value": summary["merged_rows"]},
        {"Metric": "Merge tolerance", "Value": summary["merge_tolerance"]},
    ])
    return dash_table.DataTable(
        data=df.to_dict("records"),
        columns=[{"name": c, "id": c} for c in df.columns],
        style_table={"overflowX": "auto"},
        style_header={"fontWeight": "bold", "backgroundColor": "#eef4ff"},
        style_cell={"padding": "10px", "fontFamily": "Arial", "fontSize": 14},
    )


app = Dash(__name__)
app.title = APP_TITLE
server = app.server


def initial_state():
    env_default = load_default_csv(DEFAULT_ENV_FILE)
    n2o_default = load_default_csv(DEFAULT_N2O_FILE)

    if env_default is None or n2o_default is None:
        return None, None, None

    merged, summary = build_merged_dataframe(
        env_default,
        n2o_default,
        merge_tolerance=DEFAULT_MERGE_TOLERANCE,
        smoothing_window=DEFAULT_SMOOTHING_WINDOW,
    )
    fig = build_figure(merged, summary)
    return merged, summary, fig


initial_merged, initial_summary, initial_fig = initial_state()

app.layout = html.Div(
    className="page",
    children=[
        dcc.Store(id="store-env"),
        dcc.Store(id="store-n2o"),

        html.Div(
            className="hero",
            children=[
                html.Div(
                    children=[
                        html.H1("Environmental Data vs N₂O"),
                        html.P("Upload your environment and N₂O CSV files, then open the interactive dashboard in the browser."),
                    ]
                )
            ],
        ),

        html.Div(
            className="panel",
            children=[
                html.Div(
                    className="controls controls-5",
                    children=[
                        html.Div(
                            className="control-card upload-card",
                            children=[
                                html.Label("Environment CSV", className="control-label"),
                                dcc.Upload(
                                    id="upload-env",
                                    children=html.Div([
                                        html.Button("Choose Environment CSV", className="button upload-btn"),
                                        html.Div("or drag and drop file here", className="upload-help"),
                                    ]),
                                    className="upload-box",
                                    multiple=False,
                                ),
                                html.Div(id="env-file-name", className="hidden-status"),
                            ],
                        ),
                        html.Div(
                            className="control-card upload-card",
                            children=[
                                html.Label("N₂O CSV", className="control-label"),
                                dcc.Upload(
                                    id="upload-n2o",
                                    children=html.Div([
                                        html.Button("Choose N₂O CSV", className="button upload-btn"),
                                        html.Div("or drag and drop file here", className="upload-help"),
                                    ]),
                                    className="upload-box",
                                    multiple=False,
                                ),
                                html.Div(id="n2o-file-name", className="hidden-status"),
                            ],
                        ),
                        html.Div(
                            className="control-card small-compact-card",
                            children=[
                                html.Label("Merge tolerance", className="control-label"),
                                dcc.Input(
                                    id="merge-tolerance",
                                    type="text",
                                    value=DEFAULT_MERGE_TOLERANCE,
                                    debounce=True,
                                    className="nice-input compact-input",
                                ),
                            ],
                        ),
                        html.Div(
                            className="control-card small-compact-card",
                            children=[
                                html.Label("Smoothing window", className="control-label"),
                                dcc.Input(
                                    id="smoothing-window",
                                    type="number",
                                    value=DEFAULT_SMOOTHING_WINDOW,
                                    min=1,
                                    step=1,
                                    className="nice-input compact-input",
                                ),
                            ],
                        ),
                        html.Div(
                            className="control-card action-compact-card",
                            children=[
                                html.Label(" ", className="control-label"),
                                html.Button("Update", id="btn-update", className="button update-btn"),
                                html.Div(id="app-status", className="status compact-status"),
                            ],
                        ),
                    ],
                ),
            ],
        ),

        html.Div(
            id="stats-row",
            className="stat-grid",
            children=build_stats_cards(initial_merged) if initial_merged is not None else [],
        ),

        html.Div(
            className="panel",
            children=[
                dcc.Graph(
                    id="main-graph",
                    figure=initial_fig if initial_fig is not None else go.Figure(),
                    config={"displaylogo": False},
                )
            ],
        ),

        html.Div(
            className="panel",
            children=[
                html.Div(
                    style={"display": "flex", "justifyContent": "space-between", "alignItems": "center"},
                    children=[
                        html.H3("Data summary", style={"marginTop": 0, "marginBottom": 0}),
                        html.Button("Show Summary", id="btn-open-summary", className="button", style={"height": "40px", "padding": "10px 16px"}),
                    ],
                ),
            ],
        ),

        html.Div(
            id="summary-modal",
            style={"display": "none"},
            children=[
                html.Div(
                    id="summary-modal-backdrop",
                    style={
                        "position": "fixed",
                        "top": 0,
                        "left": 0,
                        "right": 0,
                        "bottom": 0,
                        "backgroundColor": "rgba(0,0,0,0.45)",
                        "zIndex": 999,
                    },
                ),
                html.Div(
                    style={
                        "position": "fixed",
                        "top": "50%",
                        "left": "50%",
                        "transform": "translate(-50%, -50%)",
                        "width": "min(800px, 92vw)",
                        "background": "white",
                        "borderRadius": "18px",
                        "padding": "20px",
                        "boxShadow": "0 12px 40px rgba(0,0,0,0.22)",
                        "zIndex": 1000,
                    },
                    children=[
                        html.Div(
                            style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "marginBottom": "14px"},
                            children=[
                                html.H3("Data summary", style={"margin": 0}),
                                html.Button(
                                    "Close",
                                    id="btn-close-summary",
                                    className="button",
                                    style={"background": "#6b7a90", "height": "40px", "padding": "8px 14px"},
                                ),
                            ],
                        ),
                        html.Div(
                            id="summary-table",
                            children=small_summary_table(initial_summary) if initial_summary is not None else "Upload CSV files or place default CSV files next to this script.",
                        ),
                    ],
                ),
            ],
        ),
    ],
)


@app.callback(
    Output("store-env", "data"),
    Output("env-file-name", "children"),
    Input("upload-env", "contents"),
    State("upload-env", "filename"),
)
def store_env_file(contents, filename):
    if contents is None:
        return no_update, ""
    df = parse_uploaded_csv(contents, filename)
    return df.to_json(date_format="iso", orient="split"), ""


@app.callback(
    Output("store-n2o", "data"),
    Output("n2o-file-name", "children"),
    Input("upload-n2o", "contents"),
    State("upload-n2o", "filename"),
)
def store_n2o_file(contents, filename):
    if contents is None:
        return no_update, ""
    df = parse_uploaded_csv(contents, filename)
    return df.to_json(date_format="iso", orient="split"), ""


@app.callback(
    Output("main-graph", "figure"),
    Output("stats-row", "children"),
    Output("summary-table", "children"),
    Output("app-status", "children"),
    Input("btn-update", "n_clicks"),
    State("store-env", "data"),
    State("store-n2o", "data"),
    State("merge-tolerance", "value"),
    State("smoothing-window", "value"),
    prevent_initial_call=False,
)
def update_dashboard(_n_clicks, env_json, n2o_json, merge_tolerance, smoothing_window):
    try:
        env_df = pd.read_json(io.StringIO(env_json), orient="split") if env_json is not None else load_default_csv(DEFAULT_ENV_FILE)
        n2o_df = pd.read_json(io.StringIO(n2o_json), orient="split") if n2o_json is not None else load_default_csv(DEFAULT_N2O_FILE)

        if env_df is None or n2o_df is None:
            raise ValueError("Default CSV files were not found. Upload both CSV files or place them in the same folder as this script.")

        merged, summary = build_merged_dataframe(
            env_df,
            n2o_df,
            merge_tolerance=merge_tolerance or DEFAULT_MERGE_TOLERANCE,
            smoothing_window=smoothing_window or DEFAULT_SMOOTHING_WINDOW,
        )

        return (
            build_figure(merged, summary),
            build_stats_cards(merged),
            small_summary_table(summary),
            "Dashboard updated successfully.",
        )

    except Exception as exc:
        empty_fig = go.Figure()
        empty_fig.update_layout(template="plotly_white", title="Dashboard Error")
        return (
            empty_fig,
            [],
            html.Div(str(exc), style={"color": "crimson", "fontWeight": "bold"}),
            f"Error: {exc}",
        )


@app.callback(
    Output("summary-modal", "style"),
    Input("btn-open-summary", "n_clicks"),
    Input("btn-close-summary", "n_clicks"),
    prevent_initial_call=True,
)
def toggle_summary_modal(open_clicks, close_clicks):
    from dash import ctx

    if not ctx.triggered_id:
        raise PreventUpdate

    if ctx.triggered_id == "btn-open-summary":
        return {"display": "block"}

    return {"display": "none"}


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=8050)