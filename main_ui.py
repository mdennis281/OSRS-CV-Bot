import tkinter as tk
from tkinter import ttk, scrolledtext
import logging

# A modern, high-contrast dark theme inspired by ttk-dark-theme and Material Design

class TextHandler(logging.Handler):
    """Logging handler that outputs to a Tkinter ScrolledText widget."""
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        self.text_widget.configure(state='normal')
        self.text_widget.insert(tk.END, msg + '\n')
        self.text_widget.configure(state='disabled')
        self.text_widget.yview(tk.END)

class BotManagerUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Bot Manager")
        self.geometry("900x600")
        self.configure(bg='#212121')  # Dark background
        self.style = ttk.Style(self)
        self._setup_style()
        self.scripts = [f"Script_{i}" for i in range(1, 21)]
        self.filtered_scripts = list(self.scripts)
        self._create_widgets()
        self._setup_logging()

    def _setup_style(self):
        self.style.theme_use('clam')
        base_bg = '#212121'
        panel_bg = '#2e2e2e'
        widget_bg = '#313131'
        select_bg = '#2196F3'
        select_fg = '#FFFFFF'
        fg = '#E0E0E0'

        # General
        self.style.configure('.', background=base_bg, foreground=fg, font=('Segoe UI', 10))
        self.style.configure('TFrame', background=base_bg)
        self.style.configure('TLabel', background=base_bg, foreground=fg)
        self.style.configure('TLabelframe', background=panel_bg, foreground=fg)
        self.style.configure('TLabelframe.Label', background=panel_bg, foreground=fg)

        # Entry & Combobox
        self.style.configure('TEntry', fieldbackground=widget_bg, background=widget_bg, foreground=fg)
        self.style.map('TEntry', insertcolor=[('!disabled', fg)])
        self.style.configure('TCombobox', fieldbackground=widget_bg, background=widget_bg, foreground=fg)
        self.style.map('TCombobox', fieldbackground=[('!disabled', widget_bg)])

        # Buttons
        self.style.configure('TButton', background=widget_bg, foreground=fg, borderwidth=0, focusthickness=3,
                             focuscolor=select_bg)
        self.style.map('TButton', background=[('active', '#424242')], foreground=[('active', fg)])

        # Scale
        self.style.configure('Horizontal.TScale', troughcolor=widget_bg)

        # Treeview
        self.style.configure('Treeview', background=widget_bg, fieldbackground=widget_bg, foreground=fg, rowheight=24)
        self.style.layout('Treeview', [('Treeview.treearea', {'sticky': 'nswe'})])
        self.style.map('Treeview', background=[('selected', select_bg)], foreground=[('selected', select_fg)])

        # Scrollbar
        self.style.configure('Vertical.TScrollbar', background=panel_bg, troughcolor=base_bg,
                             arrowcolor=fg)

    def _create_widgets(self):
        vertical_pane = ttk.Panedwindow(self, orient=tk.VERTICAL)
        vertical_pane.pack(fill=tk.BOTH, expand=True)

        top_pane = ttk.Panedwindow(vertical_pane, orient=tk.HORIZONTAL)
        bottom_frame = ttk.Frame(vertical_pane)
        vertical_pane.add(top_pane, weight=3)
        vertical_pane.add(bottom_frame, weight=1)

        # Script panel
        script_frame = ttk.Labelframe(top_pane, text="Scripts")
        top_pane.add(script_frame, weight=1)
        self._build_script_panel(script_frame)

        # Controls & State
        right_frame = ttk.Frame(top_pane)
        top_pane.add(right_frame, weight=2)
        self._build_control_panel(right_frame)
        self._build_state_panel(right_frame)

        # Log panel
        log_frame = ttk.Labelframe(bottom_frame, text="Logs")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)
        self.log_widget = scrolledtext.ScrolledText(log_frame, state='disabled', height=7,
                                                   bg='#1e1e1e', fg='#E0E0E0', insertbackground='#E0E0E0')
        self.log_widget.pack(fill=tk.BOTH, expand=True)

    def _build_script_panel(self, parent):
        search_var = tk.StringVar()
        entry = ttk.Entry(parent, textvariable=search_var)
        entry.pack(fill=tk.X, padx=6, pady=(6,2))
        entry.bind('<KeyRelease>', lambda e: self._filter_scripts(search_var.get()))

        cols = ('name',)
        self.script_tree = ttk.Treeview(parent, columns=cols, show='headings', selectmode='browse')
        self.script_tree.heading('name', text='Script Name')
        vsb = ttk.Scrollbar(parent, orient='vertical', command=self.script_tree.yview)
        self.script_tree.configure(yscrollcommand=vsb.set)
        self.script_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6,0), pady=6)
        vsb.pack(side=tk.LEFT, fill=tk.Y, padx=(0,6), pady=6)
        self._refresh_script_list()

    def _filter_scripts(self, query):
        q = query.lower()
        self.filtered_scripts = [s for s in self.scripts if q in s.lower()] if q else list(self.scripts)
        self._refresh_script_list()

    def _refresh_script_list(self):
        for item in self.script_tree.get_children():
            self.script_tree.delete(item)
        for script in self.filtered_scripts:
            self.script_tree.insert('', tk.END, values=(script,))

    def _build_control_panel(self, parent):
        ctrl = ttk.Labelframe(parent, text="Controls")
        ctrl.pack(fill=tk.X, padx=6, pady=6)

        btns = ttk.Frame(ctrl)
        btns.pack(pady=6)
        ttk.Button(btns, text="Start", command=self._start_bot).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Stop", command=self._stop_bot).pack(side=tk.LEFT, padx=4)

        # Mouse speed
        speed_frame = ttk.Frame(ctrl)
        speed_frame.pack(fill=tk.X, padx=6, pady=(4,0))
        ttk.Label(speed_frame, text="Mouse Speed Multiplier").pack(side=tk.LEFT)
        self.speed_var = tk.DoubleVar(value=1.0)
        ttk.Scale(speed_frame, from_=0.1, to=5.0, variable=self.speed_var,
                  style='Horizontal.TScale').pack(fill=tk.X, expand=True, padx=6)

        # Log level
        lvl_frame = ttk.Frame(ctrl)
        lvl_frame.pack(fill=tk.X, padx=6, pady=(6,4))
        ttk.Label(lvl_frame, text="Log Level").pack(side=tk.LEFT)
        self.level_var = tk.StringVar(value='INFO')
        combo = ttk.Combobox(lvl_frame, textvariable=self.level_var,
                              values=['DEBUG','INFO','WARNING','ERROR','CRITICAL'], state='readonly')
        combo.pack(side=tk.LEFT, padx=6)
        combo.bind('<<ComboboxSelected>>', lambda e: self._set_log_level())

    def _build_state_panel(self, parent):
        state = ttk.Labelframe(parent, text="Game State")
        state.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.state_vars = {}
        for key in ['Hitpoints','Prayer','Run Rate','Active Tab']:
            row = ttk.Frame(state)
            row.pack(fill=tk.X, pady=3)
            ttk.Label(row, text=f"{key}:").pack(side=tk.LEFT)
            var = tk.StringVar(value='--')
            self.state_vars[key] = var
            ttk.Label(row, textvariable=var, width=8).pack(side=tk.LEFT, padx=6)
            ttk.Button(row, text="Refresh", command=lambda k=key: self._refresh_state(k)).pack(side=tk.LEFT)

    def _setup_logging(self):
        self.logger = logging.getLogger('BotManager')
        handler = TextHandler(self.log_widget)
        fmt = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%H:%M:%S')
        handler.setFormatter(fmt)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
        self._set_log_level()

    def _set_log_level(self):
        lvl = getattr(logging, self.level_var.get(), logging.INFO)
        self.logger.setLevel(lvl)
        self.logger.info(f"Log level set to {self.level_var.get()}")

    def _start_bot(self):
        sel = self.script_tree.selection()
        if sel:
            script = self.script_tree.item(sel[0], 'values')[0]
            self.logger.info(f"Starting bot: {script}")
            # TODO: hook into bot start

    def _stop_bot(self):
        self.logger.info("Stopping bot")
        # TODO: hook into bot stop

    def _refresh_state(self, name):
        self.logger.debug(f"Fetching state: {name}")
        # TODO: replace with real API call
        dummy = {'Hitpoints':'99','Prayer':'52','Run Rate':'100%','Active Tab':'Inventory'}
        self.state_vars[name].set(dummy.get(name,'--'))

if __name__ == '__main__':
    BotManagerUI().mainloop()
