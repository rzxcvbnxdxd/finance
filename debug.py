import customtkinter as ctk
import tkinter as tk

app = ctk.CTk()
v = tk.StringVar()
e = ctk.CTkEntry(app)
e.pack()

# Configure after creation
e.configure(textvariable=v)

def on_w(*args):
    print('changed:', v.get())
v.trace_add('write', on_w)

app.after(1000, lambda: e.insert(0, 'test'))
app.after(2000, app.destroy)
app.mainloop()
