'''
Created on Nov 28, 2012

@author: morganl
'''
import itertools, subprocess, socket, re, signal, sys, os, time
from traceback import print_exc
#from math import sqrt
from threading import Thread
from Queue import Queue, Empty
from tempfile import mkdtemp
import tkMessageBox
class ProcessingThread(Thread):
    
    def ready(self):
        '''
        Return True if there is an established SUMA session
        '''
        return hasattr(self, "suma") and self.suma.poll() == None
    
    def __init__(self, 
                 # Args for client mode
                 spec_file=None, surfvol_file=None, dset_path=None,
                 # Args for server mode 
                 dset=None, net_thread=None, owner=None):
        '''
        Constructor. Can take two sets of arguments to operate 
        in client or server mode.
        
        Client mode:
        spec_file: The path to a SUMA spec file
        surfvol_file: The path to an AFNI HEAD file
        dset_path: The path to a directory containing a clusters.1D 
                   and .stat.1D files
        
        Server mode:
        dset: The name of the dataset to request from the server
        net_thread: A COVI network thread connected to the server
        owner: The dataset's owner, if it's a shared dataset. 
        '''
        Thread.__init__(self)
        
        if spec_file and surfvol_file and dset_path:
            self.spec_file = spec_file
            self.surfvol_file = surfvol_file
            self.dset_path = dset_path
            self.mode = 'local'
        
        elif dset and net_thread:
            print "dset: %s"%(dset)
            self.dset = dset
            self.net_thread = net_thread
            if owner:
                self.owner = owner
            else:
                self.owner = False
            self.mode = "server"
        
        else:
            raise ValueError("ProcessingThreadClass needs the arguments:\n"+
                             "spec_file, surfvol_file, and dset_path to "+
                             "operate in client mode, or:\n"+
                             "dset and net_thread to operate in server mode.")
        
        self.do_file = 'shapes'
        self.selected_cluster = None
        self.job_q = Queue()
        self.res_q = Queue()
        self.cont = True
        self.threshold = 0.5
        
        # Set default shape and color mode
        self.shape = 'sized spheres'
        self.color = 'heat'
        self.shapes = itertools.cycle(['paths', "spheres", "sized spheres"])
        self.colors = itertools.cycle(["brightness", "heat"])

    def get_matrix(self, cluster_num):
        if self.mode == 'server':
            self.net_thread.job_q.put(["matrix", self.dset, cluster_num])
            raw_matrix = self.net_thread.recv_response(expected='binary')
            if not raw_matrix:
                return None
            raw_matrix = [i for i in raw_matrix.split('\n') if i]            
        else:
            try:
                print "Starting to read stats"
                stat_fi = open(os.path.join(self.dset_path, 
                        '%i.stat.1D' % self.clust[self.surface_nodeid]), 
                    'r')
                raw_matrix = stat_fi.readlines()
                stat_fi.close()
                print 'Loaded matrix ok'
            except IOError:
                #TODO: Handle a file error
                raise
            
        print raw_matrix
        matrix = [float(i) for i in raw_matrix]
        # Map nodes to correlations
        matrix = zip(self.draw_here, matrix)    
          
        return matrix
    
    def fetch_initial_data(self):
        '''
        In server mode, download the surface, volume, and cluster files we 
        need to start the session.
        '''
        #TODO: Handle all the exceptions in this method.
        print self.temp_dir
        if not self.mode == 'server':
            raise ValueError(
                "fetch_initial_data can only be used in server mode.")
        
        if self.owner:
            self.net_thread.job_q.put(['shared_cluster', self.dset, 
                                       self.owner])
        else:
            self.net_thread.job_q.put(['cluster', self.dset])
        raw_clusters = self.net_thread.recv_response(None)
            
        self.parse_clusters(raw_clusters.split('\n'))
        
        if self.owner:
            self.net_thread.job_q.put(['shared_surface', self.dset, 
                                       self.owner, self.temp_dir])
        else:
            self.net_thread.job_q.put(['surface', self.dset, self.temp_dir])
        self.dset_path = self.net_thread.recv_response(None)
        
        files = os.listdir(self.dset_path)
        
        '''
        print files
        print [os.path.splitext(file) for file in files]
        print [file for file in files 
                              if os.path.splitext(file)[1] == '.spec' or 
                              os.path.splitext(file)[1] == '.SPEC']
        print [file for file in files 
                              if os.path.splitext(file)[1] == '.head' or 
                              os.path.splitext(file)[1] == '.HEAD']
        '''
        try:
            self.spec_file = [file for file in files 
                              if os.path.splitext(file)[1] == '.spec' or 
                              os.path.splitext(file)[1] == '.SPEC'][0]
            self.surfvol_file = [file for file in files 
                              if os.path.splitext(file)[1] == '.head' or 
                              os.path.splitext(file)[1] == '.HEAD'][0]
            self.spec_file = os.path.join(self.dset_path, self.spec_file)
            self.surfvol_file = os.path.join(self.dset_path, self.surfvol_file)
            
            print "Spec file: %s"%(self.spec_file)
            print "Surfvol file: %s"%(self.surfvol_file)
        except IndexError:
            tkMessageBox.showerror("Error", 
                "The dataset did not contain a valid spec or surfvol file. "+
                "Check the dataset and try uploading it again.")
            raise
        
        
    def parse_clusters(self, clust_dat):
        '''
        Parse a cluster file and store it in self.clust.
        Takes a file object or a cluster file split at '\n'
        '''
        # Preallocate the cluster array
        self.clust = [0 for i in clust_dat if i != ''] 
        # Draw the graphic for each cluster at the first node in the cluster
        #TODO: Make sure the center vertex is always first 
        self.draw_here = []
        cluster = 0
        first = True
        for i in clust_dat:
        # Empty lines signify a new cluster
            if i == '':
                cluster += 1
                first = True
            else:
                try:
                    self.clust[int(i)] = cluster
                    if first:
                        self.draw_here.append(int(i))
                        first = False
                except IndexError:
                    print "Index error:"
                    print "int(i) == %i" % (int(i))
                    print "len(clust) == %i" % (len(self.clust))
        
        #            assert cluster[-1] ==
        print 'Loaded cluster file ok'

    def launch_suma_connect(self):
        '''
        Launch SUMA, initiate a NIML connection, and load the surface that 
        SUMA is loading 
        '''
        if self.mode == 'server':
            self.temp_dir = mkdtemp()
            #TODO: Handle errors from fetch_initial_data
            self.fetch_initial_data()
            
        self.svr_socket.listen(5)
        
        # SUMA has a bug with spaces in the path to surfvol, so set the cwd
        # to the surfvol directory.
        cwd, surfvol = os.path.split(self.surfvol_file)
        self.suma = subprocess.Popen(["/home/morganl/workspace/AFNI/Debug/afni_src/suma", 
                "-spec", self.spec_file, 
                "-sv", surfvol, 
                "-niml", 
                "-ah", "127.0.0.1", 
                "-np", str(self.np)], cwd=cwd)
        
        #                    stderr=subprocess.PIPE,
        #                    stdout=subprocess.PIPE)
        # TODO: Add a message telling the user to press 't' in SUMA
        # Tell SUMA to initiate the NIML connection
        """
        print ' '.join(["/home/morganl/workspace/AFNI/Debug/afni_src/DriveSuma",
                    "-com", "viewer_cont", "-key", "'t'", "-np", "53211"])
        """
        time.sleep(3)
        DriveSuma = subprocess.Popen(["/home/morganl/workspace/AFNI/Debug/afni_src/DriveSuma",
                    "-com", "viewer_cont", "-key", "t", "-np", str(self.np)])
        """
        DriveSuma = subprocess.Popen(["/home/morganl/workspace/AFNI/Debug/afni_src/DriveSuma",
                    "-com", "viewer_cont", "-key", "'t'"])
                    """
        print 'Sent key to SUMA'
    
        print "Waiting for connection from SUMA"
        self.svr_socket.settimeout(60)
        self.socket, address = self.svr_socket.accept()
        self.socket.settimeout(0.5)
        print "Connection accepted"
    # Receive the big chunk of data SUMA sends on connect
        print "Starting to receive data"
        data = self.recv_data()
        print "Data chunk received"
    # Parse info out of the data we received
        num_nodes, self.volume_idcode, self.surface_idcode, self.surface_label = re.findall("""<SUMA_ixyz\n  ni_form="binary.lsbfirst"\n  ni_type="int,3\*float"\n  ni_dimen="([0-9]+?)"\n  volume_idcode="(.*?)"\n  surface_idcode="(.*?)".*\n  surface_label="(.*?)".*""", data, flags=re.DOTALL)[0]
        self.num_nodes = int(num_nodes)
    # Decode the cluster file
    # Load the cluster information
        if self.mode == 'local':
            try:
                print "Starting to read clusters"
                clust_fi = open(os.path.join(self.dset_path, 'clusters.1D'))
                clust_dat = clust_fi.read().split('\n')
                clust_fi.close() 
                self.parse_clusters(clust_dat)
            except os.error:
                print "ERROR: Could not open cluster file"
                sys.exit(1)
    # Send the reply we need to get things started
    #TODO: Error in reply. Why?
        self.socket.send('<SUMA_irgba\n  surface_idcode="%s"\n  ' % (self.surface_idcode) + 'local_domain_parent_ID="%s"\n  ' % (self.surface_idcode) + 'volume_idcode="%s"\n  ' % (self.volume_idcode) + 'function_idcode="%s"\n  threshold="0" />' % (self.volume_idcode))
    #FIXME: Read in the surface file from disk, no time for NIDO right now
        self.load_surface(os.path.join(os.path.split(self.spec_file)[0], 
                                       self.surface_label))

    def run(self):
        self.svr_socket = socket.socket(socket.AF_INET, 
                                    socket.SOCK_STREAM)
        self.svr_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.np = 53211
        bound = False
        while not bound:
            try:
                self.svr_socket.bind(("127.0.0.1", self.np))
                bound = True
            except socket.error as e:
                # If the port is already in use
                if e.errno == 98:
                    self.np = self.np+1
                else: 
                    raise e
        self.launch_suma_connect()
        
        # Start the main loop
        while self.cont:
            # Alternately check the socket and command queue 
            try:
                # Check for mouse clicks in SUMA 
#                dat = self.recv_data()
                dat = self.recv_data()
                if dat:
                    self.last_dat = dat
                    print dat
                    self.handle_mouse_click(dat)

            except socket.error:
                # If the socket times out, it's no problem. Just check the queue.
                pass
            
            try:
                cmd = self.job_q.get_nowait()
                if cmd:
                    print "Got a command: ",
                    print cmd
                    self.handle_cmd(cmd)
                    self.job_q.task_done()
            except Empty:
                pass
        if self.mode == 'server':
            # Delete temporary folder containing dataset
            try:
                os.rmdir(self.dset_path)
            except OSError:
                tkMessageBox.showerror("Error", "Could not delete temporary "+
                                       "folder %s. If it still exists, you can "+
                                       "try to delete it manually.")
            
        self.suma.kill()
        self.svr_socket.close()
                
    def handle_mouse_click(self, dat, force_update=False):
        if force_update == True:
            print "Redrawing"
        try:
            self.surface_nodeid, self.surface_idcode, surface_label = re.findall("""<SUMA_crosshair_xyz\n  ni_type="float"\n  ni_dimen="3"\n  surface_nodeid="([0-9\.]+?)"\n  surface_idcode="(.*?)"\n  surface_label="(.*?)" >""", dat, flags=re.DOTALL)[0]
            # If surface label is different, load the new surface
            if surface_label != self.surface_label:
                self.surface_label = surface_label
                self.load_surface(os.path.join(os.path.split(self.spec_file)[0], 
                                               self.surface_label))
                print "Loaded new surface"
            self.surface_nodeid = int(self.surface_nodeid)
            self.res_q.put_nowait(["node", self.surface_nodeid])
            selected_cluster = self.clust[self.surface_nodeid]
            self.res_q.put_nowait(["cluster", selected_cluster])
            
            # If a new cluster was selected, update the figure
            if (self.selected_cluster != selected_cluster) or force_update:
                if not force_update:
                    #TODO: Remove debug output
                    print "surface nodeid: %s" % (self.surface_nodeid)
                    print "surface idcode: %s" % (self.surface_idcode)
                    print "surface label: %s" % (self.surface_label)
                # Update the selected cluster
                self.selected_cluster = self.clust[self.surface_nodeid] # Load the appropriate matrix
                matrix = self.get_matrix(self.selected_cluster)
                # If there was an error while getting the matrix, return
                if not matrix:
                    return
                self.send_displayable_object(self.surface_nodeid, matrix)
                print "Sent DO"
            else:
                print "Same cluster selected" #                                                     [[i, uniform(0,1)]
                    #                                                         for i in clusters])
        except IndexError:
            # If we didn't find the data we were looking for
            # in the SUMA response, tell the user, but carry on
            print "Got unexpected data:"
            print dat
            raise
                

    def recv_data(self):
        '''
        Recieve data of indeterminate length and return it
        '''
        dat_array = []
        dat = self.socket.recv(1024)
        while dat:
            dat_array.append(dat)
            try:
                dat = self.socket.recv(1024)
            except socket.error:
                dat = ''
        
        return ''.join([str(i) for i in dat_array])
        
        
    def handle_cmd(self, cmd):
        '''
        Handle a command from some other part of the program
        '''
        #TODO: Finish handle command method
        
        if cmd[0] == 'suma':
            try:
                # If suma is running, kill it
                if self.ready():
                    self.suma.kill()
                    
                self.res_q.put_nowait(
                    self.launch_suma_connect())
            except Exception as e:
                self.res_q.put_nowait(e)
        elif self.ready():
            if cmd[0] == 'threshold':
                self.threshold = cmd[1]
            elif cmd[0] == 'shape':
                self.shape = cmd[1]
            elif cmd[0] == 'color':
                self.color = cmd[1]
            elif cmd[0] == 'redraw':
                try:
                    """
                    self.res_q.put_nowait(
                        self.redraw())
                        """
                    print "Got redraw command"
                    self.redraw()
                except Exception as e:
                    print "Exception during redraw: ",
                    print e
                    print_exc()
#                    self.res_q.put_nowait(e)
            elif cmd[0] == 'die':
                self.cont = False
        else:
            print "Got an invalid command: ",
            print cmd
            return 

    """
    def interp_parabola(self, p1, p2, normal, height, n=20):
        '''
        Create a parabola of height "height", interpolated at n points, 
        between 3D points p1 and p2, pointing in the direction of 
        3D vector "normal".
        '''
        rng, offset = (0, 0)
        make_line = lambda x: (x*(rng/float(n)))+offset
        p1p2 = [i[1]-i[0] for i in itertools.izip(p1,p2)]
        line = [[], [], []]
        
        # Calculate the line between p1 and p2
        for i in xrange(3):
            rng = p1p2[i]
            offset = p1[i[i] = [ j for j in itertools.imap(make_line, xrange(n+1)) ]
        
        # Calculate the parabola in 2D
        rng = sqrt( p1p2[0]**2 + p1p2[1]**2 + p1p2[2]**2 )
        offset = 0
        # parabola_2 = [ height*(i)(i-rng) for i in itertools.imap(make_line, xrange(n+1)) ]
        parabola_2 = [ height*(i)*(i-rng) for i in 
                      itertools.imap(make_line, xrange(n+1)) ]
        
        # Calculate the parabola in 3D
        parabola_3 = [[], [], []]
        for i in xrange(3):
            parabola_3[i] = [ j[0] + j[1]*normal[i] 
                             for j in itertools.izip(line[i], parabola_2) ]
            
        return parabola_3
    """
    
    def interp_circle(self, p1, p2, normal, height=None, n=20):
        pass
    """    
    def create_nido_segments_coord(self, src_node, matrix):
        '''
        Takes a source node and a list of nodes it's connected to. 
        Produces a displayable object of circles connecting the source node
        to destination nodes.
        '''
        nido_array = ['#coordinate-based_segments',]
        src_coords = self.get_node_coords(src_node)
        src_normal = self.get_node_normal(src_node)
        for dst_node in matrix:
            dst_coords = self.get_node_coords(dst_node)
            dst_normal = self.get_node_normal(dst_node)
            average_normal = [(i[0]+i[1])/2. for i in itertools.izip(src_normal, dst_normal)]
            segments = self.interp_circle(src_coords, dst_coords, average_normal)
            segments_text = range(1, len(segments))
            for i in xrange(len(segments_text)):
                segments_text[i] = "%i %i %i %i %i %i\n"%(
                                                          segments[i-1][0],
                                                          segments[i-1][1],
                                                          segments[i-1][2],
                                                          segments[i][0],
                                                          segments[i][1],
                                                          segments[i][2])
    """
    
    def load_surface(self, surf_fi_name):
        try:
            surf_fi = open(surf_fi_name, 'r')
            surf = surf_fi.read()
            
            #TODO: Support binary surfaces
            #TODO: Make this a separate library
            if not re.match("#!ascii", surf):
                raise ValueError("Only ASCII surface files (.asc files) are currently supported")
            else:
                # Load an ASCII surface
                surf = surf.split('\n')
                num_nodes = int(surf[1].split(' ')[0])
                # Separate out the x y z locations of nodes and 
                # parse them to floats
                nodes = [i.split() for i in surf[2:num_nodes+2]]
                nodes = [[float(i) for i in node] for node in nodes]
                self.nodes = nodes
                
                triangles = [i.split() for i in surf[num_nodes+2:(2*num_nodes)+2]]
                triangles = [[int(i) for i in triangle] for triangle in triangles]
                self.triangles = triangles
                
                # Get mins and maxes of x,y,z for coloring
                x = [i[0] for i in nodes]
                y = [i[1] for i in nodes]
                z = [i[2] for i in nodes]
                
                self.x_range = max(x)-min(x)
                self.y_range = max(y)-min(y)
                self.z_range = max(z)-min(z) 
            
        except IOError as e:
            #TODO: Rethink error handling
            print "Could not open surface file: %s"%str(e)
            sys.exit(1)
        except ValueError as e:
            print "Error reading surface file: %s"%str(e)
            sys.exit(1)
            
    def norm(self, val):
        '''
        Normalize val from being between self.threshold and 1
        to being from 0 to 1
        '''
        return (val-self.threshold)/(1-self.threshold)
            
    def color_data(self, filtered_matrix):
        '''
        Given a list of nodes and their correlations,
        make a list of nodes and RGBA values given the current coloring mode
        '''
        # Normalize a value self.threshold<=t<=1 to 0<=t<=1
        if self.color == 'heat':
            colored = [(i[0], self.norm(i[1]), 0., 1.-self.norm(i[1]), 1.) for i in filtered_matrix]
        
        if self.color == 'brightness':
            colored = range(len(filtered_matrix))
            for i in xrange(len(filtered_matrix)):
                node = filtered_matrix[i][0]
                corr = filtered_matrix[i][1]
                x, y, z, w = self.nodes[node]
                colored[i] = (node, (x/self.x_range)*corr, 
                              (y/self.y_range)*corr, 
                              (z/self.z_range)*corr, 1.0)
            
            
        
        return colored
                
    
    def send_displayable_object(self, src_node, matrix):
        '''
        Takes a source node and a list of nodes it's connected to. 
        Produces a displayable object node-based lines connecting the 
        source node to destination nodes and loads it into SUMA.
        '''
        # Valid shapes: paths, spheres (only supports heat)
        # Valid colors: brightness, heat, alpha
        shape = self.shape
        color = self.color
#        shape = 'spheres'
#        color = 'heat'
        
        # TODO: Make path generation use filtered_matrix
        filtered_matrix = [i for i in matrix if i[1] > self.threshold] 
        colored = self.color_data(filtered_matrix)
        
        if os.path.exists(self.do_file):
                os.remove(self.do_file)
        
        if shape == 'paths':
            # Generate a list of the nodes we'll draw paths to
            nodelist = open('nodelist.1D', 'w')
            nodes = [i[0] for i in matrix if i[1] >= self.threshold]
            indices = [i for i in xrange(len(matrix)) if matrix[i][1] >= self.threshold]
            for i in nodes:
                nodelist.write("%s\n"%(i))
            nodelist.close()
            
            # Generate the paths
            surfdist = subprocess.Popen(["/home/morganl/workspace/AFNI/Debug/afni_src/SurfDist",
                    "-i", self.surface_label,
                    "-input", "nodelist.1D",
                    "-from_node", str(src_node),
                    "-node_path_do", str(self.do_file)],
                    stderr=subprocess.STDOUT,
                    stdout=subprocess.PIPE)
            ret = surfdist.wait()
        
            if ret != 0:
                # Handle failure
                pass
        
            ret = surfdist.wait()
            
            if ret != 0:
                #TODO: Handle failure
                pass
            
            # Modify the brightness of each path to reflect its level of correlation
            paths_fi = open(self.do_file+".1D.do", 'r')
            paths = paths_fi.read()
            paths = paths.split('\n\n')
            paths = [path.split('\n') for path in paths]
            head = paths[0][0]
            # Remove the text header, since it would break the parsing of the 
            # numbers later on
            paths[0] = paths[0][1:]
            paths = [[line.split(' ') for line in path] for path in paths]
            # Remove the empty line at the end of the file
            del paths[-1]
            print "Indices:"
            print len(indices)
            print "Paths:"
            print len(paths)
            for dest in xrange(len(indices)):
                path = paths[dest]
                if color == 'brightness': 
                    for line_ind in xrange(len(path)):
                        line = path[line_ind]
                        norm_corr = self.norm(matrix[indices[dest]][1])
                        path[line_ind] = [int(line[0]), int(line[1]), 
                             float(line[2])*norm_corr, 
                             float(line[3])*norm_corr, 
                             float(line[4])*norm_corr, 
                             float(line[5])]
                elif color == 'heat':
                    for line_ind in xrange(len(path)):
                        line = path[line_ind]
                        path[line_ind] = [int(line[0]), int(line[1]), 
                             self.norm(matrix[indices[dest]][1]), 
                             0.0, 
                             (1-self.norm(matrix[indices[dest]][1])), 
                             float(line[5])]
                elif color == 'alpha':
                    for line_ind in xrange(len(path)):
                        line = path[line_ind]
                        path[line_ind] = [int(line[0]), int(line[1]), 
                             float(line[2]), 
                             float(line[3]), 
                             float(line[4]), 
                             float(line[5])*matrix[indices[dest]][1]]
                    
            # Put it back into a textual format
            #paths_txt = [' '.join((str(i) for i in line)) for path in paths for line in path]
            paths_txt = [['%i %i %.2f %.2f %.2f %.2f'%tuple(line) for line in path] for path in paths]
            paths_txt = ['\n'.join(path) for path in paths_txt]
            paths_txt.insert(0, head)
            paths_txt = '\n\n'.join(paths_txt)
            paths_fi = open(self.do_file+".1D.do", 'w')
            paths_fi.write(paths_txt)
            
        elif shape == 'spheres':
            # Generate spheres
            do_file = open(self.do_file+'.1D.do', 'w')
            do_file.write("#node-based_spheres\n")
            if color == 'nodemap':
                for i in xrange(0,self.num_nodes,4):
                    do_file.write("%i %.3f 0.0 %.3f 1.0\n"%(i, 
                                                    self.norm(float(i)/float(self.num_nodes)), 
                                                    1.-self.norm(float(i)/float(self.num_nodes))))
            else:
                for i in colored:
                    do_file.write("%i %.3f %.3f %.3f %.3f\n"%(i))
            do_file.close()
            
        elif shape == 'sized spheres':
            # Generate spheres
            do_file = open(self.do_file+'.1D.do', 'w')
            do_file.write("#node-based_spheres\n")
            for j in xrange(len(colored)):
                i = colored[j]
                corr = filtered_matrix[j][1]
                do_file.write("%i %.3f %.3f %.3f %.3f %.3f\n"%(i[0], i[1], i[2], 
                                                               i[3], i[4], 2.*corr))

            do_file.close()
        
        # Load the shapes into SUMA
        DriveSuma = subprocess.Popen(["/home/morganl/workspace/AFNI/Debug/afni_src/DriveSuma",
                    "-np", str(self.np),
                    "-com","viewer_cont",
                    "-load_do", self.do_file+'.1D.do'],
                    stderr=subprocess.STDOUT,
                    stdout=subprocess.PIPE)
        
    def get_node_coords(self, node):
        '''
        Look up a node's xyz coordinates from its node number.
        '''
        return range(3)
    
    def redraw(self):
        self.handle_mouse_click(self.last_dat, 
                                force_update=True)
    
    def handle_input(self, inp):
        inp = inp.strip()
        
        if re.match("[sS]", inp):
            self.shape = self.shapes.next()
            print "Switched shape to %s"%(self.shape)
        elif re.match("[mMcC]", inp):
            self.color = self.colors.next()
            print "Switched mode to %s"%(self.color)
            
        # Update the graphic
        self.redraw()
            
def input_loop(proc_thread):
    print "Taking input now"
    while True:
        proc_thread.handle_input(raw_input())
    
if __name__ == '__main__':
    in_queue = Queue()
    out_queue = Queue()
    
    try:
        spec_file, surfvol_file = sys.argv[1:]
    except ValueError:
        print "Usage: python ProcessingThreadClass.py <spec file> <surfvol file>"
        sys.exit(1)
        
    proc_thread = ProcessingThread(spec_file, surfvol_file, dset='test_dset')
    proc_thread.setDaemon(True)
    proc_thread.start()
    
    input_thread = Thread(target=input_loop(proc_thread))
    input_thread.setDaemon(True)
    input_thread.start()
    
    # Wait for the kill signal to exit
    signal.pause()
    proc_thread.suma.kill()
