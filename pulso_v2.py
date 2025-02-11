import tkinter as tk
from tkinter import ttk
import time
from dataclasses import dataclass

@dataclass
class BreathingPattern:
    phases: list[float]
    uses_pace: bool
    labels: list[str]

class BreathingApp:
    MIN_BREATH_PACE = 2.0
    MAX_BREATH_PACE = 9.0
    DEFAULT_BREATH_PACE = 5.5
    MIN_SESSION_DURATION = 0.5
    MAX_SESSION_DURATION = 60.0
    DEFAULT_SESSION_DURATION = 5.0
    CANVAS_SIZE = 300
    CIRCLE_PADDING = 15
    UPDATE_INTERVAL = 16  # ~60 FPS

    PHASE_COLORS = {"inhale": "#3498db", "hold": "#2ecc71", "exhale": "#e67e22"}
    SCALE_FACTORS = {
        "inhale": lambda p: 0.2 + 0.8 * p,
        "exhale": lambda p: 1.0 - 0.8 * p,
        "hold":   lambda _: 1.0
    }

    def __init__(self, master):
        self.master = master
        master.title("Breathing Exercise Assistant")
        master.geometry("500x800")

        self.patterns = {
            "Balanced (1:1)": BreathingPattern([1, 1], True,  ["inhale", "exhale"]),
            "Calm (1:2)":     BreathingPattern([1, 2], True,  ["inhale", "exhale"]),
            "Vitality (2:1)": BreathingPattern([2, 1], True,  ["inhale", "exhale"]),
            "4-7-8 (+hold)":  BreathingPattern([4, 7, 8], False, ["inhale", "hold", "exhale"])
        }

        self.selected_pattern = tk.StringVar(value="Balanced (1:1)")
        self.breath_pace = tk.DoubleVar(value=self.DEFAULT_BREATH_PACE)
        self.session_duration = tk.DoubleVar(value=self.DEFAULT_SESSION_DURATION)
        self.is_running = False
        self.current_phase = "exhale"
        self.progress = 0
        self.scheduled_end = None

        self._configure_styles()
        self._create_widgets()
        self.reset_visuals()

    def _configure_styles(self):
        style = ttk.Style()
        style.configure("Accent.TButton", font=("Arial", 14, "bold"), padding=10)
        style.map("Dis.TLabel", foreground=[("disabled", "gray")])

    def _create_widgets(self):
        # Pattern selection
        ttk.Label(self.master, text="Select Breathing Pattern:").pack(pady=(20, 5))
        f = ttk.Frame(self.master); f.pack()
        for name in self.patterns:
            ttk.Radiobutton(f, text=name, variable=self.selected_pattern,
                            value=name, command=self._handle_pattern_change
            ).pack(side=tk.LEFT, padx=5)

        # Canvas & circle
        self.canvas = tk.Canvas(self.master, width=self.CANVAS_SIZE, height=self.CANVAS_SIZE)
        self.canvas.pack(pady=20)
        c = self.CANVAS_SIZE // 2
        r = c - self.CIRCLE_PADDING
        coords = (c - r, c - r, c + r, c + r)
        self.circle = self.canvas.create_oval(*coords, outline="#ecf0f1", width=6)
        self.arc = self.canvas.create_arc(*coords, start=90, extent=0, width=6,
                                          outline=self.PHASE_COLORS["inhale"], style="arc")
        self.text = self.canvas.create_text(c, c, text="Ready", font=("Arial", 18, "bold"))

        # Sliders
        f2 = ttk.Frame(self.master); f2.pack(fill=tk.X, padx=20, pady=10)
        f2.columnconfigure(1, weight=1)
        self.breath_scale, self.breath_pace_label = self._create_scale(
            f2, 0, "Breath Pace (bpm):", self.breath_pace,
            self.MIN_BREATH_PACE, self.MAX_BREATH_PACE, 0.5, "bpm"
        )
        self.session_scale, self.session_duration_label = self._create_scale(
            f2, 1, "Duration (min):", self.session_duration,
            self.MIN_SESSION_DURATION, self.MAX_SESSION_DURATION, 0.5, "min"
        )

        # Buttons
        f3 = ttk.Frame(self.master); f3.pack(pady=20)
        self.start_stop_button = ttk.Button(f3, text="Start", command=self.toggle_session, style="Accent.TButton")
        self.start_stop_button.pack(side=tk.LEFT, padx=10)
        ttk.Button(f3, text="Reset", command=self.reset_settings).pack(side=tk.LEFT, padx=10)

    def _create_scale(self, parent, row, lbl_text, var, min_v, max_v, step, unit):
        ttk.Label(parent, text=lbl_text).grid(row=row, column=0, sticky="w")
        scale = ttk.Scale(
            parent, from_=min_v, to=max_v, variable=var,
            command=lambda v: self._update_scale(v, var, lbl, min_v, max_v, step, unit)
        )
        scale.grid(row=row, column=1, sticky="ew")
        val_str = f"{var.get():.1f}" if unit == "bpm" else f"{var.get():g}"
        lbl = ttk.Label(parent, text=f"{val_str} {unit}")
        lbl.grid(row=row, column=2, padx=5)
        return scale, lbl

    def _update_scale(self, value, var, label, mn, mx, step, unit):
        try:
            scaled = round(float(value) / step) * step
            clamped = max(mn, min(scaled, mx))
            var.set(clamped)
            txt = f"{clamped:.1f}" if unit == "bpm" else f"{clamped:g}"
            label.config(text=f"{txt} {unit}")
        except:
            var.set(var.get())
            self.master.bell()

    def _handle_pattern_change(self):
        p = self.patterns[self.selected_pattern.get()]
        state = "normal" if p.uses_pace else "disabled"
        self.breath_scale.config(state=state)
        self.breath_pace_label.config(style="TLabel" if p.uses_pace else "Dis.TLabel")

    def toggle_session(self):
        self.is_running = not self.is_running
        self.start_stop_button.config(text="Stop" if self.is_running else "Start")
        if self.is_running:
            ms = int(self.session_duration.get() * 60 * 1000)
            self.scheduled_end = self.master.after(ms, self.stop_session)
            self._run_breathing_cycle()
        else:
            self.stop_session()

    def stop_session(self):
        if self.is_running:
            self.is_running = False
            if self.scheduled_end:
                self.master.after_cancel(self.scheduled_end)
            self.scheduled_end = None
        self.reset_visuals()

    def reset_settings(self):
        self.stop_session()
        self.breath_pace.set(self.DEFAULT_BREATH_PACE)
        self.session_duration.set(self.DEFAULT_SESSION_DURATION)
        self.selected_pattern.set("Balanced (1:1)")
        self.breath_pace_label.config(text=f"{self.DEFAULT_BREATH_PACE:.1f} bpm")
        self.session_duration_label.config(text=f"{self.DEFAULT_SESSION_DURATION:g} min")
        self._handle_pattern_change()

    def reset_visuals(self):
        self.progress = 0
        self.current_phase = "exhale"
        self.canvas.itemconfig(self.arc, extent=0, outline=self.PHASE_COLORS["inhale"])
        self.canvas.itemconfig(self.text, text="Ready")
        self._update_circle_size(1.0)

    def _run_breathing_cycle(self):
        if not self.is_running: return
        pat = self.patterns[self.selected_pattern.get()]
        total = sum(pat.phases)
        cycle_time = 60 / self.breath_pace.get() if pat.uses_pace else total
        self.progress = (self.progress + self.UPDATE_INTERVAL / (cycle_time * 1000)) % 1
        phase, prog, rem = self._calc_phase_progress(self.progress, pat, total)
        self.current_phase = phase
        self._update_visuals(prog, rem, phase)
        self.master.after(self.UPDATE_INTERVAL, self._run_breathing_cycle)

    def _calc_phase_progress(self, norm, pat, total):
        t = norm * total
        c = 0
        for i, d in enumerate(pat.phases):
            if t < c + d:
                e = t - c
                return pat.labels[i], e / d, (d - e)
            c += d
        # Fallback: last phase
        return pat.labels[-1], 1.0, 0.0

    def _update_visuals(self, prog, rem, phase):
        ext = min(359.99, 359.99 * prog)
        self.canvas.itemconfig(self.arc, outline=self.PHASE_COLORS[phase], extent=ext)
        self.canvas.itemconfig(self.text, text=f"{phase.capitalize()}\n{rem:.1f}s")
        self._update_circle_size(self.SCALE_FACTORS[phase](prog))

    def _update_circle_size(self, scale):
        c = self.CANVAS_SIZE // 2
        r = (c - self.CIRCLE_PADDING) * scale
        coords = (c - r, c - r, c + r, c + r)
        self.canvas.coords(self.circle, *coords)
        self.canvas.coords(self.arc, *coords)

if __name__ == "__main__":
    root = tk.Tk()
    BreathingApp(root)
    root.mainloop()