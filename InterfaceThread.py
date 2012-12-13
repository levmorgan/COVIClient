import Tkinter as tk
import ttk
import tkFileDialog, tkMessageBox, re
from tkSimpleDialog import Dialog

def is_error(obj):
    return isinstance(obj, Exception)

def valid_dset(dset):
    '''
    Check to see whether a directory is a valid COVI dataset
    '''
    # TODO: Finish valid_dset
    print dset
    return True

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

class MainWindow:
    def __init__(self, real_root):
        # Set up a network thread
        self.net_thread = NetworkThread()
        self.net_thread.start()

        self.real_root = real_root
        self.root = ttk.Frame(real_root)
        root = self.root
        root.pack()
        rootlabel = ttk.Label(root, text="Fakey fake")
        rootlabel.pack()
        center_window(real_root)

        # TODO: Make all of the widgets

        set_state(self.root)
        self.real_root.withdraw()
        init_dialog = tk.Toplevel()
        init = InitWindow(init_dialog, self.net_thread)
        center_window(init_dialog)
        root.wait_window(init_dialog)

        if init.mode == 'server':
            dset_dialog = ServerDsetWindow(self.real_root,
                                            dset=init.reply,
                                            net_thread=self.net_thread,)
            root.wait_window(dset_dialog)
        



class InitWindow:
    def __init__(self, real_root, net_thread):
        '''
        Create a window that allows a user to log in to a server 
        or to load a local dataset
        '''
        self.net_thread = net_thread
        self.real_root = real_root
        self.root = ttk.Frame(real_root)
        root = self.root
        root.pack()
        top_label = ttk.Label(root, text="Data Source:")
        top_label.pack(anchor=tk.W)

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
        server_radio.pack(anchor=tk.W)
        server_frame.pack(anchor=tk.W)
        print len(server_radio.winfo_children())

        client_radio = ttk.Radiobutton(root, text="Local Dataset",
                                variable=self.radio_var,
                                value=1, 
                                command=self.radio_command)
        client_radio.pack(anchor=tk.W)
        #local_frame.pack(anchor=tk.W, fill=tk.X)
        local_frame.pack(anchor=tk.CENTER, fill=tk.X)

        # Create the server connection frame
        # Create tk variables to hold info about the server connection
        self.addr_var = tk.StringVar()
        self.port_var = tk.IntVar()
        self.port_var.set(14338)
        self.user_var = tk.StringVar()
        self.pass_var = tk.StringVar()

        self. fields = {self.addr_var:"Address",
            self.port_var:"Port",
            self.user_var:"Username",
            self.pass_var:"Password"}

        txt_len = 60

        addr_label = ttk.Label(server_frame, text="Address")
        addr_label.grid(row=0, column=0, sticky=tk.W)
        addr_field = ttk.Entry(server_frame, 
                                textvariable=self.addr_var,
                                width=txt_len)
        addr_field.grid(row=0, column=1, sticky=tk.W)

        port_label = ttk.Label(server_frame, text="Port")
        port_label.grid(row=1, column=0, sticky=tk.W)
        port_field = ttk.Entry(server_frame, 
                                textvariable=self.port_var,
                                width=6)
        port_field.grid(row=1, column=1, sticky=tk.W)

        user_label = ttk.Label(server_frame, text="Username")
        user_label.grid(row=2, column=0, sticky=tk.W)
        user_field = ttk.Entry(server_frame, 
                                textvariable=self.user_var,
                                width=txt_len)
        user_field.grid(row=2, column=1, sticky=tk.W)

        pass_label = ttk.Label(server_frame, text="Password")
        pass_label.grid(row=3, column=0, sticky=tk.W)
        pass_field = ttk.Entry(server_frame, 
                                textvariable=self.pass_var,
                                show=u'\u2022',
                                width=txt_len)
        pass_field.grid(row=3, column=1, sticky=tk.W)

        add_padding(server_frame)

        # Create the local dataset selection frame

        self.dset_var = tk.StringVar()
        self.dset_field = ttk.Entry(local_frame,
                                textvariable=self.dset_var)
        self.dset_field.pack(side=tk.LEFT, anchor=tk.W, fill=tk.X, expand=1)
        #self.dset_field.grid(row=0, column=1, sticky=tk.E+tk.W)

        browse_button = ttk.Button(local_frame,
                                text="Browse",
                                command=self.browse_command)
        browse_button.pack(side=tk.RIGHT, anchor=tk.E)
        #browse_button.grid(row=0, column=1, sticky=tk.E)

        self.radio_command()

        ok_button = ttk.Button(root, text="Ok",
                                command=self.ok_command)
        ok_button.pack(anchor=tk.E)


        # Bind the relevant keys
        #root.grab_set()
        self.real_root.bind("<Return>", self.ok)
   
    def radio_command(self):
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
                                "%s is not a valid COVI dataset. "+
                                "Please choose another directory.")
    def validate(self):
        MAX_FIELD_LENGTH = 140
        for i in self.fields:
            if len(i) > MAX_FIELD_LENGTH:
                tkMessageBox.showwarning("Validation Error",
                    "Field %s has a maximum length of %i"%(
                        self.fields[i], MAX_FIELD_LENGTH))
            if len(i) < 2:
                tkMessageBox.showwarning("Validation Error",
                    "Field %s has a minimum length of %i"%(
                        self.fields[i], 2))
                return 0
            if not re.match("[0-9A-Za-z\-\.]", i):
                tkMessageBox.showwarning("Validation Error",
                    "Invalid characters in %s: %s"%(
                        self.fields[i], 
                        ' '.join(
                            set(
                            re.findall('[^0-9A-Za-z\-\.]')
                            ))))
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
            
        if self.radio_var == 0:
            # Get data from a server
            self.mode = 'server'
            # Authenticate with the server
            self.net_thread.job_q.put(
                ['auth', self.user_var, self.pass_var])
            # TODO: start a progress bar
            response = self.net_thread.res_q.get()
            self.response = response
            
            if is_error(response):
                tkMessageBox.showwarning("Problem During Authentication",
                                        res.message)
                set_state(self.root, state='enabled')
                # TODO: stop progress bar
                return
            
            pass
        else:
            # TODO: Go into local dataset mode
            self.mode = 'local'

        tkMessageBox.showinfo("Radical!", "You hit OK! Way to go!")
        self.real_root.destroy()

class ServerDsetWindow(Dialog):

    
    def rename_command(self):
        pass
    
    
    def delete_command(self):
        pass
    
    
    def share_command(self):
        pass
    
    
    def accept_command(self):
        pass
    
    
    def body(self, root, **kwargs):
        '''
        Create the body of the window, made up of a Treeview
        with the datasets on the server and share requests, and the
        relevant buttons.

        args should be the body of a list response, documented in 
            sendable-json.json
        '''
        self.root = root
        self.net_thread = kwargs['net_thread']
        center_window(self)
        tree = ttk.Treeview(root, selectmode='browse',
                            show="tree")
        
        # Insert nodes into the tree
        if 'dsets' in kwargs:
            dsets = kwargs['dsets']
            tree.insert('', 'end', 'list',
                        text='Your Datasets')
            # Sort the lists of datasets
            [dsets[i].sort() for i in dsets]

            for i in dsets['list']:
                tree.insert('list', 'end', i, text=i)

            tree.insert('', 'end', 'shared', 
                        text="Shared with you")
            for i in dsets['shared']:
                tree.insert('shared', 'end', 'share'+i[0]+'/'+i[2],
                            text='Owner: %s\n%s'%(i[0], i[2]))

            tree.insert('', 'end', 'requests', 
                        text="Share Requests")
            for i in dsets['requests']:
                tree.insert('requests', 'end', 'req'+i[0]+'/'+i[2],
                            text='From: %s\n%s'%(i[0], i[2]))

            tree.insert("", "end", "user's shares", 
                        text="Shared by you")
            for i in dsets["user's shares"]:
                tree.insert("user's shares", "end", 'usrs'+i[0]+"/"+i[2],
                            text="To: %s\n%s"%(i[0], i[2]))

            # Insert 'None' nodes in empty categories
            [tree.insert(i, "end", i+"none", text="None") for i in dsets
                if not dsets[i]]

        tree.pack(anchor=tk.W, side=tk.LEFT)

        button_frame = tk.Frame(root)
        button_frame.pack(anchor=tk.E, padx=(5,0))
        rename_button = ttk.Button(button_frame, text="Rename",
                                    command=self.rename_command)
        rename_button.pack()
        delete_button = ttk.Button(button_frame, text="Delete",
                                    command=self.delete_command)
        delete_button.pack()
        share_button = ttk.Button(button_frame, text="Share",
                                    command=self.share_command)
        share_button.pack()
        accept_button = ttk.Button(button_frame, text="Accept",
                                    command=self.accept_command)
        accept_button.pack()
        





root = tk.Tk()
#init_window = InitWindow(root)
ServerDsetWindow(root, title="Select Dataset", 
                        dsets={'list':[], 'shared':[], 
                        'requests':[], "user's shares":[]})
#MainWindow(root)
center_window(root)
root.mainloop()
