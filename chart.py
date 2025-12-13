
import tkinter as tk
from tkinter import ttk
import requests
import json
import threading
import time
from collections import deque
import numpy as np

# Matplotlib Imports
import matplotlib
matplotlib.use("TkAgg") # Use Tkinter backend for Matplotlib
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import mpl_finance as mpf  # Use the alias for candlestick plotting
import matplotlib.pyplot as plt # <--- EXPLICITLY IMPORT plt

# WebSocket Import
import websocket # <--- EXPLICITLY IMPORT websocket

# --- Configuration ---
SYMBOL = "BTCUSDT"
INTERVAL = "1m"
CHART_LOOKBACK_MINUTES = 60 

# --- REST API Helper (Remains the same) ---
def fetch_klines(symbol, interval, limit):
    """Fetches historical candlestick (Kline) data via REST API."""
    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": symbol.upper(),
        "interval": interval,
        "limit": limit
    }
    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        # Format data: (Timestamp, O, H, L, C, V)
        formatted_data = []
        for candle in data:
            formatted_data.append((
                candle[0],        # 0: Open time (Timestamp in ms)
                float(candle[1]), # 1: Open
                float(candle[2]), # 2: High
                float(candle[3]), # 3: Low
                float(candle[4]), # 4: Close
                float(candle[5]), # 5: Volume
            ))
        return formatted_data
    except Exception as e:
        print(f"Error fetching klines for {symbol}: {e}")
        return []

# --- Chart Panel Class ---

class ChartPanel(ttk.Frame):
    """A Matplotlib chart component for real-time candlestick and volume data."""

    def __init__(self, parent, symbol, interval):
        self.bg_style = ttk.Style()
        self.bg_style.configure("BGC.TFrame", background="#3b3b3b")
        super().__init__(parent, padding=5, style="BGC.TFrame")
        self.symbol = symbol.upper()
        self.interval = interval
        self.is_active = False
        self.ws = None
        self.data = deque(maxlen=60)
        
        self.setup_ui()
        self.load_initial_data()
    
    def setup_ui(self):
        # 1. Create Matplotlib Figure with two subplots (axes)
        self.fig = Figure(figsize=(10, 6), dpi=100, facecolor="#252525", edgecolor='#5F747E', linewidth=2)
        
        # 1.1 Candlestick Plot (Primary)
        self.ax_price = self.fig.add_subplot(2, 1, 1, 
            title=f"{self.symbol} Real-Time {self.interval} (Binance)",
            sharex=self.fig.add_subplot(2, 1, 2, frame_on=False) 
        )
        # FIX: Use plt.setp for setting axis properties
        plt.setp(self.ax_price.get_xticklabels(), visible=False) 
        self.ax_price.grid(True, linestyle=':', alpha=0.5)
        
        # 1.2 Volume Plot (Secondary)
        self.ax_volume = self.fig.add_subplot(2, 1, 2, sharex=self.ax_price)
        self.ax_volume.set_ylabel(f"Volume ({self.symbol.replace('USDT', '')})")
        self.ax_volume.grid(True, linestyle=':', alpha=0.5)
        
        self.fig.tight_layout(h_pad=0.5)
        
        # 2. Embed Figure into Tkinter Canvas
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        # 3. Add Navigation Toolbar
        self.toolbar = NavigationToolbar2Tk(self.canvas, self)
        self.toolbar.update()
        self.toolbar.pack(side=tk.BOTTOM, fill=tk.X)


    # --- Data Handling & Plotting Methods ---

    def load_initial_data(self):
        # ... (unchanged)
        def run_fetch():
            klines = fetch_klines(self.symbol, self.interval, self.data.maxlen)
            if klines:
                self.data.extend(klines)
                self.master.after(0, self.draw_chart)
                self.master.after(100, self.start_websocket) 
        
        threading.Thread(target=run_fetch, daemon=True).start()

    def start_websocket(self):
        """Start WebSocket for live kline updates."""
        if self.is_active: return

        self.is_active = True
        ws_url = f"wss://stream.binance.com:9443/ws/{self.symbol.lower()}@kline_{self.interval}"
        
        # FIX: The websocket library is called directly here.
        self.ws = websocket.WebSocketApp(
            ws_url,
            on_message=self.on_message,
            on_error=lambda ws, err: print(f"Chart WS Error: {err}"),
            on_close=lambda ws, s, m: print(f"Chart WS Closed: {self.symbol}"),
            on_open=lambda ws: print(f"Chart WS Connected: {self.symbol}")
        )
        threading.Thread(target=self.ws.run_forever, daemon=True).start()

    def stop(self):
        # ... (unchanged)
        self.is_active = False
        if self.ws:
            self.ws.close()
            self.ws = None

    def on_message(self, ws, message):
        # ... (unchanged)
        if not self.is_active: return
        
        data = json.loads(message)
        kline = data['k']
        
        new_candle = (
            kline['t'],        # 0: Open time
            float(kline['o']), # 1: Open
            float(kline['h']), # 2: High
            float(kline['l']), # 3: Low
            float(kline['c']), # 4: Close
            float(kline['v'])  # 5: Volume
        )
        
        if self.data and kline['t'] == self.data[-1][0]:
            self.data[-1] = new_candle
        else:
            self.data.append(new_candle)

        self.master.after(0, self.draw_chart)

    def draw_chart(self):
        #Clears axes, redraws candlestick and volume plots, and formats axes.
        if not self.is_active or not self.data: return
            
        # 1. Clear previous content
        self.ax_price.clear()
        self.ax_volume.clear()
        
        # 2. Prepare Data (same as before)
        ohlc_data = np.array([candle[1:5] for candle in self.data]) 
        volumes = np.array([candle[5] for candle in self.data])
        indexes = np.arange(len(ohlc_data))
        colors = np.where(ohlc_data[:, 3] >= ohlc_data[:, 0], 'g', 'r') 

        # 3. Plot Candlestick (same as before)
        self.ax_price.set_title(f"{self.symbol} Real-Time {self.interval} (Binance)", color="#D88EFF", fontweight="bold")
        
        mpf.candlestick_ohlc(
            self.ax_price, 
            np.hstack((indexes[:, np.newaxis], ohlc_data)), 
            width=0.6, 
            colorup='g', 
            colordown='r', 
            alpha=0.8
        )
        self.ax_price.set_facecolor("#191919")
        self.ax_price.grid(True, linestyle=':', alpha=0.5, color="#5F747E")
        self.ax_price.tick_params(axis='y', labelcolor='white')
        self.ax_price.autoscale_view()
        
        # 4. Plot Volume Bar Chart (same as before)
        self.ax_volume.set_facecolor("#191919")
        self.ax_volume.set_ylabel(f"Volume ({self.symbol.replace('USDT', '')})", color="#D88EFF", fontweight="bold")
        self.ax_volume.bar(indexes, volumes, color=colors, width=0.8, alpha=0.8)
        self.ax_volume.grid(True, linestyle=':', alpha=0.5, color="#5F747E")
        self.ax_volume.tick_params(axis='y', labelcolor='white')
        self.ax_volume.autoscale_view()

        # 5. X-Axis Formatting (Time) - MODIFIED FOR BETTER SPACING
        all_timestamps_ms = np.array([candle[0] for candle in self.data])
        
        # 5a. Increased Step: Only label every Nth tick for maximum readability
        step = max(1, len(all_timestamps_ms) // 10) # Label every 10th candle
        x_ticks = indexes[::step]
        
        # Convert milliseconds timestamp to HH:MM format
        x_labels = [time.strftime("%H:%M", time.localtime(ts / 1000)) for ts in all_timestamps_ms[::step]]
        
        self.ax_volume.set_xticks(x_ticks)
        
        # 5b. Aggressive Rotation: 45-degree angle prevents horizontal overlap
        self.ax_volume.set_xticklabels(x_labels, rotation=45, ha='right', color="#D88EFF") 
        self.ax_volume.set_xlabel("Time", color="#D88EFF", fontweight="bold")

        # 6. Redraw the canvas - FIXES FOR OVERLAP
        
        # 6a. Explicitly use Matplotlib's date formatter utility 
        # This often helps the backend handle date/time formatting better, even with indices
        self.fig.autofmt_xdate(rotation=45) 
        
        # 6b. Adjust tight_layout with a vertical padding increase (h_pad) 
        # to ensure Y-axis labels and titles have space.
        self.fig.tight_layout(h_pad=1.0, pad=1.5) 
        
        self.canvas.draw()