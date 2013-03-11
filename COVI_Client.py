import Tkinter as tk
import ttk
import tkFileDialog, tkMessageBox, tkFont, tkSimpleDialog
import re, socket, os, threading, json, sys, inspect
from tkCustomDialog import Dialog
from NetworkThread import NetworkThread
from Queue import Empty
from collections import defaultdict


try:
    from COVIClient.ProcessingThread import ProcessingThread
except:
    from ProcessingThread import ProcessingThread

def is_error(obj):
    return isinstance(obj, Exception)

def valid_dset(dset):
    '''
    Check to see whether a directory is a valid COVI dataset
    by making sure it's a directory and checking for a few files
    '''
    return bool(os.path.isdir(dset) and 
            os.access(os.path.join(dset, 'clusters.1D'), os.W_OK) and
            os.access(os.path.join(dset, '0.stat.1D'), os.W_OK))

def set_state(widget, state='disabled'):
    '''
    Enable or disable a widget and all its children.
    Disable by default.
    '''
    try:
        widget.configure(state=state)
    except tk.TclError:
        pass
    for child in widget.winfo_children():
        set_state(child, state=state)
'''
def remove_widget(widget, method='pack'):
    children = widget.winfo_children()
    if len(children) == 0:
        if method == 'pack':
            
        elif method == 'grid':
            pass
        else:
            raise ValueError('method must be pack or grid')
        for child in widget.winfo_children():
            pass
'''            

def add_padding(widget, padx='1m', pady='1m'):
    '''
    Add padding to a widget that uses a grid layout
    '''
    cols, rows = widget.grid_size()
    for i in range(cols):
        widget.grid_columnconfigure(i, pad=padx)
    for i in range(rows):
        widget.grid_rowconfigure(i, pad=pady)

def center_window(window):
    '''
    Center a tk window. Only call after the window is populated 
    with widgets.
    '''
    # Hide the window so it doesn't draw in the wrong place
    window.withdraw()
    # Update it
    window.update_idletasks()

    # Center
    x = (window.winfo_screenwidth() - window.winfo_reqwidth()) / 2
    y = (window.winfo_screenheight() - window.winfo_reqheight()) / 2
    window.geometry("+%d+%d" % (x, y))

    # Show
    window.deiconify()

def handle_net_response(res, msg):
    '''
    Handle a response from the network thread. Display an error 
    message & return false if it's an error. Return the response
    otherwise.
    '''
    if is_error(res):
#        print "%s is an error."%(str(res))
        tkMessageBox.showwarning("Problem During %s"%msg,
#                                        response.message)
                                str(res[1]))
        return False
    else: 
#        print "%s is not an error."%(str(res))
        return res


class LocalSpecAndVolWindow(Dialog): 
    def validate(self):
        if not (os.access(self.spec_var.get(), os.W_OK)
                and os.access(self.vol_var.get(), os.W_OK)):
            tkMessageBox.showwarning("Spec and volume file selection", 
                                     "You must specify both a spec and a volume "+
                                     "file")
            return False
        if not self.annot_var.get():
            self.annot_file = None
        return True
    
    def browse_command(self, source):
        if source == 0:
            # Get the spec file location
            self.spec_file = tkFileDialog.askopenfilename(multiple=False,
                    initialdir=self.default_path, 
                    filetypes=[("SUMA spec file", "*.spec")])
            if self.spec_file:
                self.spec_var.set(self.spec_file)
                self.default_path = os.path.dirname(self.spec_file)
        elif source == 1:
            # Get the volume file location
            self.vol_file = tkFileDialog.askopenfilename(multiple=False,
                    initialdir=self.default_path, 
                    filetypes=[("AFNI HEAD file", "*.HEAD"),])
            if self.vol_file:
                self.vol_var.set(self.vol_file)
                self.default_path = os.path.dirname(self.vol_file)
#                               ("AFNI BRIK file", "*.BRIK")])
            # Remove the file extension
#            self.vol_file = os.path.splitext(self.vol_file)[0]
        elif source == 2:
            # Get the annot file location
            self.annot_file = tkFileDialog.askopenfilename(multiple=False,
                    initialdir=self.default_path, 
                    filetypes=[("FreeSurfer annot file", "*.annot")])
            if self.annot_file:
                self.annot_var.set(self.annot_file)
                self.default_path = os.path.dirname(self.annot_file)
        
    def body(self, root, dset_path):
        self.spec_file = ''
        self.vol_file = ''
        self.default_path = dset_path
        title_label = ttk.Label(root, text='Select Spec file and Volume File')
        title_label.grid(row=0, column=0, columnspan=3) 
        
        spec_label = ttk.Label(root, text="Spec file")
        spec_label.grid(row=1, column=0)
        
        self.spec_var = tk.StringVar()
        self.spec_field = ttk.Entry(root, width=60,
                                textvariable=self.spec_var)
        self.spec_field.grid(row=1, column=1)
        
        self.spec_browse_button = ttk.Button(root, text="Browse",
                                             command=lambda: self.browse_command(0))
        self.spec_browse_button.grid(row=1, column=2)
        
        vol_label = ttk.Label(root, text="Volume file")
        vol_label.grid(row=2, column=0)
        
        self.vol_var = tk.StringVar()
        self.vol_field = ttk.Entry(root, width=60,
                                textvariable=self.vol_var)
        self.vol_field.grid(row=2, column=1)
        
        self.vol_browse_button = ttk.Button(root, text="Browse",
                                             command=lambda: self.browse_command(1))
        self.vol_browse_button.grid(row=2, column=2)
        
        annot_label = ttk.Label(root, text="Annot file")
        annot_label.grid(row=3, column=0)
        
        self.annot_var = tk.StringVar()
        self.annot_field = ttk.Entry(root, width=60,
                                textvariable=self.annot_var)
        self.annot_field.grid(row=3, column=1)
        
        self.annot_browse_button = ttk.Button(root, text="Browse",
                                             command=lambda: self.browse_command(2))
        self.annot_browse_button.grid(row=3, column=2)
        
        add_padding(root)
        


class MainWindow:
    def begin_session(self):
        set_state(self.root, 'disabled')
        set_state(self.switch_button, 'enabled')
        self.real_root.withdraw()
        config_name = os.path.join(
           os.path.dirname(inspect.stack()[-1][1]),
           'suma.config')
        try:
            
            config_fi = open(config_name, 'r')
            config = config_fi.read()
            config_fi.close()
            self.suma_file = json.loads(config)["suma"]
            if not self.suma_file:
                raise IOError()
            
                
        except (IOError, KeyError):
            try:
                self.configure()
            except ValueError:
                # We can't continue without a path to SUMA.
                sys.exit(1)
            
            
        # If we're not connected, we need to choose a local dataset or server
        if self.net_thread and self.net_thread.authenticated:
            mode = 'server'
        else:
            init_dialog = tk.Toplevel()
            init_dialog.title("COVI: Choose data source")
            if self.net_thread:
                self.net_thread.job_q.put(["die"])
            self.net_thread = NetworkThread()
            init = InitWindow(init_dialog, self.net_thread)
            center_window(init_dialog)
            root.wait_window(init_dialog)
            mode = init.mode

        if mode == 'server':
            dset_dialog = ServerDsetWindow(self.real_root,
                                            net_thread=self.net_thread,
                                            title="COVI: %s: Datasets"%init.user_var.get())
            if hasattr(dset_dialog, 'dset'):
                self.dset = dset_dialog.dset
                if type(self.dset) == list:
                    dset_name = '/'.join(self.dset)
                else:
                    dset_name = self.dset
                
                if type(self.dset) == list:
                    self.proc_thread = ProcessingThread(dset=self.dset[1], 
                        net_thread=self.net_thread, owner=self.dset[0],
                        suma_file = self.suma_file)
                else:
                    self.proc_thread = ProcessingThread(dset=self.dset, 
                        net_thread=self.net_thread,
                        suma_file = self.suma_file)
                    
                self.proc_thread.start()
            
        elif mode == 'local':
            self.dset = init.dset_var.get()
            # TODO: Load dataset & surfaces
            sv_window = LocalSpecAndVolWindow(self.real_root,
                                              title="COVI: Select Spec "
                                              +"and Volume Files",
                                              dset_path=self.dset)
            
            if sv_window.spec_file and sv_window.vol_file:
                self.spec_file = sv_window.spec_file
                self.vol_file = sv_window.vol_file
                self.annot_file = sv_window.annot_file
                self.proc_thread = ProcessingThread(
                    spec_file=self.spec_file,
                    surfvol_file=self.vol_file,
                    dset_path = self.dset,
                    annot_file = self.annot_file,
                    suma_file = self.suma_file)
                self.proc_thread.start()
                
                # Re-enable main window widgets
                set_state(self.real_root, 'enabled')
            
        
        
        self.real_root.deiconify()
        
    def configure(self):
        config_name = os.path.join(
            os.path.dirname(inspect.stack()[-1][1]),
            'suma.config')
        config_dialog = ConfigDialog(parent=self.root, 
            title='COVI Configuration')
        self.suma_file = config_dialog.suma_file
        if self.suma_file:
            config = {"suma":self.suma_file}
            config_fi = open(config_name, 'w')
            json.dump(config, config_fi, indent=4, separators=(',',':'))
            if self.proc_thread and self.proc_thread.ready():
                self.proc_thread.job_q.put_nowait(["suma_path", 
                    self.suma_file])
            
            return True
        else:
            raise ValueError("The user did not specify the path to SUMA.")
        
    
    def __init__(self, real_root):
        self.proc_thread = False
        self.net_thread = False
        self.real_root = real_root
        self.real_root.resizable(0,0)
        self.real_root.title("COVI")
        self.menu_vars = []
        
        self.real_root.protocol("WM_DELETE_WINDOW", self.cleanup)
        
        # Put all of our widgets inside a frame, not the Toplevel object
        self.root = ttk.Frame(real_root)
        root = self.root
        root.pack(fill=tk.BOTH, expand=tk.YES)
        self.body()
        #rootlabel = ttk.Label(root, 
        #    text="I'm the main window!\nWhen I grow up, I'll be full of widgets!")
        #rootlabel.pack()
        center_window(real_root)
        set_state(self.root, 'disabled')
        set_state(self.switch_button, 'enabled')

        self.begin_session()
        set_state(self.root, 'disabled')
        set_state(self.switch_button, 'enabled')
        self.poll()
    
    def poll(self):
        '''
        Check for events from SUMA.
        '''
        if self.proc_thread:
            if self.proc_thread not in threading.enumerate():
                tkMessageBox.showwarning("Connection to SUMA lost", 
                      "The connection to SUMA has been lost. "+
                      "Reload  your dataset to continue using COVI.")
                self.proc_not_ready()
                self.proc_thread = False
            if self.proc_thread and self.proc_thread.ready():
                try:
                    res = self.proc_thread.res_q.get_nowait()
                    self.proc_thread.res_q.task_done()
                    if res:
                        if res[0] == 'node':
                            self.node_number_label['text'] = '%i'%res[1]
                        elif res[0] == 'cluster':
                            self.cluster_number_label['text'] = '%i'%res[1]
                        elif res[0] == 'area':
                            self.curr_area_label['text'] = res[1]
                        elif res[0] == 'ready':
                            # Re-enable main window widgets
                            set_state(self.real_root, 'enabled')
                except Empty:
                    pass
        
        self.root.after(100, self.poll)
        
    def cleanup(self):
        if self.net_thread:
            self.net_thread.job_q.put_nowait(["close"])
            self.net_thread.job_q.put_nowait(["die"])
        if self.proc_thread:
            self.proc_thread.job_q.put_nowait(["die"])
        self.real_root.quit()
                                            
    def proc_not_ready(self):
        '''
        What to do if no dataset is loaded into SUMA.
        Disable interface widgets that won't work without SUMA 
        and display a message.
        '''
        set_state(self.root, 'disabled')
        set_state(self.switch_button, 'enabled')
        """
        tkMessageBox.showwarning("Warning", 
             "A dataset needs to be loaded into SUMA to do that.")"""
        
    def scale_command(self, event=None):
        threshold = self.threshold.get()
        self.threshold_label['text'] = str(threshold)
        
    def switch_command(self):
        '''
        Switch datasets
        '''
        answer = True
        if self.proc_thread and self.proc_thread.ready():
            answer = tkMessageBox.askyesno("Warning", 
                "This will end your current COVI session. Continue?")
            
        if answer:
            if self.proc_thread:
                self.proc_thread.job_q.put_nowait(["die"])
                self.proc_thread = False
                self.proc_not_ready()
            self.begin_session()
            
    
    def open_command(self):
        pass
    
    def mode_command(self, mode):
        if self.proc_thread and self.proc_thread.ready():
            self.proc_thread.job_q.put_nowait(["shape", mode])
        else:
            self.proc_not_ready()
            
    
    def color_command(self, color):
        if self.proc_thread and self.proc_thread.ready():
            if color == 'annot' and not self.proc_thread.annot:
                tkMessageBox.showerror("Coloring Error", 
                    "Can't use brain area-based coloring without an annot file.")
                self.color_var.set(self.last_color)
                return
            elif color == 'brightness' and self.proc_thread.no_surface:
                tkMessageBox.showerror("Coloring Error", 
                    "Coordinate-based coloring can't be used, since "+
                    "COVI could not find a valid FreeSurfer ASCII surface "+
                    "file for the current surface. You can use the AFNI "+
                    "program ConvertSurface to create a FreeSurfer ASCII "+
                    "file for the current surface.")
                self.color_var.set(self.last_color)
                return
            else:
                self.proc_thread.job_q.put_nowait(["color", color])
                self.last_color = color
            
        else:
            self.proc_not_ready()
    def redraw_command(self):
        if self.proc_thread and self.proc_thread.ready():
            threshold = float(self.threshold.get())
            # Avoid divide by zero error
            threshold = max(threshold, 10**-9)
            self.proc_thread.job_q.put_nowait(["threshold", 
                float(self.threshold.get())/100.])
            self.proc_thread.job_q.put_nowait(["redraw"])
        else:
            self.proc_not_ready()
            
    def relaunch_command(self):
        if self.proc_thread and self.proc_thread.ready():
            self.proc_thread.job_q.put_nowait(['suma'])
        else:
            self.proc_not_ready()
            
    def make_mode_menu(self, root_menu):
        '''
        Make a menu to choose among graph modes.
        '''
        if not hasattr(self, "mode_var"):
            self.mode_var = tk.StringVar()
            self.mode_var.set("sized spheres")
        mode_menu = tk.Menu(root_menu, tearoff=0)
        """
        mode_menu.add_radiobutton(label="Paths", variable=self.mode_var,
                command=lambda: self.mode_command("paths"),
                value="paths")
        """
        mode_menu.add_radiobutton(label="Spheres", variable=self.mode_var,
                command=lambda: self.mode_command("spheres"),
                value="spheres")
        mode_menu.add_radiobutton(label="Sized Spheres", variable=self.mode_var,
                command=lambda: self.mode_command("sized spheres"),
                value="sized spheres")
        return mode_menu
        
    def make_color_menu(self, root_menu):
        '''
        Make a menu to choose among color modes.
        '''
        if not hasattr(self, "mode_var"):
            self.mode_var = tk.StringVar()
        
        if not hasattr(self, "color_var"):
            self.color_var = tk.StringVar()
            self.color_var.set("heat")
        color_menu = tk.Menu(self.edit_menu,tearoff=0)
        color_menu.add_radiobutton(label="Heatmap", 
                command=lambda: self.color_command("heat"),
                variable=self.color_var, value="heat")
        color_menu.add_radiobutton(label="Coordinate-based", 
                command=lambda: self.color_command("brightness"),
                variable=self.color_var, value="brightness")
        color_menu.add_radiobutton(label=" Brain Area-based", 
                command=lambda: self.color_command("annot"),
                variable=self.color_var, value="annot")
        return color_menu
        
    def body(self):
        self.threshold = tk.IntVar(0)
        self.menu = tk.Menu()
        
        self.file_menu = tk.Menu(self.menu, tearoff=0)
        self.file_menu.add_command(label="Open dataset/Connect to server",
                                   command=self.begin_session)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Quit", command=self.cleanup)
        self.menu.add_cascade(label="File", menu=self.file_menu)
        
        self.edit_menu = tk.Menu(self.menu, tearoff=0)
        
        
        self.edit_menu.add_cascade(label="Graph mode", 
                menu=self.make_mode_menu(self.edit_menu))
        
        self.last_color = 'heat'
        
        self.edit_menu.add_cascade(label="Color mode", 
                menu=self.make_color_menu(self.edit_menu)) 
        
        
        self.edit_menu.add_command(label="Relaunch SUMA", 
                                   command=self.relaunch_command)
        self.edit_menu.add_command(label="Reconfigure", 
                                   command=self.configure)
        self.menu.add_cascade(label="Edit", menu=self.edit_menu)
        
        self.real_root.config(menu=self.menu)
        
        
        self.scale = ttk.Scale(self.root, from_=100, to=0, 
                               variable=self.threshold,
                               orient=tk.VERTICAL,
                               command=self.scale_command)
        self.threshold.set(50)
        self.scale.grid(column=0, row=0, rowspan=8, sticky=(tk.N+tk.S),
                        padx='3m', pady='1m')
        self.threshold_label = ttk.Label(self.root, text="0", justify=tk.LEFT)
        self.threshold_label.grid(column=0, row=8)
        self.scale_command()
        
        
        self.node_label = ttk.Label(self.root, text="Node")
        self.node_label.grid(column=1, row=0, sticky=tk.W+tk.E, padx='1m')
        
        self.node_number_label = ttk.Label(self.root, text='%i'%0, width='6',
                                      relief=tk.SUNKEN, justify=tk.RIGHT)
        self.node_number_label.grid(column=1, row=1, sticky=tk.W+tk.E, padx='1m')
        
        
        self.cluster_label = ttk.Label(self.root, text="Cluster")
        self.cluster_label.grid(column=1, row=2, sticky=tk.W+tk.E, padx='1m')
         
        self.cluster_number_label = ttk.Label(self.root, text='%i'%0, width='6',
                                      relief=tk.SUNKEN, justify=tk.RIGHT)
        self.cluster_number_label.grid(column=1, row=3, sticky=tk.W+tk.E, padx='1m')
        
        self.area_label = ttk.Label(self.root, text="Area") 
        self.area_label.grid(column=1, row=4, sticky=tk.W+tk.E, padx='1m')
        self.curr_area_label = ttk.Label(self.root, text='',
                                      relief=tk.SUNKEN, justify=tk.RIGHT)
        self.curr_area_label.grid(column=1, row=5, sticky=tk.W+tk.E, padx='1m')

        """
        self.open_button = ttk.Button(self.root, text= "Open\nDataset",
                                        command=self.open_command)
        self.open_button.grid(column=1, row=3, sticky=tk.W+tk.E, padx='1m')
        """
        self.switch_button = ttk.Button(self.root, text= "Switch\nDataset",
                                        command=self.switch_command)
        self.switch_button.grid(column=1, row=6, sticky=tk.W+tk.E, padx='1m')
        self.mode_button = ttk.Menubutton(self.root, text= "Graph\nMode")
        self.mode_button['menu'] = self.make_mode_menu(self.mode_button)
        self.mode_button.grid(column=1, row=7, sticky=tk.W+tk.E, padx='1m')
        self.color_button = ttk.Menubutton(self.root, text= "Color\nMode")
        self.color_button['menu'] = self.make_color_menu(self.color_button)
        self.color_button.grid(column=1, row=8, sticky=tk.W+tk.E, padx='1m')
        self.redraw_button = ttk.Button(self.root, text= "Redraw",
                                        command=self.redraw_command)
        self.redraw_button.grid(column=0, row=9, sticky=(tk.W+tk.E), 
                                columnspan=2, padx='1m')
        add_padding(self.root)
        
class ConfigDialog(Dialog):
    def browse_command(self, source):
        if source == 0:
            # Get the suma file location
            self.suma_file = tkFileDialog.askopenfilename(multiple=False, 
                initialfile='suma')
                    
            if self.suma_file:
                self.suma_var.set(self.suma_file)
                self.default_path = os.path.dirname(self.suma_file)
    
    def validate(self):
        return (os.access(self.suma_var.get(), os.W_OK) 
                and os.path.basename(self.suma_var.get()) == 'suma')
    
    def body(self, root):
        self.suma_file = ''
        title_label = ttk.Label(root, text='COVI needs to use SUMA, but its '+
            'location can vary on different systems.\nPlease select your SUMA '+
            'executable so COVI will know where to find it.')
        title_label.grid(row=0, column=0, columnspan=3, sticky=tk.W) 
        
        
        self.suma_var = tk.StringVar()
        self.suma_field = ttk.Entry(root, width=60,
                                textvariable=self.suma_var)
        self.suma_field.grid(row=1, column=0)
        
        self.suma_browse_button = ttk.Button(root, text="Browse",
                                             command=lambda: self.browse_command(0))
        self.suma_browse_button.grid(row=1, column=1)
        
        add_padding(root)
        

class NetworkDialog(object):
    #TODO: Test data validation
    def recv_response(self, expected="req ok"):
        '''
        Get the response from the server, handling missing or incorrect responses
        '''
        try:
            res = self.net_thread.res_q.get(True, 5)
        except Empty:
            res = None
        
        wait = True
        while wait and not res:
            try:
                res = self.net_thread.res_q.get(True, 5)
                wait = False
            except Empty:
                wait = tkMessageBox.askyesno("Network Issue", 
                                      "The response from the server is"+
                                      " taking longer than expected. "+
                                      "Continue waiting?")
        if wait == False:
            return False

        # Go through responses from the server until we find the 
        # one that we want
        while True:
            # Validate the response
            if expected == 'req ok' and res == True:
                break
            elif type(res) == dict and res['type'] == expected:
                break
            elif isinstance(res, Exception):
                return res
            else:
                tkMessageBox.showinfo("Unexpected data from the server", 
                                      "COVI got an unexpected response from the server. It's "+
                                      "probably nothing to worry about.")
                # TODO: Remove debug output
                print "Unexpected response:"
                print res
                # If the data isn't valid and there isn't any more, return False
                if self.net_thread.res_q.empty():
                    return False
                
                res = self.net_thread.res_q.get_nowait()
        
        return res

class InitWindow(NetworkDialog):
    def __init__(self, real_root, net_thread):
        '''
        Create a window that allows a user to log in to a server 
        or to load a local dataset
        '''
        super(InitWindow, self).__init__()
        self.net_thread = net_thread
        self.net_thread.start()
        self.real_root = real_root
        self.real_root.resizable(0,0)
        self.root = ttk.Frame(real_root)
        root = self.root
        root.pack(fill=tk.BOTH, expand=tk.YES)
        top_label = ttk.Label(root, text="Data Source:")
        top_label.pack(anchor=tk.W, padx='1m', pady='0.5m')
        # can be 'local', 'server', or '' (cancelled)
        self.mode = ''

        # Set up frames
        self.server_frame = ttk.Frame(root)
        server_frame = self.server_frame

        self.local_frame = ttk.Frame(root)
        local_frame = self.local_frame

        # Create a radio button that activates the server section
        self.radio_var = tk.IntVar()
        self.radio_var.set(0)
        server_radio = ttk.Radiobutton(root, text="Server",
                                variable=self.radio_var,
                                value=0, 
                                command=self.radio_command)
        server_radio.pack(anchor=tk.W, padx='1m')
        server_frame.pack(anchor=tk.W, fill=tk.BOTH, expand=tk.YES, padx='1m')

        client_radio = ttk.Radiobutton(root, text="Local Dataset",
                                variable=self.radio_var,
                                value=1, 
                                command=self.radio_command)
        client_radio.pack(anchor=tk.W, padx='1m')
        #local_frame.pack(anchor=tk.W, fill=tk.X)
        local_frame.pack(anchor=tk.CENTER, fill=tk.X, padx='1m')

        # Create the server connection frame
        # Create tk variables to hold info about the server connection
        self.addr_var = tk.StringVar()
        self.addr_var.set(socket.gethostname())
        self.port_var = tk.IntVar()
        self.port_var.set(14338)
        self.user_var = tk.StringVar()
        self.pass_var = tk.StringVar()

        self.fields = [
            self.addr_var,
            self.port_var,
            self.user_var,
            self.pass_var,
            ]

        self.field_names = {
            str(self.addr_var):"Address",
            str(self.port_var):"Port",
            str(self.user_var):"Username",
            str(self.pass_var):"Password"}

        txt_len = 60

        addr_label = ttk.Label(server_frame, text="Address")
        addr_label.grid(row=0, column=0, sticky=tk.W, padx='1m')
        addr_field = ttk.Entry(server_frame, 
                                textvariable=self.addr_var,
                                width=txt_len)
        addr_field.grid(row=0, column=1, sticky=(tk.W+tk.E), padx='1m')

        port_label = ttk.Label(server_frame, text="Port")
        port_label.grid(row=1, column=0, sticky=tk.W, padx='1m')
        port_field = ttk.Entry(server_frame, 
                                textvariable=self.port_var,
                                width=6)
        port_field.grid(row=1, column=1, sticky=(tk.W+tk.E), padx='1m')

        user_label = ttk.Label(server_frame, text="Username")
        user_label.grid(row=2, column=0, sticky=tk.W, padx='1m')
        user_field = ttk.Entry(server_frame, 
                                textvariable=self.user_var,
                                width=txt_len)
        user_field.grid(row=2, column=1, sticky=(tk.W+tk.E), padx='1m')

        pass_label = ttk.Label(server_frame, text="Password")
        pass_label.grid(row=3, column=0, sticky=tk.W, padx='1m')
        pass_field = ttk.Entry(server_frame, 
                                textvariable=self.pass_var,
                                show=u'\u2022',
                                width=txt_len)
        pass_field.grid(row=3, column=1, sticky=(tk.W+tk.E), padx='1m')

        add_padding(server_frame)

        # Create the local dataset selection frame

        self.dset_var = tk.StringVar()
        self.dset_field = ttk.Entry(local_frame,
                                textvariable=self.dset_var)
        self.dset_field.pack(side=tk.LEFT, anchor=tk.W, fill=tk.X, 
                             expand=True, padx='1m')
        #self.dset_field.grid(row=0, column=1, sticky=tk.E+tk.W)

        browse_button = ttk.Button(local_frame,
                                text="Browse",
                                command=self.browse_command)
        browse_button.pack(side=tk.RIGHT, anchor=tk.E)
        #browse_button.grid(row=0, column=1, sticky=tk.E)

        self.radio_command()

        ok_button = ttk.Button(root, text="Ok",
                                command=self.ok_command)
        ok_button.pack(anchor=tk.E, padx='1m', pady='1m')


        # Bind the relevant keys
        #root.grab_set()
        self.real_root.bind("<Return>", self.ok_command)
   
    def radio_command(self):
        '''
        Enable either the server controls or dataset selection controls,
        depending on what radio button was clicked
        '''
        if self.radio_var.get() == 0:
            set_state(self.server_frame, state='enabled')
            set_state(self.local_frame)
        else:
            set_state(self.local_frame, state='enabled')
            set_state(self.server_frame)

    def browse_command(self):
        path = tkFileDialog.askdirectory(mustexist=True)
        if not path:
            return
        if valid_dset(path):
            self.dset_var.set(path)
        else:
            tkMessageBox.showwarning("Error",
                                "%s is not a valid COVI dataset. "%path+
                                "Please choose another directory.")
    def validate(self):
        MAX_FIELD_LENGTH = 140
        if self.radio_var.get() == 0:
            # Check server-related fields
            for i in self.fields:
                value = str(i.get())
                if len(value) > MAX_FIELD_LENGTH:
                    tkMessageBox.showwarning("Validation Error",
                        "Field %s has a maximum length of %i"%(
                            self.field_names[str(i)], MAX_FIELD_LENGTH))
                if len(value) < 2:
                    tkMessageBox.showwarning("Validation Error",
                        "Field %s has a minimum length of %i"%(
                            self.field_names[str(i)], 2))
                    return 0
                if not re.match("[0-9A-Za-z\-\.]", value):
                    tkMessageBox.showwarning("Validation Error",
                        "Invalid characters in %s: %s"%(
                            self.field_names[str(i)], 
                            ' '.join(
                                set(
                                re.findall('[^0-9A-Za-z\-\.]')
                                ))))
                    return 0
            return 1
        else:
            # Check client-related fields
            if valid_dset(self.dset_var.get()):
                return 1
            else:
                return 0
                
    def cleanup(self):
        '''
        Cleanup method, called when 'Cancel' is clicked but before
        the window is closed.
        '''
        self.mode = ''

    def ok_command(self, event=None):
        if not self.validate():
            return
            
        if self.radio_var.get() == 0:
            # MODE: Get data from a server
            # Connect to the server
            self.net_thread.job_q.put(
                ['connect', self.addr_var.get(), int(self.port_var.get())])
            # TODO: start an animation
#            res = self.net_thread.recv_response()
            res = self.net_thread.recv_response()
            # TODO: stop animation
            res = handle_net_response(res, "Connection")
            if not res:
                return
            
            
            # Authenticate with the server
            print "Trying to auth"
            self.net_thread.job_q.put(
                ['auth', self.user_var.get(), self.pass_var.get()])
            # TODO: start an animation
            print "Got auth response"
            res = self.net_thread.recv_response()
            # TODO: stop animation
            res = handle_net_response(res, "Authentication")
            if not res:
                return
            else:
                self.net_thread.set_auth(True)
            self.mode = 'server'
            
        elif self.radio_var.get() == 1:
            # TODO: Go into local dataset mode
            self.mode = 'local'

        self.real_root.destroy()

class ServerDsetWindow(Dialog, NetworkDialog):
    #TODO: Handle broken pipe
    '''
    A dialog to load and modify datasets on the server
    
    TODO:
        rename_command: Dialog box w/text input
        delete_command: Confirmation dialog
        share_command: text input dialog
        accept_command: confirmation dialog
    '''
    
    def rename_command(self):
        item = self.tree.selection()[0]
        item_details = self.tree.item(item)
        parent = self.tree.parent(item)
        
        # If this is a valid item to rename, rename it
        if (parent and parent != 'requests' and 
            item_details['text'] != 'None' and parent != 'shared'):
            new = tkSimpleDialog.askstring("Rename a dataset", 
                                           "Input the new name for dataset %s."%item)
            if not new:
                return
            
            self.net_thread.job_q.put_nowait(["rename", item, new])
            
            #Make sure the rename succeeded
            #TODO: Start and stop animation
            res = self.net_thread.recv_response()
            handle_net_response(res, "Rename")
            if res:
                self.update_tree()
            
        elif parent == 'shared':
            tkMessageBox.showinfo("Can't rename dataset", 
                                  "You can only rename valid datasets that you own.")
            
    
    
    def delete_command(self):
        item = self.tree.selection()[0]
        item_details = self.tree.item(item)
        parent = self.tree.parent(item)
        
        ask = lambda x: tkMessageBox.askyesno("Delete dataset", 
                        "Are you sure you want to delete %s?"%x)
        
        # If this is a valid item to delete, delete it
        if parent == 'list':
            if not ask(item):
                return
            self.net_thread.job_q.put_nowait(["remove", item])
            
        elif parent == 'shared':
            owner, dset = item_details['values']
            if not ask('/'.join([owner, dset])):
                return
            self.net_thread.job_q.put_nowait(["remove_shared", dset, owner])
            
        elif parent == "user's shares":
            recipient, dset = item_details['values']
            if not ask('/'.join([recipient, dset])):
                return
            self.net_thread.job_q.put_nowait(["unshare", dset, recipient])
        
        elif parent == "requests":
            owner, dset = item_details['values']
            if not ask('request '+'/'.join([owner, dset])):
                return
            self.net_thread.job_q.put_nowait(["share_response", dset, owner, 0])
        #TODO: Start and stop animation
        res = self.net_thread.recv_response()
        handle_net_response(res, "Deletion")
        if res:
            self.update_tree()
    
    def copy_command(self):
        item = self.tree.selection()[0]
        item_details = self.tree.item(item)
        parent = self.tree.parent(item)
        
        if parent == "list" or parent == "shared":
            new = tkSimpleDialog.askstring("Copy a Dataset", 
                "What should the new dataset's name be?")
            
            # If the user cancelled, return
            if not new:
                return
            
            #TODO: Start and stop animation
            if parent == "list":
                self.net_thread.job_q.put_nowait(
                    ["copy", item, new])
            else:
                owner, old = item_details['values'] 
                self.net_thread.job_q.put_nowait(
                    ["copy_shared", old, new, owner])
            
            # TODO: Start an animation
            res = self.net_thread.recv_response()
            handle_net_response(res, "Copying")
            self.update_tree()
            
            res = ''
            
            if res:
                handle_net_response(res, "Copying")
            
            
            
    
    def share_command(self):
        item = self.tree.selection()[0]
        item_details = self.tree.item(item)
        parent = self.tree.parent(item)
        
        if parent == "list":
            recipient = tkSimpleDialog.askstring("Share a Dataset", 
                "Which user would you like to share %s with?"%item)
            if recipient:
                self.net_thread.job_q.put_nowait(["share", item, recipient, 0])
        else:
            return
        #TODO: Add re-sharing of shared datasets
        
        #TODO: Start and stop animation
        res = self.net_thread.recv_response()
        handle_net_response(res, "Sharing")
        if res:
            self.update_tree()
    
    
    def accept_command(self):
        item = self.tree.selection()[0]
        item_details = self.tree.item(item)
        parent = self.tree.parent(item)
        
        if parent == "requests":
            owner, dset = item_details['values']
            self.net_thread.job_q.put_nowait(["share_response", dset, owner, 1])
            #TODO: Start and stop animation
            res = self.net_thread.recv_response()
            handle_net_response(res, "Response Acceptance")
            if res:
                self.update_tree()
        else:
            tkMessageBox.showwarning("Can't Accept Request", 
                                     "%s is not a share request."%item)
            
    def info_command(self):
        item = self.tree.selection()[0]
        item_details = self.tree.item(item)
        parent = self.tree.parent(item)
        
        print "Item: ",
        print item
        print "Item details: "
        print item_details
        print "Parent: "
        print parent
            
    def TreeviewSelect_command(self, event):
        item = self.tree.selection()[0]
        item_details = self.tree.item(item)
        parent = self.tree.parent(item)
        
        if item_details['text'] == 'None' or parent == '':
            set_state(self.button_frame, 'disabled')
            set_state(self.refresh_button, 'enabled')
            return
        
        set_state(self.button_frame, 'enabled')
        
        
        if parent != 'list':
            set_state(self.share_button, 'disabled')
            set_state(self.rename_button, 'disabled')
            
        if parent != "list" and parent != 'shared':
            set_state(self.copy_button, 'disabled')
        
        if parent != "requests":
            set_state(self.accept_button, 'disabled')    
            
    def validate(self):
        '''
        Called when Ok is pressed. Makes sure a valid dataset is selected.
        '''
        
        item = self.tree.selection()[0]
        item_details = self.tree.item(item)
        parent = self.tree.parent(item)
        
        # If a valid dataset is selected, store which it is so the main window
        # can load it
        if (parent == 'list' or parent == 'shared' and 
            item_details['text'] != "None"):
            if parent == 'shared':
                self.dset = item_details['values']
            else:
                self.dset = item
            return True
        tkMessageBox.showwarning("Can't load dataset", 
            "You can only load datasets you own or ones that are shared with you.")
        return False
        
        
    def sortby(self, tree, col, descending):
        '''
        sort tree contents when a column header is clicked on
        
        from: 
        http://www.daniweb.com/software-development/python/threads/350266/creating-table-in-python
        '''
        
        # TODO: Re-implement
        
        # grab values to sort
        data = [(tree.set(child, col), child) \
            for child in tree.get_children('')]
        # if the data to be sorted is numeric change to float
        #data =  change_numeric(data)
        # now sort the data in place
        data.sort(reverse=descending)
        for ix, item in enumerate(data):
            tree.move(item[1], '', ix)
        # switch the heading so it will sort in the opposite direction
        tree.heading(col, command=lambda col=col: self.sortby(tree, col, \
            int(not descending)))
    
    def update_tree(self):
        tree = self.tree
        
        children = tree.get_children()
        # Store which categories are expanded in the tree
        visible = defaultdict(lambda: False, 
                              ((i, bool(tree.item(i)['open'])) for i in children))
        
        # Clear out any children in the tree
        [self.tree.delete(i)
         for i in self.tree.get_children()]
         
        # Get a list of datasets to populate the tree
        self.net_thread.job_q.put(['list'])
        # TODO: start animation
        res = self.net_thread.recv_response('list')
        # TODO: stop animation
        handle_net_response(res, "Dataset Retrieval")
        if not res:
            return
        try:
            # Try to parse out the dataset list
            dsets = res
                
            # If the queue is empty and we didn't get a response
            if not res:
                raise KeyError
                
        except KeyError:
            # TODO: create a real error message
            print "Could not get datasets! Key Error!"
            print "res: ",
            print res
            dsets = {'list':[], 'shared':[], 'requests':[], "user's shares":[]} 
        
        # Sort the lists of datasets
        [dsets[i].sort() for i in dsets if type(dsets[i]) == list]
        
        # Insert nodes into the tree
        tree.insert('', 'end', 'list',
                    text='Your Datasets', open=visible['list'])

        for i in dsets['list']:
            tree.insert('list', 'end', i, text=i)

        tree.insert('', 'end', 'shared', 
                    text="Shared with you", 
                    open=visible['shared'])
        for i in dsets['shared']:
            tree.insert('shared', 'end', values=(i[0], i[2]),
                        text=i[2])

        tree.insert('', 'end', 'requests', 
                    text="Share Requests",
                    open=visible['requests'])
        for i in dsets['requests']:
            tree.insert('requests', 'end', values=(i[0], i[2]),
                        text=i[2])

        tree.insert("", "end", "user's shares", 
                    text="Shared by you",
                    open=visible["user's shares"])
        for i in dsets["user's shares"]:
            tree.insert("user's shares", "end", values=(i[1], i[2]),
                        text=i[2])

        # Insert 'None' nodes in empty categories
        [tree.insert(i, "end", i+"none", text="None") for i in dsets
            if not dsets[i]]
    
    
    def body(self, root, **kwargs):
        '''
        Create the body of the window, made up of a Treeview
        with the datasets on the server and share requests, and the
        relevant buttons.

        kwargs should be:
            net_thread=a NetworkThread object
        '''
        self.root = root
        self.resizable(0,0)
        self.net_thread = kwargs['net_thread']
        
        self.tree_columns = ["From/To"]
        
        self.tree = ttk.Treeview(root, selectmode='browse',
                            columns=self.tree_columns, #show="tree",
                            displaycolumns=self.tree_columns,
                            )
        # TODO: Re-implement 
        # Column formatting from
        # http://www.daniweb.com/software-development/python/threads/350266/creating-table-in-python
        for col in self.tree_columns:
            self.tree.heading(col, text=col.title(),
                command=lambda c=col: self.sortby(self.tree, c, 0))
            # adjust the column's width to the header string
            self.tree.column(col,
                width=tkFont.Font().measure(col.title()))
        
        # Update self.tree with dataset information
        self.update_tree()
        self.tree.pack(anchor=tk.W, side=tk.LEFT)
        self.bind("<<TreeviewSelect>>", self.TreeviewSelect_command)

        self.button_frame = tk.Frame(root)
        self.button_frame.pack(anchor=tk.E, padx=(5,0))
        button_frame = self.button_frame
        self.rename_button = ttk.Button(button_frame, text="Rename",
                                    command=self.rename_command, 
                                    state='disabled')
        
        self.rename_button.pack()
        self.delete_button = ttk.Button(button_frame, text="Delete",
                                    command=self.delete_command, 
                                    state='disabled')
        self.delete_button.pack()
        self.copy_button = ttk.Button(button_frame, text="Copy",
                                      command=self.copy_command,
                                      state='disabled')
        self.copy_button.pack()
        self.share_button = ttk.Button(button_frame, text="Share",
                                    command=self.share_command, 
                                    state='disabled')
        self.share_button.pack()
        self.accept_button = ttk.Button(button_frame, text="Accept",
                                    command=self.accept_command, 
                                    state='disabled')
        self.accept_button.pack()
        
        self.refresh_button = ttk.Button(button_frame, text="Refresh",
                                    command=self.update_tree)
        self.refresh_button.pack()
        
        #TODO: Remove info button
        self.info_button = ttk.Button(button_frame, text="Info",
                                    command=self.info_command)
        self.info_button.pack()
        

        



if __name__ == '__main__':
    root = tk.Tk()
    #init_window = InitWindow(root)
    '''
    ServerDsetWindow(root, title="Select Dataset", 
                            dsets={'list':[], 'shared':[], 
                            'requests':[], "user's shares":[]})
                            '''
    MainWindow(root)
    center_window(root)
    root.v = True
    root.mainloop()
