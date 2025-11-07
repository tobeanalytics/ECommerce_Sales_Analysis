# E-commerce Sales Dashboard 
import pandas as pd
import numpy as np
from dash import Dash, dcc, html, Input, Output, State
import plotly.express as px
import plotly.graph_objects as go


# Load data
url = "https://drive.google.com/uc?export=download&id=1nBqxY2g-B1KGFbI3AxNbhYLlwyjpae8m"
df = pd.read_csv(url)
# Parse InvoiceDate to datetime
df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")

# Clean and ensure numeric
df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce").fillna(0)
df["UnitPrice"] = pd.to_numeric(df["UnitPrice"], errors="coerce").fillna(0)

# Compute TotalPrice if missing or zero
if "TotalPrice" not in df.columns or df["TotalPrice"].sum() == 0:
    df["TotalPrice"] = df["Quantity"] * df["UnitPrice"]

# Add period helpers
df["OrderDate"] = df["InvoiceDate"].dt.date
df["OrderMonth"] = df["InvoiceDate"].dt.to_period("M").dt.to_timestamp()
df["OrderWeek"] = df["InvoiceDate"].dt.to_period("W").dt.start_time

# Convert numeric columns safely
numeric_cols = ["Quantity", "UnitPrice", "TotalPrice", "Month", "Year"]


# Initialize Dash
app = Dash(__name__)
server = app.server

# Layout
app.layout = html.Div([
    # Title & intro
    html.Div([
        html.H2("🛍 E-commerce Sales Dashboard",
                style={"textAlign": "center", "color": "#007bff", "marginBottom": "0"}),
        html.P("Explore sales trends, top products, and customer segments interactively.",
               style={"textAlign": "center", "color": "#444", "marginBottom": "20px"})
    ]),

    # Main wrapper (sidebar + content)
    html.Div([
        # Sidebar filters
        html.Div([
            html.H4("🔍 Filters", style={"color": "#333", "marginBottom": "15px"}),

            html.Label("📅 Date Range"),
            dcc.DatePickerRange(
                id="date-range",
                start_date=df["InvoiceDate"].min().date(),
                end_date=df["InvoiceDate"].max().date(),
                display_format="YYYY-MM-DD"
            ),
            html.Br(), html.Br(),

            html.Label("🌍 Country"),
            dcc.Dropdown(
                id="country-filter",
                options=[{"label": c, "value": c} for c in sorted(df["Country"].dropna().unique())],
                multi=True,
                placeholder="Select countries (leave empty = all)"
            ),
            html.Br(),

            html.Label("⭐ Customer Type"),
            dcc.RadioItems(
                id="customer-type",
                options=[
                    {"label": "All", "value": "all"},
                    {"label": "High-Value Only", "value": "yes"},
                    {"label": "Regular Only", "value": "no"},
                ],
                value="all",
                labelStyle={"display": "block"}
            ),
            html.Br(),

            html.Label("🏆 Top N Products"),
            dcc.Slider(
                id="top-n",
                min=5, max=50, step=5, value=10,
                marks={i: str(i) for i in [5, 10, 20, 30, 40, 50]}
            ),
        ], style={
            "background": "#f8f9fa",
            "padding": "18px",
            "width": "22%",
            "borderRadius": "8px",
            "boxShadow": "0 1px 4px rgba(0,0,0,0.1)",
            "position": "fixed",
            "top": "120px",
            "bottom": "20px",
            "overflowY": "auto"
        }),

        # Main content
        html.Div([
            html.Div(id="kpi-row", style={"display": "flex", "gap": "10px"}),

            html.Div([
                dcc.Graph(id="sales-trend"),
            ], style={"marginTop": "20px"}),

            html.Div([
                dcc.Graph(id="top-products", style={"width": "49%", "display": "inline-block"}),
                dcc.Graph(id="sales-by-country", style={"width": "49%", "display": "inline-block"}),
            ], style={"marginTop": "20px"}),

            html.Div([
                dcc.Graph(id="customer-segment"),
            ], style={"marginTop": "20px"}),

            html.Hr(),
            html.H4("📋 Sample Transactions", style={"marginTop": "10px"}),
            html.Div(id="sample-table", style={"overflowX": "auto"}),
            html.Div(style={"height": "20px"})
        ], style={
            "marginLeft": "25%",
            "padding": "10px 25px",
            "maxWidth": "1100px",
            "fontFamily": "Segoe UI, sans-serif"
        })
    ])
], style={"fontFamily": "Segoe UI, sans-serif", "padding": "20px", "background": "#f6f7fb"})


# Aggregate by frequency
def aggregate_sales(df, freq="W"):
    if freq == "D":
        group = df.groupby("OrderDate").agg(Revenue=("TotalPrice", "sum"))
        group.index.name = "Date"
    elif freq == "M":
        group = df.groupby("OrderMonth").agg(Revenue=("TotalPrice", "sum"))
        group.index.name = "Date"
    else:
        group = df.groupby("OrderWeek").agg(Revenue=("TotalPrice", "sum"))
        group.index.name = "Date"
    return group.reset_index()


# Callbacks

@app.callback(
    Output("kpi-row", "children"),
    Output("sales-trend", "figure"),
    Output("top-products", "figure"),
    Output("sales-by-country", "figure"),
    Output("customer-segment", "figure"),
    Output("sample-table", "children"),
    Input("date-range", "start_date"),
    Input("date-range", "end_date"),
    Input("country-filter", "value"),
    Input("customer-type", "value"),
    Input("top-n", "value")
)
def update_dashboard(start_date, end_date, countries, cust_type, top_n):
    dff = df.copy()
    dff = dff[(dff["InvoiceDate"] >= pd.to_datetime(start_date)) &
              (dff["InvoiceDate"] <= pd.to_datetime(end_date))]

    if countries:
        dff = dff[dff["Country"].isin(countries)]

    if cust_type == "yes":
        dff = dff[dff["HighValueCustomer"].str.lower() == "yes"]
    elif cust_type == "no":
        dff = dff[dff["HighValueCustomer"].str.lower() == "no"]

    # KPIs
    total_rev = dff["TotalPrice"].sum()
    total_orders = dff["InvoiceNo"].nunique()
    total_customers = dff["CustomerID"].nunique()

    def kpi_card(label, value, color):
        return html.Div([
            html.Div(label, style={"fontSize": "12px", "color": "#666"}),
            html.Div(value, style={"fontSize": "20px", "fontWeight": "700", "color": color})
        ], style={"background": "#fff", "padding": "12px", "borderRadius": "6px",
                  "boxShadow": "0 1px 4px rgba(0,0,0,0.06)", "width": "32%"})

    kpis = [
        kpi_card("Total Revenue", f"${total_rev:,.0f}", "#007bff"),
        kpi_card("Unique Orders", f"{total_orders:,}", "#28a745"),
        kpi_card("Unique Customers", f"{total_customers:,}", "#ff5733")
    ]

    # Sales trend
    ts = aggregate_sales(dff, "W")
    fig_ts = px.line(ts, x="Date", y="Revenue", markers=True, title="Revenue Trend (Weekly)")
    fig_ts.update_layout(plot_bgcolor="white", hovermode="x unified")

    # Top products
    top = dff.groupby("Description").agg(Revenue=("TotalPrice", "sum")).reset_index()
    top = top.sort_values("Revenue", ascending=False).head(top_n)
    fig_top = px.bar(top, x="Revenue", y="Description", orientation="h",
                     title=f"Top {top_n} Products by Revenue")
    fig_top.update_layout(yaxis={"categoryorder": "total ascending"}, plot_bgcolor="white")

    # Sales by country
    region = dff.groupby("Country").agg(Revenue=("TotalPrice", "sum")).reset_index()
    region = region.sort_values("Revenue", ascending=False).head(15)
    fig_region = px.bar(region, x="Country", y="Revenue", title="Revenue by Country")
    fig_region.update_layout(plot_bgcolor="white")

    # High-value vs regular
    seg = dff.groupby("HighValueCustomer").agg(Revenue=("TotalPrice", "sum")).reset_index()
    seg["HighValueCustomer"] = seg["HighValueCustomer"].fillna("Unknown")
    fig_seg = px.pie(seg, names="HighValueCustomer", values="Revenue",
                     title="Revenue by Customer Type")

    # Sample table
    sample = dff.sort_values("InvoiceDate", ascending=False).head(10)
    header = [html.Th(col) for col in sample.columns]
    rows = [html.Tr([html.Td(sample.iloc[i][c]) for c in sample.columns]) for i in range(len(sample))]
    table = html.Table([html.Tr(header)] + rows,
                       style={"width": "100%", "borderCollapse": "collapse", "fontSize": "12px"})

    return kpis, fig_ts, fig_top, fig_region, fig_seg, table


# Run server
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=False)
