import tkinter as tk
from tkinter import ttk
import websocket
import json
import threading
import chart as c

class CryptoTicker:
    """Reusable ticker component for any cryptocurrency."""
    
    def __init__(self, parent, symbol, display_name):
        self.parent = parent
        self.symbol = symbol.lower()
        self.display_name = display_name
        self.is_active = False
        self.ws = None
        
        # Create UI
        self.frame = ttk.Frame(parent, relief="solid", borderwidth=1, padding=15, height=97)
        
        # Title
        ttk.Label(self.frame, text=display_name, 
                 font=("Arial", 13, "bold")).pack()
        
        # Price
        self.price_label = tk.Label(self.frame, text="--,---", 
                                    font=("Arial", 12, "bold"))
        self.price_label.pack(pady=10)
        
        # Change
        self.change_label = ttk.Label(self.frame, text="--", 
                                      font=("Arial", 10))
        self.change_label.pack()
    
    def start(self):
        """Start WebSocket connection."""
        if self.is_active:
            return
        
        self.is_active = True
        ws_url = f"wss://stream.binance.com:9443/ws/{self.symbol}@ticker"
        
        self.ws = websocket.WebSocketApp(
            ws_url,
            on_message=self.on_message,
            on_error=lambda ws, err: print(f"{self.symbol} error: {err}"),
            on_close=lambda ws, s, m: print(f"{self.symbol} closed"),
            on_open=lambda ws: print(f"{self.symbol} connected")
        )
        
        threading.Thread(target=self.ws.run_forever, daemon=True).start()
    
    def stop(self):
        """Stop WebSocket connection."""
        self.is_active = False
        if self.ws:
            self.ws.close()
            self.ws = None
    
    def on_message(self, ws, message):
        """Handle price updates."""
        if not self.is_active:
            return
        
        data = json.loads(message)
        price = float(data['c'])
        change = float(data['p'])
        percent = float(data['P'])
        
        # Schedule GUI update on main thread
        self.parent.after(0, self.update_display, price, change, percent)
    
    def update_display(self, price, change, percent):
        """Update the ticker display."""
        if not self.is_active:
            return
        
        color = "green" if change >= 0 else "red"
        self.price_label.config(text=f"{price:,.2f}", fg=color)
        
        sign = "+" if change >= 0 else ""
        self.change_label.config(
            text=f"{sign}{change:,.2f} ({sign}{percent:.2f}%)",
            foreground=color
        )
    
    def pack(self, **kwargs):
        """Allow easy placement of ticker."""
        self.frame.pack(**kwargs)
    
    def pack_forget(self):
        """Hide the ticker."""
        self.frame.pack_forget()
    
    def on_closing(self):
        """Clean up when closing."""
        self.btc_ticker.stop()
        self.eth_ticker.stop()
        self.sol_ticker.stop()
        self.root.destroy()


class BinanceDashboardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Crypto Dashboard with Toggle")
        self.root.configure(bg="#3B3B3B")
        self.root.geometry("750x550")

        self.bg_style = ttk.Style()
        self.bg_style.configure("BGC.TFrame", background="#3b3b3b")

        self.title_style = ttk.Style()
        self.title_style.configure("T.TFrame", background="#252525")
        self.title_frame = ttk.Frame(root, style="T.TFrame")
        self.title_frame.pack(side="top",fill="x")

        self.label_style = ttk.Style()
        self.label_style.configure("L.TLabel", background="#252525", foreground="#AC84F2")
        
        self.label = ttk.Label(self.title_frame, text="Binance Real-Time Dashboard", padding=10, font=("Arial", 15, "bold"), style="L.TLabel")
        self.label.pack(side="left", fill="x")

        self.top_frame = ttk.Frame(root, style="BGC.TFrame")
        self.top_frame.pack(anchor="nw",side="top", fill="x", padx=10)

        self.button_frame_style = ttk.Style()
        self.button_frame_style.configure("Button.TFrame", background="#A2A2A2")

        self.button_frame = ttk.Frame(self.top_frame, padding=10, height=97, style="Button.TFrame")
        self.button_frame.pack(side="left")
        
        self.button_style = ttk.Style()
        self.button_style.configure("Button.TButton", font=("Arial", 10, "bold"), background="#A2A2A2", foreground="#74299C")

        self.sol_btn = ttk.Button(
            self.button_frame, 
            text="Show SOL/USDT",
            command=self.toggle_sol,
            style="Button.TButton"
        )
        self.sol_btn.pack(side="top", padx=5, pady=5, fill="both", expand=True)

        self.graph_btn = ttk.Button(
            self.button_frame, 
            text="Show Graph",
            command=self.toggle_graph,
            style="Button.TButton"
        )
        self.graph_btn.pack(side="bottom", padx=5, pady=5, fill="both", expand=True)

        self.ticker_frame = ttk.Frame(self.top_frame, padding=10, style="BGC.TFrame")
        self.ticker_frame.pack(anchor="n",fill="x", expand=True)

        # Create tickers
        self.btc_ticker = CryptoTicker(self.ticker_frame, "btcusdt", "BTC/USDT")
        self.btc_ticker.pack(side="left", padx=10, expand=True,fill="both")
        
        self.eth_ticker = CryptoTicker(self.ticker_frame, "ethusdt", "ETH/USDT")
        self.eth_ticker.pack(side="left", padx=10, expand=True,fill="both")
        
        self.sol_ticker = CryptoTicker(self.ticker_frame, "solusdt", "SOL/USDT")

        self.graph_frame = ttk.Frame(root, style="BGC.TFrame")
        self.graph_frame.pack(fill="both",  expand=True, padx=20, pady=20)
        self.graph_visible = True

        self.chart_panel = c.ChartPanel(self.graph_frame, "BTCUSDT", "1m")
        self.chart_panel.pack(fill=tk.BOTH, expand=True)
        
        # Start BTC and ETH
        self.btc_ticker.start()
        self.eth_ticker.start()
        
        self.sol_visible = False

    def toggle_graph(self):
        if self.graph_visible:
            # Hide Chart
            self.graph_frame.pack_forget()
            self.graph_btn.config(text="Show Chart")
            self.graph_visible = False
        else:
            # Show Chart
            self.graph_frame.pack(fill="both",  expand=True, padx=20, pady=20)
            self.graph_btn.config(text="Hide Chart")
            self.graph_visible = True
    
    def toggle_sol(self):
        """Show or hide SOL ticker."""
        if self.sol_visible:
            # Hide SOL
            self.sol_ticker.stop()
            self.sol_ticker.pack_forget()
            self.sol_btn.config(text="Show SOL/USDT")
            self.sol_visible = False
        else:
            # Show SOL
            self.sol_ticker.pack(side="left", padx=10, expand=True,fill="both")
            self.sol_ticker.start()
            self.sol_btn.config(text="Hide SOL/USDT")
            self.sol_visible = True
    
    def on_closing(self):
        """Clean up when closing."""
        self.btc_ticker.stop()
        self.eth_ticker.stop()
        self.sol_ticker.stop()
        self.chart_panel.stop()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = BinanceDashboardApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()