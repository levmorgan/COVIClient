import Tkinter as tk
import ttk
import tkFileDialog, tkMessageBox, re, socket
import tkSimpleDialog
from tkCustomDialog import Dialog
from NetworkThread import NetworkThread
import tkFont
from Queue import Empty
from collections import defaultdict

def is_error(obj):
    return isinstance(obj, Exception)

def valid_dset(dset):
    '''
    Check to see whether a directory is a valid COVI dataset
    '''
    # TODO: Finish valid_dset
#    print dset
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

class MainWindow:
    def __init__(self, real_root):
        # Set up a network thread
        self.net_thread = NetworkThread()
        self.net_thread.start()
        self.real_root = real_root
        self.real_root.title("COVI")
        self.root = ttk.Frame(real_root)
        root = self.root
        root.pack()
        rootlabel = ttk.Label(root, 
            text="I'm the main window!\nWhen I grow up, I'll be full of widgets!")
        rootlabel.pack()
        center_window(real_root)

        # TODO: Make all of the widgets

        set_state(self.root)
        self.real_root.withdraw()
        init_dialog = tk.Toplevel()
        init_dialog.title("COVI: Choose data source")
        init = InitWindow(init_dialog, self.net_thread)
        center_window(init_dialog)
        root.wait_window(init_dialog)

#        print init.mode

        if init.mode == 'server':
            dset_dialog = ServerDsetWindow(self.real_root,
                                            net_thread=self.net_thread,
                                            title="COVI: %s: Datasets"%init.user_var.get())
            if hasattr(dset_dialog, 'dset'):
                self.dset = dset_dialog.dset
                if type(self.dset) == list:
                    dset_name = '/'.join(self.dset)
                else:
                    dset_name = self.dset
                tkMessageBox.showinfo("We have a dataset!", "It's %s!"%(dset_name))
            else:
                return
        
class NetworkDialog(object):
    #TODO: Test data validation
    def recv_response(self, expected="req ok"):
        '''
        Get the response from the server, handling missing or incorrect responses
        '''
        res = self.net_thread.res_q.get(True, 5)
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

        while True:
            # Validate the response
            if expected == 'req ok' and res == True:
                break
            elif res['type'] == expected:
                break
            else:
                tkMessageBox.showinfo("Unexpected data from the server", 
                                      "COVI got an unexpected response from the server. It's "+
                                      "probably nothing to worry about.")
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
                                "%s is not a valid COVI dataset. "+
                                "Please choose another directory.")
    def validate(self):
        MAX_FIELD_LENGTH = 140
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
            res = self.recv_response()
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
            res = self.recv_response()
            # TODO: stop animation
            res = handle_net_response(res, "Authentication")
            if not res:
                return
            
            self.mode = 'server'
            
        elif self.radio_var.get() == 1:
            # TODO: Go into local dataset mode
            self.mode = 'local'

        tkMessageBox.showinfo("Radical!", "You hit OK! Way to go!")
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
            res = self.recv_response()
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
        res = self.recv_response()
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
            wait = True
            res = self.recv_response()
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
        res = self.recv_response()
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
            res = self.recv_response()
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
        
    def apply(self):
        '''
        Called when Ok is pressed. Load the selected dataset
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
        print visible
        
        # Clear out any children in the tree
        [self.tree.delete(i)
         for i in self.tree.get_children()]
         
        # Get a list of datasets to populate the tree
        self.net_thread.job_q.put(['list'])
        # TODO: start animation
        res = self.recv_response('list')
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
        
        # Insert nodes into the tree
        tree.insert('', 'end', 'list',
                    text='Your Datasets')
        # Sort the lists of datasets
        [dsets[i].sort() for i in dsets if type(dsets[i]) == list]

        for i in dsets['list']:
            tree.insert('list', 'end', i, text=i,
                        open=visible['shared'])

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
