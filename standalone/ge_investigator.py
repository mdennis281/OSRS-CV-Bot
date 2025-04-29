# app.py
import gradio as gr
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
from PIL import Image
from functools import lru_cache

# — API endpoints —
JAGEX_BASE = "https://secure.runescape.com/m=itemdb_oldschool/api"
GLOOP_HIST = "https://api.weirdgloop.org/exchange/history/osrs/all"
GLOOP_BULK = "https://chisel.weirdgloop.org/gazproj/gazbot/os_dump.json"

# — Helpers with caching & timeouts —
@lru_cache(maxsize=512)
def fetch_jagex_detail(item_id):
    try:
        r = requests.get(f"{JAGEX_BASE}/catalogue/detail.json",
            params={"item": item_id}, timeout=5)
        r.raise_for_status()
        return r.json().get("item", {})
    except:
        return {}

@lru_cache(maxsize=512)
def fetch_jagex_graph(item_id):
    try:
        r = requests.get(f"{JAGEX_BASE}/graph/{item_id}.json", timeout=5)
        r.raise_for_status()
        return r.json().get("daily", {})
    except:
        return {}

@lru_cache(maxsize=128)
def fetch_gloop_history(item_id):
    try:
        r = requests.get(GLOOP_HIST, params={"id": item_id}, timeout=5)
        r.raise_for_status()
        return r.json().get(str(item_id), [])
    except:
        return []

def fetch_gloop_bulk():
    try:
        r = requests.get(GLOOP_BULK, timeout=10)
        r.raise_for_status()
        data = r.json()
        return {k: v for k, v in data.items() if k.isdigit()}
    except:
        return {}

GLOOP_BULK_DATA = fetch_gloop_bulk()

# Build initial ITEMS_DF with empty slots for our new columns
NAME_TO_ID = {
    meta["name"]: int(k)
    for k, meta in GLOOP_BULK_DATA.items()
    if isinstance(meta.get("name"), str)
}
ITEMS_DF = pd.DataFrame([
    {"ID": v, "Name": k, "Icon": None, "Current Price": "", "High Alch": ""}
    for k, v in NAME_TO_ID.items()
])

def on_select(df: pd.DataFrame, evt: gr.SelectData):
    # Which row did the user click?
    row = evt.index[0]
    item_id = df.iloc[row]["ID"]

    # Fetch detail & bulk data
    detail = fetch_jagex_detail(item_id)
    bulk   = GLOOP_BULK_DATA.get(str(item_id), {})

    # Load icon image
    icon = None
    try:
        icon = Image.open(BytesIO(
            requests.get(detail.get("icon",""), timeout=5).content
        ))
    except:
        pass

    # Update the DataFrame copy
    df = df.copy()
    df.at[row, "Icon"] = icon
    df.at[row, "Current Price"] = detail.get("current", {}).get("price", "")
    df.at[row, "High Alch"]     = bulk.get("highalch", "")

    # Rebuild charts (as before)
    graph   = fetch_jagex_graph(item_id)
    history = fetch_gloop_history(item_id)

    # Jagex price history
    fig_price = None
    times  = [pd.to_datetime(int(ts), unit="ms") for ts in graph.keys()]
    prices = list(graph.values())
    if times:
        fig_price = px.line(
            x=times, y=prices,
            labels={"x":"Date","y":"Price"},
            title="Jagex Historical Price",
            template="plotly_dark"
        )

    # Weird Gloop price + volume
    fig_hist = fig_vol = None
    if history:
        hdf = pd.DataFrame(history)
        hdf["timestamp"] = pd.to_datetime(hdf["timestamp"], unit="ms")
        fig_hist = px.line(
            hdf, x="timestamp", y="price",
            labels={"timestamp":"Date","price":"Price"},
            title="Weird Gloop Price History",
            template="plotly_dark"
        )
        if "volume" in hdf.columns:
            fig_vol = px.area(
                hdf, x="timestamp", y="volume",
                labels={"timestamp":"Date","volume":"Volume"},
                title="Weird Gloop Volume History",
                template="plotly_dark"
            )
            fig_vol.update_traces(opacity=0.8)

    # 7‑day rolling high/low
    fig_range = None
    if times:
        dfg = pd.DataFrame({"timestamp": times, "price": prices})
        dfg.set_index("timestamp", inplace=True)
        dfg.sort_index(inplace=True)
        dfg["min7"] = dfg["price"].rolling(7, min_periods=1).min()
        dfg["max7"] = dfg["price"].rolling(7, min_periods=1).max()
        fig_range = go.Figure()
        fig_range.add_trace(go.Scatter(x=dfg.index, y=dfg["min7"], name="7‑day Low"))
        fig_range.add_trace(go.Scatter(x=dfg.index, y=dfg["max7"], name="7‑day High"))
        fig_range.update_layout(
            title="7‑day Rolling Price Range",
            template="plotly_dark",
            xaxis_title="Date",
            yaxis_title="Price"
        )

    # Return updated table + all charts
    return df, fig_price, fig_hist, fig_vol, fig_range

with gr.Blocks(theme=gr.themes.Ocean()) as demo:
    gr.Markdown("## OSRS Grand Exchange Market Explorer")

    items_table = gr.Dataframe(
        value=ITEMS_DF,
        headers=["ID","Name","Icon","Current Price","High Alch"],
        label="Searchable Item List",
        interactive=False,         # display‑only
        show_fullscreen_button=True,
        show_search='search'
    )

    price_plot  = gr.Plot(label="Jagex Price Graph")
    hist_plot   = gr.Plot(label="Weird Gloop Price History")
    vol_plot    = gr.Plot(label="Weird Gloop Volume History")
    range_plot  = gr.Plot(label="7‑day Rolling Price Range")

    # Wire up row‑click to update OUR DataFrame and charts :contentReference[oaicite:1]{index=1}
    items_table.select(
        fn=on_select,
        inputs=[items_table],
        outputs=[items_table, price_plot, hist_plot, vol_plot, range_plot]
    )

if __name__ == "__main__":
    demo.launch()
