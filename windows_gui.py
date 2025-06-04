import sys
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox


class TunnelGUI:
    def __init__(self, root):
        self.root = root
        self.proc = None
        root.title("Local Remote Tunnel Client")

        frm = ttk.Frame(root, padding=10)
        frm.grid(row=0, column=0, sticky="nsew")
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)

        ttk.Label(frm, text="Server:").grid(row=0, column=0, sticky="e")
        self.server_var = tk.StringVar(value="localhost:8000")
        ttk.Entry(frm, textvariable=self.server_var, width=40).grid(row=0, column=1, sticky="we")

        ttk.Label(frm, text="Token:").grid(row=1, column=0, sticky="e")
        self.token_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.token_var, width=40, show="*").grid(row=1, column=1, sticky="we")

        ttk.Label(frm, text="Mappings (one per line LOCAL=TARGET):").grid(row=2, column=0, sticky="ne")
        self.map_text = tk.Text(frm, height=4, width=40)
        self.map_text.grid(row=2, column=1, sticky="we")

        ttk.Label(frm, text="CA cert (optional):").grid(row=3, column=0, sticky="e")
        self.ca_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.ca_var, width=40).grid(row=3, column=1, sticky="we")

        ttk.Label(frm, text="Retries:").grid(row=4, column=0, sticky="e")
        self.retries_var = tk.IntVar(value=3)
        ttk.Entry(frm, textvariable=self.retries_var, width=5).grid(row=4, column=1, sticky="w")

        btn_frame = ttk.Frame(frm)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=5)
        self.start_btn = ttk.Button(btn_frame, text="Start", command=self.start)
        self.start_btn.grid(row=0, column=0, padx=5)
        self.stop_btn = ttk.Button(btn_frame, text="Stop", command=self.stop, state="disabled")
        self.stop_btn.grid(row=0, column=1, padx=5)

        self.log = scrolledtext.ScrolledText(frm, state="disabled", width=60, height=15)
        self.log.grid(row=6, column=0, columnspan=2, sticky="nsew")
        frm.rowconfigure(6, weight=1)

    def append_log(self, text):
        self.log.configure(state="normal")
        self.log.insert(tk.END, text)
        self.log.see(tk.END)
        self.log.configure(state="disabled")

    def reader_thread(self):
        assert self.proc is not None
        for line in self.proc.stdout:
            self.append_log(line.decode())
        self.append_log("\nClient stopped\n")
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.proc = None

    def start(self):
        if self.proc is not None:
            return
        server = self.server_var.get().strip()
        token = self.token_var.get().strip()
        maps = [m.strip() for m in self.map_text.get("1.0", tk.END).splitlines() if m.strip()]
        if not server or not token or not maps:
            messagebox.showerror("Error", "Server, token and at least one mapping are required")
            return
        cmd = [sys.executable, "tunnel.py", "client", "--server", server, "--token", token, "--retries", str(self.retries_var.get())]
        for m in maps:
            cmd.extend(["--map", m])
        ca = self.ca_var.get().strip()
        if ca:
            cmd.extend(["--ca", ca])
        self.append_log(f"Starting: {' '.join(cmd)}\n")
        self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        threading.Thread(target=self.reader_thread, daemon=True).start()
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")

    def stop(self):
        if self.proc:
            self.proc.terminate()


def main():
    root = tk.Tk()
    TunnelGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
