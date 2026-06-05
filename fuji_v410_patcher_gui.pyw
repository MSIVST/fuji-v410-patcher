from __future__ import annotations

import json
import queue
import threading
import traceback
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from fuji_v410_patcher import (
    KNOWN_STOCK_GCD_SHA256,
    TOOL_NAME,
    TOOL_VERSION,
    default_output_path,
    patch_gcd,
)


class FujiPatcherApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{TOOL_NAME} {TOOL_VERSION}")
        self.geometry("820x620")
        self.minsize(720, 520)

        self.input_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.report_var = tk.StringVar()
        self.allow_unknown_var = tk.BooleanVar(value=False)
        self.write_report_var = tk.BooleanVar(value=False)

        self.queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self.worker: threading.Thread | None = None

        self._build_ui()
        self.after(100, self._poll_queue)

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=14)
        root.pack(fill=tk.BOTH, expand=True)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(7, weight=1)

        title = ttk.Label(root, text="Suzuki Garmin Fuji v4.10 Patcher", font=("Segoe UI", 16, "bold"))
        title.grid(row=0, column=0, columnspan=3, sticky="w")

        subtitle = ttk.Label(
            root,
            text="Select an official v4.10 GUPDATE.GCD. The tool verifies it, applies startup + MP3 + map365 patches, and writes a patched output file.",
            wraplength=760,
        )
        subtitle.grid(row=1, column=0, columnspan=3, sticky="we", pady=(4, 14))

        ttk.Label(root, text="Official GCD input").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Entry(root, textvariable=self.input_var).grid(row=2, column=1, sticky="we", padx=8, pady=4)
        ttk.Button(root, text="Browse...", command=self.browse_input).grid(row=2, column=2, sticky="e", pady=4)

        ttk.Label(root, text="Patched GCD output").grid(row=3, column=0, sticky="w", pady=4)
        ttk.Entry(root, textvariable=self.output_var).grid(row=3, column=1, sticky="we", padx=8, pady=4)
        ttk.Button(root, text="Save as...", command=self.browse_output).grid(row=3, column=2, sticky="e", pady=4)

        ttk.Checkbutton(root, text="Write JSON report", variable=self.write_report_var, command=self._sync_report_state).grid(
            row=4, column=0, sticky="w", pady=4
        )
        self.report_entry = ttk.Entry(root, textvariable=self.report_var)
        self.report_entry.grid(row=4, column=1, sticky="we", padx=8, pady=4)
        self.report_button = ttk.Button(root, text="Report as...", command=self.browse_report)
        self.report_button.grid(row=4, column=2, sticky="e", pady=4)

        opts = ttk.Frame(root)
        opts.grid(row=5, column=0, columnspan=3, sticky="we", pady=(4, 10))
        ttk.Checkbutton(
            opts,
            text="Allow unknown full-file hash if the host firmware payload still matches stock v4.10",
            variable=self.allow_unknown_var,
        ).pack(side=tk.LEFT)

        buttons = ttk.Frame(root)
        buttons.grid(row=6, column=0, columnspan=3, sticky="we", pady=(0, 10))
        self.analyze_button = ttk.Button(buttons, text="Dry-run / Analyze", command=lambda: self.start_job(dry_run=True))
        self.analyze_button.pack(side=tk.LEFT)
        self.patch_button = ttk.Button(buttons, text="Patch Firmware", command=lambda: self.start_job(dry_run=False))
        self.patch_button.pack(side=tk.LEFT, padx=8)
        ttk.Button(buttons, text="Clear Log", command=self.clear_log).pack(side=tk.LEFT, padx=8)

        status_frame = ttk.LabelFrame(root, text="Status")
        status_frame.grid(row=7, column=0, columnspan=3, sticky="nsew")
        status_frame.rowconfigure(0, weight=1)
        status_frame.columnconfigure(0, weight=1)

        self.log = tk.Text(status_frame, wrap=tk.WORD, height=18, font=("Consolas", 9))
        self.log.grid(row=0, column=0, sticky="nsew")
        yscroll = ttk.Scrollbar(status_frame, orient=tk.VERTICAL, command=self.log.yview)
        yscroll.grid(row=0, column=1, sticky="ns")
        self.log.configure(yscrollcommand=yscroll.set)

        self.progress = ttk.Progressbar(root, mode="indeterminate")
        self.progress.grid(row=8, column=0, columnspan=3, sticky="we", pady=(10, 0))

        footer = ttk.Label(
            root,
            text="Unofficial tool. No Garmin firmware is included. Use at your own risk and keep a stock recovery method ready.",
            foreground="#8a4b00",
            wraplength=760,
        )
        footer.grid(row=9, column=0, columnspan=3, sticky="we", pady=(8, 0))

        self._sync_report_state()
        self._log_known_hashes()

    def _log_known_hashes(self) -> None:
        self.log_line("Supported stock v4.10 regions:")
        for region, sha in KNOWN_STOCK_GCD_SHA256.items():
            self.log_line(f"  {region}: {sha.upper()}")
        self.log_line("")

    def _sync_report_state(self) -> None:
        state = "normal" if self.write_report_var.get() else "disabled"
        self.report_entry.configure(state=state)
        self.report_button.configure(state=state)

    def browse_input(self) -> None:
        path = filedialog.askopenfilename(
            title="Select official Garmin GUPDATE.GCD",
            filetypes=[("Garmin GCD", "*.gcd *.GCD"), ("All files", "*.*")],
        )
        if not path:
            return
        input_path = Path(path)
        self.input_var.set(str(input_path))
        if not self.output_var.get():
            self.output_var.set(str(default_output_path(input_path)))
        if not self.report_var.get():
            self.report_var.set(str(input_path.with_name(input_path.stem + "_patch_report.json")))

    def browse_output(self) -> None:
        initial = self.output_var.get() or "GUPDATE_patched.gcd"
        path = filedialog.asksaveasfilename(
            title="Choose patched output GCD",
            initialfile=Path(initial).name,
            defaultextension=".gcd",
            filetypes=[("Garmin GCD", "*.gcd"), ("All files", "*.*")],
        )
        if path:
            self.output_var.set(path)

    def browse_report(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Choose JSON report output",
            initialfile="patch_report.json",
            defaultextension=".json",
            filetypes=[("JSON report", "*.json"), ("All files", "*.*")],
        )
        if path:
            self.report_var.set(path)

    def clear_log(self) -> None:
        self.log.delete("1.0", tk.END)

    def log_line(self, text: str = "") -> None:
        self.log.insert(tk.END, text + "\n")
        self.log.see(tk.END)

    def set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        self.analyze_button.configure(state=state)
        self.patch_button.configure(state=state)
        if busy:
            self.progress.start(12)
        else:
            self.progress.stop()

    def start_job(self, dry_run: bool) -> None:
        if self.worker and self.worker.is_alive():
            messagebox.showinfo("Busy", "A patch/analyze job is already running.")
            return

        input_path = Path(self.input_var.get().strip())
        output_path = Path(self.output_var.get().strip()) if self.output_var.get().strip() else default_output_path(input_path)
        report_path = Path(self.report_var.get().strip()) if self.write_report_var.get() and self.report_var.get().strip() else None

        if not input_path.exists():
            messagebox.showerror("Missing input", "Please select an existing official GUPDATE.GCD file.")
            return
        if input_path.resolve() == output_path.resolve() and not dry_run:
            messagebox.showerror("Unsafe output", "Output path must be different from input path.")
            return

        self.set_busy(True)
        self.log_line("=" * 78)
        self.log_line("Dry-run / analyze..." if dry_run else "Patching firmware...")
        self.log_line(f"Input:  {input_path}")
        self.log_line(f"Output: {output_path}")
        if report_path:
            self.log_line(f"Report: {report_path}")

        self.worker = threading.Thread(
            target=self._job_thread,
            args=(input_path, output_path, report_path, dry_run, self.allow_unknown_var.get()),
            daemon=True,
        )
        self.worker.start()

    def _job_thread(
        self,
        input_path: Path,
        output_path: Path,
        report_path: Path | None,
        dry_run: bool,
        allow_unknown_hash: bool,
    ) -> None:
        try:
            report = patch_gcd(
                input_path=input_path,
                output_path=output_path,
                allow_unknown_hash=allow_unknown_hash,
                dry_run=dry_run,
            )
            if report_path:
                report_path.parent.mkdir(parents=True, exist_ok=True)
                report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
            self.queue.put(("success", (report, report_path, dry_run)))
        except Exception:
            self.queue.put(("error", traceback.format_exc()))

    def _poll_queue(self) -> None:
        try:
            while True:
                kind, payload = self.queue.get_nowait()
                self.set_busy(False)
                if kind == "success":
                    report, report_path, dry_run = payload  # type: ignore[misc]
                    self._show_success(report, report_path, dry_run)
                else:
                    self._show_error(str(payload))
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    def _show_success(self, report: dict, report_path: Path | None, dry_run: bool) -> None:
        self.log_line("SUCCESS")
        self.log_line(f"Detected region: {report['detected_region']}")
        self.log_line(f"Input SHA-256:  {report['input_sha256'].upper()}")
        self.log_line(f"Output SHA-256: {report['output_sha256'].upper()}")
        self.log_line(f"Verification:   {report['verification']['overall_patched_verification']}")
        for name, ok in report["verification"]["patches_present"].items():
            self.log_line(f"  {name}: {ok}")
        if report_path:
            self.log_line(f"Report written: {report_path}")
        if dry_run:
            self.log_line("Dry run only; no patched GCD was written.")
            messagebox.showinfo("Dry-run complete", "Input verified and patch simulation succeeded.")
        else:
            self.log_line(f"Patched GCD written: {report['output_file']}")
            messagebox.showinfo("Patch complete", "Patched GCD written and verified successfully.")

    def _show_error(self, text: str) -> None:
        self.log_line("ERROR")
        self.log_line(text)
        messagebox.showerror("Patch failed", "The patcher refused this file or hit an error. See the status log for details.")


if __name__ == "__main__":
    app = FujiPatcherApp()
    app.mainloop()
