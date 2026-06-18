import customtkinter as ctk
import threading
import tkinter as tk
import tkinter.messagebox as messagebox
from tkinter import ttk

import database
import analysis
import llm_helper
import suggest

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# UIの基本設定
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class SuggestManager:
    def __init__(self, parent, sym_entry, sym_var, name_entry, name_var):
        self.parent = parent
        self.sym_entry = sym_entry
        self.sym_var = sym_var
        self.name_entry = name_entry
        self.name_var = name_var
        self.popup = None
        self.listbox = None
        self.timer = None
        self.results = []
        self.ignore_trace = False
        self.active_entry = None
        
        self.sym_var.trace_add("write", lambda *a: self.on_text_change(self.sym_entry, self.sym_var))
        self.name_var.trace_add("write", lambda *a: self.on_text_change(self.name_entry, self.name_var))
        
        self.sym_entry.bind("<FocusOut>", self.on_focus_out)
        self.name_entry.bind("<FocusOut>", self.on_focus_out)
        
    def on_text_change(self, entry, var):
        if self.ignore_trace:
            return
        self.active_entry = entry
        if self.timer:
            self.parent.after_cancel(self.timer)
        self.timer = self.parent.after(400, lambda: self.fetch_suggestions(var))
        
    def fetch_suggestions(self, var):
        query = var.get()
        if not query:
            self.hide_popup()
            return
            
        threading.Thread(target=self._fetch_thread, args=(query,), daemon=True).start()
        
    def _fetch_thread(self, query):
        results = suggest.get_suggestions(query)
        self.parent.after(0, self.show_popup, results)
        
    def show_popup(self, results):
        if not results:
            self.hide_popup()
            return
            
        if not getattr(self, 'popup', None) or not self.popup.winfo_exists():
            self.popup = tk.Toplevel(self.parent)
            self.popup.wm_overrideredirect(True)
            self.popup.attributes("-topmost", True)
            
            self.listbox = tk.Listbox(self.popup, font=("Arial", 12),
                                      bg="#2b2b2b", fg="white", selectbackground="#1f538d", borderwidth=1, relief="solid")
            self.listbox.pack(fill="both", expand=True)
            self.listbox.bind("<<ListboxSelect>>", self.on_select)
            
        self.listbox.delete(0, tk.END)
        self.results = results
        for code, name in results:
            self.listbox.insert(tk.END, f"{code} - {name}")
            
        # Place relative to active screen
        if not self.active_entry:
            self.active_entry = self.sym_entry
            
        x = self.active_entry.winfo_rootx()
        y = self.active_entry.winfo_rooty() + self.active_entry.winfo_height()
        
        h = min(len(results), 8) * 22 + 4
        self.popup.geometry(f"300x{h}+{x}+{y}")
        self.popup.deiconify()
        self.popup.lift()
        
    def hide_popup(self, event=None):
        if getattr(self, 'popup', None) and self.popup.winfo_exists():
            self.popup.withdraw()
            
    def on_focus_out(self, event):
        self.parent.after(200, self.hide_popup)
        
    def on_select(self, event):
        if not self.listbox.curselection():
            return
        idx = self.listbox.curselection()[0]
        code, name = self.results[idx]
        
        self.ignore_trace = True
        self.sym_var.set(code)
        self.name_var.set(name)
        
        self.hide_popup()
        self.parent.after(500, lambda: setattr(self, 'ignore_trace', False))

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Antikabu - 株式投資補助ツール")
        self.geometry("900x700")

        # タブの作成
        self.tabview = ctk.CTkTabview(self, width=860, height=660)
        self.tabview.pack(padx=20, pady=20, fill="both", expand=True)

        self.tab_watchlist = self.tabview.add("Watchlist")
        self.tab_portfolio = self.tabview.add("Portfolio")
        self.tab_settings = self.tabview.add("Settings")

        # 各タブの初期化
        self.init_settings_tab()
        self.init_watchlist_tab()
        self.init_portfolio_tab()

    # --- Settings Tab ---
    def init_settings_tab(self):
        label = ctk.CTkLabel(self.tab_settings, text="API設定", font=ctk.CTkFont(size=20, weight="bold"))
        label.pack(pady=20)

        self.api_key_entry = ctk.CTkEntry(self.tab_settings, width=400, placeholder_text="Gemini API Key を入力してください", show="*")
        self.api_key_entry.pack(pady=10)
        
        # 既存のキーをロード
        saved_key = database.get_setting("GEMINI_API_KEY", "")
        if saved_key:
            self.api_key_entry.insert(0, saved_key)

        save_btn = ctk.CTkButton(self.tab_settings, text="保存", command=self.save_settings)
        save_btn.pack(pady=20)

        info_label = ctk.CTkLabel(self.tab_settings, text="※分析には Google Gemini API キーが必要です。\n日本株を取得する場合、シンボルの末尾に .T をつけてください（例: トヨタなら 7203.T）", text_color="gray")
        info_label.pack(pady=20)

    def save_settings(self):
        api_key = self.api_key_entry.get().strip()
        database.set_setting("GEMINI_API_KEY", api_key)
        messagebox.showinfo("保存完了", "設定を保存しました。")

    # --- Watchlist Tab ---
    def init_watchlist_tab(self):
        self.wl_left = ctk.CTkFrame(self.tab_watchlist, width=300)
        self.wl_left.pack(side="left", fill="y", padx=10, pady=10)
        
        self.wl_right = ctk.CTkFrame(self.tab_watchlist)
        self.wl_right.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        # 追加フォーム
        add_frame = ctk.CTkFrame(self.wl_left)
        add_frame.pack(fill="x", pady=(0, 10))
        
        self.wl_sym_var = tk.StringVar()
        self.wl_name_var = tk.StringVar()
        
        self.wl_symbol_entry = ctk.CTkEntry(add_frame, placeholder_text="株価コード (例: 7203.T)", width=120, textvariable=self.wl_sym_var)
        self.wl_symbol_entry.grid(row=0, column=0, padx=5, pady=5)
        
        self.wl_name_entry = ctk.CTkEntry(add_frame, placeholder_text="株式名", width=120, textvariable=self.wl_name_var)
        self.wl_name_entry.grid(row=0, column=1, padx=5, pady=5)
        
        wl_add_btn = ctk.CTkButton(add_frame, text="追加", width=60, command=self.add_to_watchlist)
        wl_add_btn.grid(row=0, column=2, padx=5, pady=5)

        # サジェスト機能の紐付け
        self.wl_suggest = SuggestManager(self, self.wl_symbol_entry, self.wl_sym_var, self.wl_name_entry, self.wl_name_var)

        # ツリービュー (銘柄リスト)
        columns = ("symbol", "name")
        self.wl_tree = ttk.Treeview(self.wl_left, columns=columns, show="headings", height=15)
        self.wl_tree.heading("symbol", text="株価コード")
        self.wl_tree.heading("name", text="株式名")
        self.wl_tree.column("symbol", width=100)
        self.wl_tree.column("name", width=150)
        self.wl_tree.pack(fill="both", expand=True)

        btn_frame = ctk.CTkFrame(self.wl_left)
        btn_frame.pack(fill="x", pady=10)
        
        wl_del_btn = ctk.CTkButton(btn_frame, text="削除", command=self.delete_from_watchlist)
        wl_del_btn.pack(side="left", padx=5, expand=True)
        
        wl_analyze_btn = ctk.CTkButton(btn_frame, text="分析実行", command=self.analyze_watchlist_item)
        wl_analyze_btn.pack(side="right", padx=5, expand=True)

        # チャート用フレーム（上部）とテキスト用フレーム（下部）に分割
        self.wl_chart_frame = ctk.CTkFrame(self.wl_right, height=250)
        self.wl_chart_frame.pack(fill="x", padx=5, pady=(5, 0))
        self.wl_chart_frame.pack_propagate(False) # 高さを固定
        
        self.wl_text_frame = ctk.CTkFrame(self.wl_right)
        self.wl_text_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # 分析結果テキストボックス
        self.wl_result_text = ctk.CTkTextbox(self.wl_text_frame, wrap="word", font=ctk.CTkFont(size=14))
        self.wl_result_text.pack(fill="both", expand=True)

        self.refresh_watchlist()

    def refresh_watchlist(self):
        for item in self.wl_tree.get_children():
            self.wl_tree.delete(item)
        for row in database.get_watchlist():
            self.wl_tree.insert("", "end", values=(row["symbol"], row["name"]))

    def add_to_watchlist(self):
        sym = self.wl_symbol_entry.get().strip()
        name = self.wl_name_entry.get().strip()
        if sym:
            database.add_to_watchlist(sym, name)
            self.wl_symbol_entry.delete(0, "end")
            self.wl_name_entry.delete(0, "end")
            self.refresh_watchlist()

    def delete_from_watchlist(self):
        selected = self.wl_tree.selection()
        if selected:
            item = self.wl_tree.item(selected[0])
            sym = item['values'][0]
            database.remove_from_watchlist(sym)
            self.refresh_watchlist()

    def analyze_watchlist_item(self):
        selected = self.wl_tree.selection()
        if not selected:
            messagebox.showwarning("選択エラー", "分析する銘柄を選択してください。")
            return
            
        item = self.wl_tree.item(selected[0])
        sym = item['values'][0]
        name = item['values'][1]

        self.wl_result_text.delete("1.0", "end")
        self.wl_result_text.insert("end", f"[{sym}] のデータを取得中...\n")

        threading.Thread(target=self._analyze_thread, args=(sym, name), daemon=True).start()

    def _render_charts(self, df):
        # 既存のチャートがあれば削除
        for widget in self.wl_chart_frame.winfo_children():
            widget.destroy()
            
        fig = Figure(figsize=(8, 2.5), dpi=100)
        fig.patch.set_facecolor('#2b2b2b') # ダークテーマに合わせる
        
        # 左：2年チャート
        ax1 = fig.add_subplot(121)
        ax1.plot(df.index, df['Close'], color='#1f538d', label='Close')
        if 'SMA_25' in df.columns:
            ax1.plot(df.index, df['SMA_25'], color='#d97726', linewidth=1, label='SMA 25')
        if 'SMA_50' in df.columns:
            ax1.plot(df.index, df['SMA_50'], color='#26d977', linewidth=1, label='SMA 50')
        ax1.set_title("2 Years", color='white')
        ax1.tick_params(colors='white', labelsize=8)
        ax1.set_facecolor('#2b2b2b')
        ax1.grid(color='#444444')
        ax1.legend(loc='upper left', fontsize=8, facecolor='#2b2b2b', edgecolor='#444444', labelcolor='white')
        
        # 右：1ヶ月チャート (直近22営業日)
        ax2 = fig.add_subplot(122)
        df_1m = df.tail(22)
        if not df_1m.empty:
            ax2.plot(df_1m.index, df_1m['Close'], color='#1f538d', label='Close')
            if 'SMA_25' in df_1m.columns:
                ax2.plot(df_1m.index, df_1m['SMA_25'], color='#d97726', linewidth=1, label='SMA 25')
            if 'SMA_50' in df_1m.columns:
                ax2.plot(df_1m.index, df_1m['SMA_50'], color='#26d977', linewidth=1, label='SMA 50')
        ax2.set_title("1 Month", color='white')
        ax2.tick_params(colors='white', labelsize=8)
        ax2.set_facecolor('#2b2b2b')
        ax2.grid(color='#444444')
        ax2.legend(loc='upper left', fontsize=8, facecolor='#2b2b2b', edgecolor='#444444', labelcolor='white')
        
        fig.autofmt_xdate()
        fig.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, master=self.wl_chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def _analyze_thread(self, sym, name):
        df = analysis.get_stock_data(sym)
        if df is None or df.empty:
            self.after(0, lambda: self.wl_result_text.insert("end", "データが取得できませんでした。\n"))
            return
            
        df = analysis.calculate_technical_indicators(df)
        summary = analysis.get_latest_indicators_summary(df)
        
        self.after(0, lambda: self.wl_result_text.insert("end", "指標の計算完了。チャートを描画・Geminiに分析を依頼中...\n\n"))
        self.after(0, lambda: self._render_charts(df))
        
        llm_result = llm_helper.get_stock_analysis(sym, name, summary)
        
        def update_text():
            self.wl_result_text.insert("end", "="*40 + "\n")
            self.wl_result_text.insert("end", llm_result)
        self.after(0, update_text)

    # --- Portfolio Tab ---
    def init_portfolio_tab(self):
        self.pf_top = ctk.CTkFrame(self.tab_portfolio)
        self.pf_top.pack(fill="x", padx=10, pady=10)
        
        self.pf_bottom = ctk.CTkFrame(self.tab_portfolio)
        self.pf_bottom.pack(fill="both", expand=True, padx=10, pady=10)

        # 追加フォーム
        self.pf_sym_var = tk.StringVar()
        self.pf_name_var = tk.StringVar()
        
        self.pf_sym_entry = ctk.CTkEntry(self.pf_top, placeholder_text="株価コード", textvariable=self.pf_sym_var)
        self.pf_sym_entry.grid(row=0, column=0, padx=5, pady=5)
        
        self.pf_name_entry = ctk.CTkEntry(self.pf_top, placeholder_text="株式名", textvariable=self.pf_name_var)
        self.pf_name_entry.grid(row=0, column=1, padx=5, pady=5)
        
        self.pf_qty_entry = ctk.CTkEntry(self.pf_top, placeholder_text="数量")
        self.pf_qty_entry.grid(row=0, column=2, padx=5, pady=5)
        
        self.pf_cost_entry = ctk.CTkEntry(self.pf_top, placeholder_text="平均取得単価")
        self.pf_cost_entry.grid(row=0, column=3, padx=5, pady=5)
        
        pf_add_btn = ctk.CTkButton(self.pf_top, text="追加/更新", command=self.add_to_portfolio)
        pf_add_btn.grid(row=0, column=4, padx=5, pady=5)

        pf_del_btn = ctk.CTkButton(self.pf_top, text="選択削除", command=self.delete_from_portfolio, fg_color="red", hover_color="darkred")
        pf_del_btn.grid(row=0, column=5, padx=5, pady=5)

        # サジェスト機能の紐付け
        self.pf_suggest = SuggestManager(self, self.pf_sym_entry, self.pf_sym_var, self.pf_name_entry, self.pf_name_var)

        # ツリービュー
        columns = ("symbol", "name", "quantity", "average_cost")
        self.pf_tree = ttk.Treeview(self.pf_bottom, columns=columns, show="headings", height=8)
        self.pf_tree.heading("symbol", text="株価コード")
        self.pf_tree.heading("name", text="株式名")
        self.pf_tree.heading("quantity", text="数量")
        self.pf_tree.heading("average_cost", text="平均取得単価")
        self.pf_tree.pack(fill="x", padx=5, pady=5)

        btn_frame = ctk.CTkFrame(self.pf_bottom)
        btn_frame.pack(fill="x", pady=5)
        
        pf_adv_btn = ctk.CTkButton(btn_frame, text="ポートフォリオ運用アドバイスをもらう", command=self.get_portfolio_advice)
        pf_adv_btn.pack(pady=5)

        self.pf_result_text = ctk.CTkTextbox(self.pf_bottom, wrap="word", font=ctk.CTkFont(size=14))
        self.pf_result_text.pack(fill="both", expand=True, padx=5, pady=5)

        self.refresh_portfolio()

    def refresh_portfolio(self):
        for item in self.pf_tree.get_children():
            self.pf_tree.delete(item)
        for row in database.get_portfolio():
            self.pf_tree.insert("", "end", values=(row["symbol"], row["name"], row["quantity"], row["average_cost"]))

    def add_to_portfolio(self):
        sym = self.pf_sym_entry.get().strip()
        name = self.pf_name_entry.get().strip()
        qty_str = self.pf_qty_entry.get().strip()
        cost_str = self.pf_cost_entry.get().strip()
        
        if not sym or not qty_str or not cost_str:
            messagebox.showwarning("入力エラー", "シンボル、数量、平均取得単価は必須です。")
            return
            
        try:
            qty = float(qty_str)
            cost = float(cost_str)
        except ValueError:
            messagebox.showwarning("入力エラー", "数量と平均取得単価は数値を入力してください。")
            return

        database.add_to_portfolio(sym, name, qty, cost)
        self.pf_sym_entry.delete(0, "end")
        self.pf_name_entry.delete(0, "end")
        self.pf_qty_entry.delete(0, "end")
        self.pf_cost_entry.delete(0, "end")
        self.refresh_portfolio()

    def delete_from_portfolio(self):
        selected = self.pf_tree.selection()
        if selected:
            item = self.pf_tree.item(selected[0])
            sym = item['values'][0]
            database.remove_from_portfolio(sym)
            self.refresh_portfolio()

    def get_portfolio_advice(self):
        items = database.get_portfolio()
        if not items:
            messagebox.showinfo("情報", "ポートフォリオに銘柄がありません。")
            return

        self.pf_result_text.delete("1.0", "end")
        self.pf_result_text.insert("end", "Geminiにポートフォリオの運用アドバイスを依頼中...\n\n")

        threading.Thread(target=self._portfolio_advice_thread, args=(items,), daemon=True).start()

    def _portfolio_advice_thread(self, items):
        llm_result = llm_helper.get_portfolio_advice(items)
        self.pf_result_text.insert("end", "="*40 + "\n")
        self.pf_result_text.insert("end", llm_result)

if __name__ == "__main__":
    app = App()
    app.mainloop()
