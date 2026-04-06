import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
import customtkinter as ctk
from styles import *
from downloader import start_download
import os
import json
import subprocess
import sys
import threading

CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".melodex_config.json")

def load_last_folder():
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
            return config.get("last_folder", "")
    except:
        return ""

def save_last_folder(folder):
    with open(CONFIG_FILE, "w") as f:
        json.dump({"last_folder": folder}, f)

def check_ffmpeg():
    """Check if ffmpeg is installed and accessible"""
    try:
        # Try to run ffmpeg -version
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Bemudex")
        self.root.geometry("650x700")
        self.root.resizable(False, False)
        
        # Check ffmpeg on startup
        if not check_ffmpeg():
            messagebox.showwarning(
                "ffmpeg Missing",
                "ffmpeg is not installed or not in PATH.\n\n"
                "MP3 conversion will fail.\n\n"
                "Install ffmpeg:\n"
                "• Windows: download from ffmpeg.org\n"
                "• Mac: brew install ffmpeg\n"
                "• Linux: sudo apt install ffmpeg"
            )
        
        self.stop_event = None
        self.download_thread = None
        self._build_ui()

    def _build_ui(self):
        self._build_header()
        self._build_url_input()
        self._build_folder_input()
        self._build_quality_option()
        self._build_buttons()
        self._build_log()

    def _build_header(self):
        ctk.CTkLabel(
            self.root, text="Bemudex",
            font=ctk.CTkFont(family="Ubuntu", size=20, weight="bold")
        ).pack(pady=(20, 2))

        ctk.CTkLabel(
            self.root,
            text="Download YouTube videos or playlists as high-quality MP3.",
            font=ctk.CTkFont(family="Ubuntu", size=11),
            text_color="gray50"
        ).pack(pady=(0, 10))

    def _build_url_input(self):
        url_frame = ctk.CTkFrame(self.root)
        url_frame.pack(pady=10, padx=20, fill="x")
        url_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            url_frame, text="Insert URL:",
            font=ctk.CTkFont(family="Ubuntu", size=14)
        ).grid(row=0, column=0, sticky="w", padx=10, pady=(10, 5))

        self.url_entry = ctk.CTkEntry(
            url_frame,
            placeholder_text="Enter YouTube URL here..."
        )
        self.url_entry.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        self.url_entry.bind("<ButtonRelease-3>", lambda e: self._show_context_menu(e, self.url_entry))
        self.url_entry.bind("<Control-v>", lambda e: self._custom_paste(e, self.url_entry))

    def _build_folder_input(self):
        folder_frame = ctk.CTkFrame(self.root)
        folder_frame.pack(pady=10, padx=20, fill="x")

        ctk.CTkLabel(
            folder_frame, text="Download Folder:",
            font=ctk.CTkFont(family="Ubuntu", size=14)
        ).pack(anchor="w", padx=10, pady=(10, 5))

        self.folder_var = tk.StringVar(value=load_last_folder())
        folder_entry_frame = ctk.CTkFrame(folder_frame, fg_color="transparent")
        folder_entry_frame.pack(padx=10, pady=(0, 10), fill="x")

        folder_entry = ctk.CTkEntry(
            folder_entry_frame,
            textvariable=self.folder_var,
            placeholder_text="Select download folder..."
        )
        folder_entry.pack(side="left", fill="x", expand=True)
        folder_entry.bind("<ButtonRelease-3>", lambda e: self._show_context_menu(e, folder_entry))
        folder_entry.bind("<Control-v>", lambda e: self._custom_paste(e, folder_entry))

        ctk.CTkButton(
            folder_entry_frame, text="Browse",
            command=self._browse_folder, width=80
        ).pack(side="right", padx=(10, 0))

    def _build_quality_option(self):
        quality_frame = ctk.CTkFrame(self.root)
        quality_frame.pack(pady=10, padx=20, fill="x")
        
        ctk.CTkLabel(
            quality_frame, text="MP3 Quality:",
            font=ctk.CTkFont(family="Ubuntu", size=14)
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        self.quality_var = ctk.StringVar(value="320")
        quality_menu = ctk.CTkOptionMenu(
            quality_frame,
            values=["128", "192", "320"],
            variable=self.quality_var,
            width=100
        )
        quality_menu.pack(anchor="w", padx=10, pady=(0, 10))
        ctk.CTkLabel(
            quality_frame,
            text="Higher quality = larger file size",
            font=ctk.CTkFont(family="Ubuntu", size=10),
            text_color="gray50"
        ).pack(anchor="w", padx=10, pady=(0, 10))

    def _build_buttons(self):
        button_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        button_frame.pack(pady=10, padx=20, fill="x")
        
        # Download button
        self.btn_download = ctk.CTkButton(
            button_frame, text="Download",
            command=self._download,
            fg_color="#e53935", hover_color="#d32f2f",
            font=ctk.CTkFont(family="Ubuntu", size=14, weight="bold"),
            height=40
        )
        self.btn_download.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        # Cancel button
        self.btn_cancel = ctk.CTkButton(
            button_frame, text="Cancel",
            command=self._cancel_download,
            fg_color="#555555", hover_color="#333333",
            font=ctk.CTkFont(family="Ubuntu", size=14, weight="bold"),
            height=40,
            state="disabled"
        )
        self.btn_cancel.pack(side="left", fill="x", expand=True, padx=(5, 0))
        
        # Open Folder button (below)
        self.btn_open = ctk.CTkButton(
            self.root, text="Open Download Folder",
            command=self._open_folder,
            fg_color="#2b2b2b", hover_color="#404040",
            font=ctk.CTkFont(family="Ubuntu", size=12),
            height=35
        )
        self.btn_open.pack(pady=(5, 0), padx=20, fill="x")

    def _build_log(self):
        log_frame = ctk.CTkFrame(self.root)
        log_frame.pack(pady=(10, 20), padx=20, fill="both", expand=True)

        ctk.CTkLabel(
            log_frame, text="Activity:",
            font=ctk.CTkFont(family="Ubuntu", size=14)
        ).pack(anchor="w", padx=10, pady=(10, 5))

        self.log_box = scrolledtext.ScrolledText(
            log_frame, state=tk.DISABLED,
            height=50, width=90,
            bg="#2b2b2b", fg="#00ff90",
            font=("Ubuntu", 9),
            wrap=tk.WORD
        )
        self.log_box.pack(padx=10, pady=(0, 10), fill="both", expand=True)

    def _browse_folder(self):
        last = self.folder_var.get() or load_last_folder()
        folder = filedialog.askdirectory(
            initialdir=last if last else os.path.expanduser("~")
        )
        if folder:
            self.folder_var.set(folder)
            save_last_folder(folder)

    def _open_folder(self):
        folder = self.folder_var.get()
        if not folder or not os.path.exists(folder):
            self._log("⚠️ No valid folder selected.")
            return
        try:
            if sys.platform == "win32":
                os.startfile(folder)
            elif sys.platform == "darwin":
                subprocess.run(["open", folder])
            else:
                subprocess.run(["xdg-open", folder])
        except Exception as e:
            self._log(f"❌ Could not open folder: {e}")

    def _log(self, message):
        self.root.after(0, self._log_safe, message)

    def _log_safe(self, message):
        self.log_box.config(state=tk.NORMAL)
        self.log_box.insert(tk.END, message + "\n")
        self.log_box.see(tk.END)
        self.log_box.update_idletasks()
        self.log_box.config(state=tk.DISABLED)

    def _custom_paste(self, event, entry):
        try:
            sel_start = entry.index(tk.SEL_FIRST)
            sel_end = entry.index(tk.SEL_LAST)
            entry.delete(sel_start, sel_end)
        except tk.TclError:
            pass
        try:
            entry.insert(tk.INSERT, self.root.clipboard_get())
        except tk.TclError:
            pass
        return "break"

    def _show_context_menu(self, event, entry):
        def cut():
            try:
                sel_start = entry.index(tk.SEL_FIRST)
                sel_end = entry.index(tk.SEL_LAST)
                self.root.clipboard_clear()
                self.root.clipboard_append(entry.get()[sel_start:sel_end])
                entry.delete(sel_start, sel_end)
            except tk.TclError:
                pass

        def copy():
            try:
                sel_start = entry.index(tk.SEL_FIRST)
                sel_end = entry.index(tk.SEL_LAST)
                self.root.clipboard_clear()
                self.root.clipboard_append(entry.get()[sel_start:sel_end])
            except tk.TclError:
                pass

        def paste():
            try:
                entry.insert(tk.INSERT, self.root.clipboard_get())
            except tk.TclError:
                pass

        def select_all():
            entry.select_range(0, tk.END)
            entry.icursor(tk.END)

        menu = tk.Menu(self.root, tearoff=0, bg="#2b2b2b", fg="#ffffff",
                       font=("Ubuntu", 10), activebackground="#404040",
                       activeforeground="#ffffff", relief="flat", bd=0)
        menu.add_command(label="Cut", command=cut)
        menu.add_command(label="Copy", command=copy)
        menu.add_command(label="Paste", command=paste)
        menu.add_command(label="Select All", command=select_all)
        menu.tk_popup(event.x_root, event.y_root)

    def _download(self):
        url = self.url_entry.get().strip()
        folder = self.folder_var.get().strip()
        quality = self.quality_var.get()

        if not url:
            self._log("⚠️ Please enter a YouTube URL.")
            return
        if not folder:
            self._log("⚠️ Please select a download folder.")
            return
        if not os.path.exists(folder):
            self._log("⚠️ Download folder does not exist. Please select a valid folder.")
            return

        # Disable download button, enable cancel
        self.btn_download.configure(state="disabled")
        self.btn_cancel.configure(state="normal")
        
        self._log(f"🚀 Starting download with quality {quality}kbps...")
        
        # Create a stop event for cancellation
        self.stop_event = threading.Event()
        
        # Start download in a separate thread
        start_download(
            url=url,
            folder=folder,
            on_log=self._log,
            on_done=self._on_download_finished,
            quality=quality,
            stop_event=self.stop_event
        )

    def _cancel_download(self):
        if self.stop_event:
            self._log("⚠️ Cancelling download... Please wait.")
            self.stop_event.set()
            self.btn_cancel.configure(state="disabled")

    def _on_download_finished(self):
        # Re-enable buttons on the main thread
        self.root.after(0, lambda: self.btn_download.configure(state="normal"))
        self.root.after(0, lambda: self.btn_cancel.configure(state="disabled"))
        self.stop_event = None