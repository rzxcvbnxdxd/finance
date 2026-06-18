import customtkinter as ctk
import tkinter as tk
import threading

def get_suggestions(query):
    return [("7203", "Toyota")] if "7" in query else []

class SuggestPopup:
    def __init__(self, parent, entry, name_entry=None):
        self.parent = parent
        self.entry = entry
        self.name_entry = name_entry
        self.popup = None
        self.listbox = None
        self.timer = None
        self.results = []
        
        self.entry.bind("<KeyRelease>", self.on_key_release)
        self.entry.bind("<FocusOut>", self.on_focus_out)
        
    def on_key_release(self, event):
        if event.keysym in ['Up', 'Down', 'Escape', 'Shift_L', 'Shift_R', 'Control_L', 'Control_R', 'Alt_L', 'Alt_R']:
            return
            
        if self.timer:
            self.parent.after_cancel(self.timer)
        self.timer = self.parent.after(400, self.fetch_suggestions)
        
    def fetch_suggestions(self):
        query = self.entry.get()
        print("fetch_suggestions for:", query)
        if not query:
            self.hide_popup()
            return
            
        threading.Thread(target=self._fetch_thread, args=(query,), daemon=True).start()
        
    def _fetch_thread(self, query):
        results = get_suggestions(query)
        print("results:", results)
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
            
        x = self.entry.winfo_rootx()
        y = self.entry.winfo_rooty() + self.entry.winfo_height()
        
        h = min(len(results), 8) * 22 + 4
        self.popup.geometry(f"300x{h}+{x}+{y}")
        self.popup.deiconify()
        self.popup.lift()
        print("popup shown at", x, y)
        
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
        
        self.entry.delete(0, tk.END)
        self.entry.insert(0, code)
        self.hide_popup()

app = ctk.CTk()
e = ctk.CTkEntry(app)
e.pack(padx=50, pady=50)
s = SuggestPopup(app, e)

def test_it():
    print("Simulating typing...")
    e.insert(0, '7')
    s.on_key_release(type('Event', (), {'keysym': 'a'}))
    
app.after(1000, test_it)
app.after(3000, app.destroy)
app.mainloop()
