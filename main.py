import tkinter as tk
from tkinter import ttk, messagebox, filedialog  # "CSS" for ttk

from gcode_reader import Part


def add_new_file(show=False):
    root = filedialog.askopenfilename(title="Select file", filetypes=(("Gcode files", "*.gcode"), ("all files", "*.*")))
    if show:
        print("Open file: %s " % root)
    return root


def save_new_file(default_name="", show=False):
    root = filedialog.asksaveasfilename(title="Select file", defaultextension=".gcode", initialfile=default_name, filetypes=(("Gcode", "*.gcode"), ("all files", "*.*")))
    if show:
        print("Save file: %s " % root)
    return root


def quit_confirmation(root):
    if messagebox.askokcancel("Quit", "Do you want to quit?"):
        root.quit()


def popup_message(message):
    if messagebox.showerror("Error", message):
        pass


def success_popup_message(message):
    if messagebox.showinfo("Success", message):
        pass

class GUI(tk.Tk):

    def __init__(self):
        tk.Tk.__init__(self)
        tk.Tk.wm_title(self, "Ironing Experiments")

        self.main_container = tk.Frame(self)
        self.main_container.grid(row=0, column=0, padx=10, pady=5, sticky="n")

        file_settings = ttk.LabelFrame(self.main_container, text="File")
        file_settings.grid(row=0, column=0, padx=5, pady=5, sticky='nwes')
        open_file = ttk.Button(file_settings, text="Open", width=15, command=self.start_ironing_object)
        open_file.grid(row=0, column=0)

        # Defining variables:
        self.ironing_settings = None

        self.part = None

        self.radio_var = None
        self.start_layer = None
        self.end_layer = None
        self.interval = None
        self.list_ironings = None
        self.ironing = None

    def after_file_open(self):
        # OPTIONS READ FROM FILE
        self.read_settings = ttk.LabelFrame(self.main_container, text="Read from file")
        self.read_settings.grid(row=1, column=0, padx=5, pady=5, sticky='nwes')

        tk.Label(self.read_settings, text="File Name:").grid(row=0, column=0, padx=5, sticky='nwe')
        tk.Label(self.read_settings, text=self.part.filename).grid(row=0, column=1, padx=5, sticky='nwe')

        tk.Label(self.read_settings, text="Number of Layers:").grid(row=1, column=0, padx=5, sticky='nwe')
        tk.Label(self.read_settings, text=len(self.part.list_of_layers)).grid(row=1, column=1, padx=5, sticky='nwe')

        tk.Label(self.read_settings, text="Ironing Enabled:").grid(row=2, column=0, padx=5, sticky='nwe')
        tk.Label(self.read_settings, text=self.part.settings["ironing_enabled"]).grid(row=2, column=1, padx=5, sticky='nwe')

        tk.Label(self.read_settings, text="Ironing Flow:").grid(row=3, column=0, padx=5, sticky='nwe')
        tk.Label(self.read_settings, text=self.part.settings["ironing_flow"]).grid(row=3, column=1, padx=5, sticky='nwe')

        tk.Label(self.read_settings, text="Ironing Inset:").grid(row=4, column=0, padx=5, sticky='nwe')
        #tk.Label(self.read_settings, text=self.part.settings["ironing_inset"]).grid(row=4, column=1, padx=5, sticky='nwe')
        tk.Label(self.read_settings, text="??").grid(row=4, column=1, padx=5, sticky='nwe')

        tk.Label(self.read_settings, text="Speed Ironing:").grid(row=5, column=0, padx=5, sticky='nwe')
        #tk.Label(self.read_settings, text=self.part.settings["speed_ironing"]).grid(row=5, column=1, padx=5, sticky='nwe')
        tk.Label(self.read_settings, text="??").grid(row=5, column=1, padx=5, sticky='nwe')

        # OPTIONS FOR IRONING
        self.ironing_settings = ttk.LabelFrame(self.main_container, text="Apply Ironing")
        self.ironing_settings.grid(row=2, column=0, padx=5, pady=5, sticky='nwe')

        self.radio_var = tk.StringVar()
        self.start_layer = tk.StringVar()
        self.end_layer = tk.StringVar()
        self.interval = tk.StringVar()
        self.list_ironings = tk.StringVar()

        self.radio_var.set("opt1")
        self.list_ironings.set("[1,0,1,...,1,0,1]")

        chk_btn_increment = tk.Radiobutton(self.ironing_settings, variable=self.radio_var, text="Use Intervals", value='opt1')
        chk_btn_increment.grid(row=0, column=0, sticky="nw")

        tk.Label(self.ironing_settings, text="Interval").grid(row=1, column=0)
        tk.Spinbox(self.ironing_settings, textvariable=self.interval, from_=1, to=len(self.part.list_of_layers), wrap=True).grid(row=1, column=1, sticky="nw")

        tk.Label(self.ironing_settings, text="Start at Layer").grid(row=2, column=0)
        tk.Spinbox(self.ironing_settings, textvariable=self.start_layer, from_=1, to=len(self.part.list_of_layers), wrap=True).grid(row=2, column=1)

        self.end_layer.set(str(len(self.part.list_of_layers)))
        tk.Label(self.ironing_settings, text="End at Layer", width=8).grid(row=3, column=0)
        tk.Spinbox(self.ironing_settings, textvariable=self.end_layer, from_=1, to=int(self.end_layer.get()), wrap=True).grid(row=3, column=1)

        chk_btn_list = tk.Radiobutton(self.ironing_settings, variable=self.radio_var, text="Use a list", value='opt2')
        chk_btn_list.grid(row=4, column=0, sticky="nw")

        tk.Label(self.ironing_settings, text="Binary list of layers").grid(row=5, column=0)
        tk.Entry(self.ironing_settings, textvariable=self.list_ironings).grid(row=5, column=1)

        # OPTIONS FOR IRONING
        self.advanced_settings = ttk.LabelFrame(self.main_container, text="Advanced Settings")
        self.advanced_settings.grid(row=3, column=0, padx=5, pady=5, sticky='news')

        self.flow_dir = tk.StringVar()
        self.flow_dir.set("opta")

        tk.Label(self.advanced_settings, text="Flow Direction").grid(row=0, column=0)
        #chk_btn_flow_rep = tk.Radiobutton(self.advanced_settings, variable=self.flow_dir, text="Replicate", value='opta')
        #chk_btn_flow_rep.grid(row=0, column=1, sticky="nw")
        chk_btn_flow_par = tk.Radiobutton(self.advanced_settings, variable=self.flow_dir, text="Parallel", value='opta')
        chk_btn_flow_par.grid(row=0, column=1, sticky="nw")
        chk_btn_flow_perp = tk.Radiobutton(self.advanced_settings, variable=self.flow_dir, text="Perpendicular", value='optb')
        chk_btn_flow_perp.grid(row=0, column=2, sticky="nw")

        self.disable_flow = tk.IntVar()
        self.disable_flow.set(0)
        tk.Checkbutton(self.advanced_settings, text="Disable Flow", variable=self.disable_flow).grid(row=1, column=0, sticky="nw")

        self.set_z_offset = tk.IntVar()
        self.z_offset = tk.StringVar()
        self.z_offset.set("0")
        tk.Checkbutton(self.advanced_settings, text="Set Z offset [mm]", variable=self.set_z_offset).grid(row=2, column=0, sticky="nw")
        tk.Entry(self.advanced_settings, textvariable=self.z_offset, width=12).grid(row=2, column=1, sticky="nw")

        self.set_fan_speed = tk.IntVar()
        self.fan_speed = tk.StringVar()
        self.fan_speed.set("-1")
        tk.Checkbutton(self.advanced_settings, text="Set Fan speed [%]", variable=self.set_fan_speed).grid(row=3, column=0, sticky="nw")
        tk.Entry(self.advanced_settings, textvariable=self.fan_speed, width=12).grid(row=3, column=1, sticky="nw")

        #tk.Checkbutton(self.advanced_settings, text="Flow direction").grid(row=4, column=0, sticky="nw")
        #tk.Spinbox(self.advanced_settings, textvariable=self.interval, from_=1, to=self.ironing.number_of_layers, width=10).grid(row=4, column=2, sticky="ne")

        # OPERATIONS
        self.calculate_export = ttk.LabelFrame(self.main_container, text="Operations")
        self.calculate_export.grid(row=4, column=0, padx=5, pady=15, sticky='nwe')
        #ttk.Button(self.calculate_export, text="Calculate", command=self.calculate_ironing).grid(row=0, column=0, pady=5, padx=20)
        #ttk.Button(self.calculate_export, text="Export", command=self.export_ironing).grid(row=0, column=1, pady=5, padx=20)
        ttk.Button(self.calculate_export, text="Apply Ironing", command=self.export_ironing).grid(row=0, column=1, pady=5, padx=20)

    def start_ironing_object(self):
        root = add_new_file()
        print("Open file %s" % root)
        self.part = Part(root)
        self.part.read_file()
        self.part.get_settings_from_file()
        self.part.get_part_instructions()

        if self.part.check_for_ironing():
            self.after_file_open()
        else:
            popup_message("Ironing is disabled")

    def export_ironing(self):
        root = save_new_file(self.part.ironing_file)
        if root != '':

            if self.radio_var.get() == 'opt1':
                start_layer = int(self.start_layer.get()) - 1
                end_layer = int(self.end_layer.get())
                interval = int(self.interval.get())

                list_for_ironing = [0] * len(self.part.list_of_layers)
                for i in range(start_layer, end_layer, interval):
                    list_for_ironing[i] = 1
                print(list_for_ironing)

            elif self.radio_var.get() == 'opt2':
                separate = self.list_ironings.get().split(',')
                if len(separate) != len(self.part.list_of_layers):
                    popup_message("Number of layers mismatch")
                else:
                    list_for_ironing = [int(k) for k in separate]
                    print(list_for_ironing)

            fan_speed = 255 * float(self.fan_speed.get()) / 100
            flow = bool(self.disable_flow.get())
            z_offset = float(self.z_offset.get())
            result = self.part.add_ironing_to_part(list_for_ironing, self.flow_dir.get(), flow, fan_speed, z_offset)

            if result:
                success_popup_message("Ironing caculated with success!")
            else:
                popup_message("Error")
        else:
            popup_message("Choose a file to export")


if __name__ == '__main__':
    app = GUI()
    app.protocol("WM_DELETE_WINDOW", lambda: quit_confirmation(app))
    app.mainloop()