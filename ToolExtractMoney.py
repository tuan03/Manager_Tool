#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import subprocess
import json
import re
import queue
import time
import os
import signal
from datetime import datetime

# ====== CẤU HÌNH / REGEX ======
MARK = "Start sending event to main app:"
PATTERN = re.compile(r'Start sending event to main app:\s*(\{.*\})')

# File log đầu ra
LOG_FILE = "log.txt"

class LogGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Ad Events Monitor")
        self.geometry("900x520")
        self.minsize(820, 460)

        # State
        self.total = 0.0
        self.proc = None
        self.reader_thread = None
        self.stop_event = threading.Event()
        self.q = queue.Queue()

        self._build_ui()
        self._schedule_queue_drain()

    # ---------- UI ----------
    def _build_ui(self):
        # Main split
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)

        # Header / Controls
        toolbar = ttk.Frame(self, padding=(10, 8))
        toolbar.grid(row=0, column=0, columnspan=2, sticky="ew")

        self.btn_start = ttk.Button(toolbar, text="Start", command=self.start_capture)
        self.btn_stop = ttk.Button(toolbar, text="Stop", command=self.stop_capture, state="disabled")
        self.btn_clear = ttk.Button(toolbar, text="Clear table", command=self.clear_table)
        self.btn_open_log = ttk.Button(toolbar, text="Open log.txt", command=self.open_log_file)

        self.status_var = tk.StringVar(value="Idle")
        status_lbl = ttk.Label(toolbar, textvariable=self.status_var, foreground="#555")

        self.btn_start.pack(side="left")
        self.btn_stop.pack(side="left", padx=(8, 0))
        self.btn_clear.pack(side="left", padx=(8, 0))
        self.btn_open_log.pack(side="left", padx=(8, 0))
        status_lbl.pack(side="right")

        # Left: Table
        left = ttk.Frame(self, padding=(10, 0, 6, 10))
        left.grid(row=1, column=0, sticky="nsew")
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        lbl_left = ttk.Label(left, text="Logs (Loại thưởng, Số tiền USD)", font=("Segoe UI", 10, "bold"))
        lbl_left.grid(row=0, column=0, sticky="w", pady=(0, 6))

        cols = ("format", "value")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", height=18)
        self.tree.heading("format", text="Loại thưởng")
        self.tree.heading("value", text="Số tiền (USD)")
        self.tree.column("format", width=260, anchor="w")
        self.tree.column("value", width=140, anchor="e")

        vsb = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=vsb.set)

        self.tree.grid(row=1, column=0, sticky="nsew")
        vsb.grid(row=1, column=1, sticky="ns")

        # Right: Total panel
        right = ttk.Frame(self, padding=(6, 0, 10, 10))
        right.grid(row=1, column=1, sticky="nsew")
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        lbl_right = ttk.Label(right, text="Tổng số tiền đã nhận", font=("Segoe UI", 10, "bold"))
        lbl_right.grid(row=0, column=0, sticky="w", pady=(0, 6))

        card = ttk.Frame(right, padding=16, style="Card.TFrame")
        card.grid(row=1, column=0, sticky="nsew")

        self.total_var = tk.StringVar(value="$0.00000000")
        total_lbl = ttk.Label(card, textvariable=self.total_var, font=("Segoe UI", 24, "bold"))
        total_lbl.pack(anchor="center", pady=(12, 4))

        self.last_update_var = tk.StringVar(value="Last update: —")
        sub_lbl = ttk.Label(card, textvariable=self.last_update_var, foreground="#666")
        sub_lbl.pack(anchor="center")

        # Style tweaks
        style = ttk.Style(self)
        # Use a theme that supports TTK styling on most OS
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Card.TFrame", relief="groove", borderwidth=1)

        # Footer help
        footer = ttk.Label(
            right,
            text="Mỗi dòng được lưu vào log.txt theo dạng: ad_format\\tvalue\\t(total=...)\n"
                 "Nhấn Start để bắt đầu đọc adb logcat.",
            foreground="#555",
            justify="left"
        )
        footer.grid(row=2, column=0, sticky="w", pady=(8, 0))

        # Close protocol
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---------- Capture control ----------
    def start_capture(self):
        if self.proc is not None and self.proc.poll() is None:
            messagebox.showinfo("Đang chạy", "Tiến trình đang chạy rồi.")
            return
        self.stop_event.clear()
        self._ensure_logfile_exists()

        # Clear ADB buffer first (optional; can ignore failures)
        try:
            subprocess.run(["adb", "logcat", "-c"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

        # Start subprocess
        try:
            self.proc = subprocess.Popen(
                ["adb", "logcat", "-v", "brief"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
        except FileNotFoundError:
            messagebox.showerror("Lỗi", "Không tìm thấy 'adb'. Hãy cài Android Platform Tools và thêm vào PATH.")
            return
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể chạy adb: {e}")
            return

        # Start reader thread
        self.reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
        self.reader_thread.start()

        self.status_var.set("Capturing…")
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")

    def stop_capture(self):
        self.stop_event.set()
        if self.proc:
            try:
                # Try graceful terminate
                if os.name == "nt":
                    self.proc.terminate()
                else:
                    os.killpg(os.getpgid(self.proc.pid), signal.SIGTERM)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
        self.proc = None
        self.status_var.set("Stopped")
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")

    def on_close(self):
        self.stop_capture()
        self.destroy()

    # ---------- Reader / Parser ----------
    def _reader_loop(self):
        # Read lines and push parsed events to queue
        if not self.proc or not self.proc.stdout:
            return
        for line in self.proc.stdout:
            if self.stop_event.is_set():
                break
            if MARK not in line:
                continue
            m = PATTERN.search(line)
            if not m:
                continue
            try:
                payload = json.loads(m.group(1))
                print("Parsed payload:", payload)  # Debug
            except json.JSONDecodeError:
                continue

            events = payload.get("events", [])
            for ev in events:
                params = ev.get("params", {}) or {}
                ad_format = params.get("ad_format")
                value = params.get("value")
                if ad_format is None or value is None:
                    continue
                try:
                    v = float(value)
                except (TypeError, ValueError):
                    continue
                # Push to UI queue
                self.q.put((ad_format, v))

        # End of stream
        self.q.put(("__END__", 0.0))

    # ---------- UI Queue Drain ----------
    def _schedule_queue_drain(self):
        self.after(80, self._drain_queue)

    def _drain_queue(self):
        try:
            while True:
                ad_format, v = self.q.get_nowait()
                if ad_format == "__END__":
                    self.status_var.set("Stream ended")
                    break
                self._append_row(ad_format, v)
        except queue.Empty:
            pass
        finally:
            self._schedule_queue_drain()

    # ---------- Helpers ----------
    def _append_row(self, ad_format: str, value: float):
        # Update table
        self.tree.insert("", "end", values=(ad_format, f"{value:.8f}"))
        # Update total
        self.total += value
        self.total_var.set(f"${self.total:.8f}")
        self.last_update_var.set(f"Last update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Append to log file
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                str_total = f"{self.total:.8f}"
                f.write(f"{ad_format}\t{value}\t(total={str_total})\n")
        except Exception as e:
            # Non-fatal: show once in status
            self.status_var.set(f"Không ghi được log.txt: {e}")

        # Auto-scroll to last row
        try:
            last = self.tree.get_children()[-1]
            self.tree.see(last)
        except IndexError:
            pass

    def clear_table(self):
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        self.total = 0.0
        self.total_var.set("$0.00000000")
        self.last_update_var.set("Last update: —")

    def open_log_file(self):
        # Open log.txt with default app
        try:
            self._ensure_logfile_exists()
            if os.name == "nt":
                os.startfile(LOG_FILE)  # type: ignore
            elif sys.platform == "darwin":
                subprocess.run(["open", LOG_FILE], check=False)
            else:
                subprocess.run(["xdg-open", LOG_FILE], check=False)
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không mở được log.txt: {e}")

    def _ensure_logfile_exists(self):
        if not os.path.exists(LOG_FILE):
            try:
                with open(LOG_FILE, "w", encoding="utf-8") as f:
                    f.write("")  # create empty file
            except Exception:
                pass


if __name__ == "__main__":
    app = LogGUI()
    app.mainloop()
