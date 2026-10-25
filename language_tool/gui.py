"""Bilingual desktop workflow. UI language never changes camera options."""
import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from . import controller, detection, firmware, workflow
from .i18n import UserError, translate, error_text, log_text


class App:
    def __init__(self, root):
        self.root, self.busy = root, False
        self.events, self.history = queue.Queue(), []
        self.device = self.package = None
        self.language = tk.StringVar(root, value='中文')
        self.chinese = tk.BooleanVar(root, value=False)
        self.restarted = tk.BooleanVar(root, value=False)
        self.source = tk.StringVar(root, value='')
        self.static = []
        root.geometry('850x810')
        root.minsize(800, 780)
        root.protocol('WM_DELETE_WINDOW', self.close)
        ttk.Style(root).configure('.', font=('Microsoft YaHei UI', 10))
        panel = ttk.Frame(root, padding=20)
        panel.pack(fill='both', expand=True)
        top = ttk.Frame(panel)
        top.pack(fill='x')
        self.label(top, 'title', font=('Microsoft YaHei UI', 21, 'bold')).pack(side='left')
        self.language_box = ttk.Combobox(top, values=['中文', 'English'], textvariable=self.language, state='readonly', width=10)
        self.language_box.pack(side='right')
        self.language_box.bind('<<ComboboxSelected>>', lambda event: self.refresh())
        self.label(panel, 'scope').pack(anchor='w', pady=(4, 12))
        detect_row = ttk.Frame(panel)
        detect_row.pack(fill='x')
        self.detect_button = self.button(detect_row, 'detect', self.detect_device)
        self.detect_button.pack(side='left')
        self.device_label = ttk.Label(detect_row)
        self.device_label.pack(side='left', padx=12)
        self.label(panel, 'support', foreground='#6a5a30', wraplength=790).pack(anchor='w', pady=(8, 12))
        self.option = ttk.Checkbutton(panel, variable=self.chinese, command=self.refresh)
        self.static.append((self.option, 'chinese'))
        self.option.pack(anchor='w')
        self.description = ttk.Label(panel, wraplength=790)
        self.description.pack(anchor='w', pady=(5, 10))
        file_row = ttk.Frame(panel)
        file_row.pack(fill='x')
        self.entry = ttk.Entry(file_row, textvariable=self.source, state='readonly')
        self.entry.pack(side='left', fill='x', expand=True)
        self.browse = ttk.Button(file_row, command=self.choose_source)
        self.browse.pack(side='right', padx=(8, 0))
        self.package_label = ttk.Label(panel, wraplength=790)
        self.package_label.pack(anchor='w', pady=(5, 0))
        self.label(panel, 'package_help', wraplength=790).pack(anchor='w', pady=(4, 10))
        self.label(panel, 'connect_help', wraplength=790).pack(anchor='w')
        actions = ttk.Frame(panel)
        actions.pack(fill='x', pady=(12, 10))
        self.start_button = self.button(actions, 'start', self.start)
        self.start_button.pack(side='left')
        self.button(actions, 'records', self.open_records).pack(side='right')
        self.restart_option = ttk.Checkbutton(panel, variable=self.restarted)
        self.static.append((self.restart_option, 'restarted'))
        self.restart_option.pack(anchor='w', pady=(2, 5))
        self.verify_button = self.button(panel, 'verify', self.verify)
        self.verify_button.pack(anchor='w')
        self.progress = ttk.Progressbar(panel, mode='indeterminate')
        self.progress.pack(fill='x', pady=12)
        self.output = tk.Text(panel, height=8, wrap='word', state='disabled', font=('Microsoft YaHei UI', 9))
        self.output.pack(fill='both', expand=True)
        self.label(panel, 'persistence', foreground='#7a5500').pack(anchor='w', pady=(8, 0))
        self.refresh()
        self.root.after(100, self.poll)

    @property
    def lang(self):
        return 'en' if self.language.get() == 'English' else 'zh'

    def tr(self, key, **values):
        return translate(key, self.lang, **values)

    def label(self, parent, key, **kwargs):
        widget = ttk.Label(parent, **kwargs)
        self.static.append((widget, key))
        return widget

    def button(self, parent, key, command):
        widget = ttk.Button(parent, command=command)
        self.static.append((widget, key))
        return widget

    def refresh(self):
        self.root.title(self.tr('title') + ' · SonyLanguageUnlock')
        for widget, key in self.static:
            widget.configure(text=self.tr(key))
        self.device_label.configure(text=self.tr('device_info', **self.device) if self.device else self.tr('device_none'))
        self.package_label.configure(text=self.tr('firmware_info', **self.package) if self.package else self.tr('firmware_none'))
        self.description.configure(text=self.tr('description_on' if self.chinese.get() else 'description_off'))
        self.browse.configure(text=self.tr('replace' if self.package else 'select'))
        available = not self.busy
        detected = available and self.device is not None
        for widget in (self.detect_button, self.verify_button, self.restart_option):
            widget.configure(state='normal' if available else 'disabled')
        for widget in (self.option, self.start_button):
            widget.configure(state='normal' if detected else 'disabled')
        self.browse.configure(state='normal' if detected and self.chinese.get() else 'disabled')
        self.entry.configure(state='readonly' if detected and self.chinese.get() else 'disabled')
        self.language_box.configure(state='readonly' if available else 'disabled')
        self.render_history()

    def render_history(self):
        self.output.configure(state='normal')
        self.output.delete('1.0', 'end')
        for message in self.history:
            text = error_text(message, self.lang) if isinstance(message, Exception) else log_text(message, self.lang)
            self.output.insert('end', text + '\n')
        self.output.see('end')
        self.output.configure(state='disabled')

    def log(self, message):
        self.events.put(('log', None, message))

    def launch(self, kind, action):
        if self.busy:
            return
        self.busy = True
        self.refresh()
        self.progress.start(12)
        def work():
            try:
                self.events.put(('done', kind, action()))
            except Exception as exc:
                self.events.put(('error', kind, exc))
        threading.Thread(target=work, daemon=False).start()

    def detect_device(self):
        if self.busy:
            return
        self.device = None
        self.restarted.set(False)
        self.log(UserError('detecting'))
        self.launch('detect', lambda: detection.detect(log=self.log))

    def choose_source(self):
        if self.busy or not self.chinese.get() or self.device is None:
            return
        path = filedialog.askopenfilename(parent=self.root, title=self.tr('select'),
                                         filetypes=[('Sony firmware', '*.DAT *.dat'), ('All files', '*.*')])
        if not path:
            return
        self.package = None
        self.source.set(path)
        self.log(UserError('inspecting'))
        self.launch('package', lambda: firmware.inspect_package(path))

    def start(self):
        if self.busy:
            return
        chinese = self.chinese.get()
        try:
            firmware.check_selection(self.device, chinese, self.package)
            firmware.require_supported(self.device)
        except UserError as exc:
            messagebox.showwarning(self.tr('notice'), error_text(exc, self.lang))
            return
        self.restarted.set(False)
        device, package = dict(self.device), dict(self.package) if chinese else None
        self.log(UserError('starting'))
        self.launch('unlock', lambda: controller.execute(device, chinese, package, self.log))

    def verify(self):
        if self.busy:
            return
        if not self.restarted.get():
            messagebox.showinfo(self.tr('notice'), self.tr('restart_first'))
            return
        self.launch('verify', lambda: workflow.verify_after_restart(self.log, owner_confirmed=True))

    def poll(self):
        while not self.events.empty():
            event, kind, value = self.events.get_nowait()
            if event == 'log':
                self.history.append(value)
                self.render_history()
                continue
            self.busy = False
            self.progress.stop()
            if event == 'error':
                self.history.append(value)
                self.refresh()
                messagebox.showerror(self.tr('stopped'), error_text(value, self.lang))
                continue
            if kind == 'detect':
                self.device = value
            elif kind == 'package':
                self.package = value
            self.refresh()
            if kind in ('package', 'detect') and self.package and self.chinese.get():
                try:
                    firmware.check_selection(self.device, True, self.package)
                except UserError as exc:
                    messagebox.showwarning(self.tr('notice'), error_text(exc, self.lang))
            elif kind == 'unlock':
                messagebox.showinfo(self.tr('notice'), self.tr('await_restart'))
            elif kind == 'verify':
                messagebox.showinfo(self.tr('notice'), self.tr('verified'))
        self.root.after(100, self.poll)

    def open_records(self):
        folder = workflow.state_root()
        folder.mkdir(parents=True, exist_ok=True)
        os.startfile(folder)

    def close(self):
        if self.busy:
            messagebox.showinfo(self.tr('notice'), self.tr('wait_close'))
        else:
            self.root.destroy()


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()
