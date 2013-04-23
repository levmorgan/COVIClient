import ServerCommunication as sc
import threading, socket, ssl
from Queue import Queue, Empty
from traceback import print_exc
import tkMessageBox

class NetworkThread(threading.Thread):
    '''
    Thread to communicate with COVI server. Takes jobs from job_q,
    executes them with ServerCommunication, and returns the results in res_q.
    '''
    def __init__(self):
        super(NetworkThread, self).__init__()
        self.cont = True
        self.job_q = Queue()
        self.res_q = Queue()

        # Map job commands to ServerCommunication methods
        self.dispatch = {
            "auth":sc.auth,
            "list":sc.lst,
            "new_dset":sc.new_dset,
            "matrix":sc.matrix_req,
            "matrix_req":sc.matrix_req,
            "surface":sc.surface,
            "shared_surface":sc.shared_surface,
            "cluster":sc.cluster,
            "shared_cluster":sc.shared_cluster,
            "rename":sc.rename,
            "share":sc.share,
            "unshare":sc.unshare,
            "share_response":sc.share_response,
            "copy":sc.copy,
            "copy_shared":sc.copy_shared,
            "remove":sc.remove,
            "remove_shared":sc.remove_shared,
            "close":sc.close,
            "rename_admin":sc.rename_admin,
            "remove_admin":sc.remove_admin,}
        self.authenticated = False
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Bind to the port even if it's already in use
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.settimeout(10)
        self.sock = ssl.wrap_socket(self.sock)
        self.setDaemon(True)
        
    def set_auth(self, authed=True):
        '''
        Set whether the client has authenticated with the server.
        If so, allow commands other than connect, auth, and die to 
        be executed.
        
        Args:
        authed: Whether or not client is autheniticated 
        '''
        self.authenticated = authed

    def run(self):
        '''
        Execute jobs from the job queue, putting results (including exceptions)
        in the results queue. 
        '''
        while self.cont:
            # Take a job off the job queue, 
            # blocking if it's empty
            job = self.job_q.get()
            if job[0] == 'connect':
                try:
                    self.sock.connect((job[1], job[2]))
                    print "Connected OK"
                    self.res_q.put(True)
                except Exception as e:
                    print "Could not connect"
                    print_exc()
                    self.res_q.put(e)
                    continue
            elif job[0] == 'die':
                self.cont = False
                self.sock.close()
            elif not self.authenticated and job[0] != "auth":
                raise sc.RequestFailureException("dispatching", 
                     "you must be authenticated to run a(n) "+
                     "%s request"%(job[0]))
            else:
                try:
                    res = self.dispatch[job[0]](self.sock, *job[1:])
                except Exception as e:
#                    print "Could not execute job"
                    print_exc()
                    res = e
                if not res:
                    print job
                self.res_q.put(res)
                self.job_q.task_done()

    def recv_response(self, expected="req ok"):
        '''
        Get the response from the server, handling missing or incorrect responses.
        
        Args:
        expected: The expected response type. An exception will be raised if
                  there is no response of this type waiting to be processed.
                  This method discards responses waiting to be processed 
                  until it finds one of type expected. 
                  If expected is None, any response type will be accepted.
        Returns:
        True if the response was of type "req ok", the response otherwise
        '''
        try:
            res = self.res_q.get(True, 5)
        except Empty:
            res = False
            wait = True
            while wait and not res:
                try:
                    res = self.res_q.get(True, 5)
                    wait = False
                except Empty:
                    wait = tkMessageBox.askyesno("Network Issue", 
                        "The response from the server is  taking longer than "+
                        "expected. Continue waiting?")
            if wait == False:
                return False

        # Go through responses from the server until we find the 
        # one that we want
        while True:
            # Validate the response
            if isinstance(res, Exception):
                tkMessageBox.showerror("Network Error", 
                    "Error while communicating with the server: "+
                    "%s"%(str(res)))
                print_exc()
                return False
            elif expected == 'binary' or expected == None:
                return res
            elif expected == 'req ok' and res == True:
                break
            elif type(res) == dict and res['type'] == expected:
                break
            else:
                tkMessageBox.showinfo("Unexpected data from the server", 
                    "COVI got an unexpected response from the server."+
                    " It's probably nothing to worry about.")
                # TODO: Remove debug output
                print "Unexpected response:"
                print res
                # If the data isn't valid and there isn't any more, return False
                if self.res_q.empty():
                    return False
                
                res = self.res_q.get_nowait()
        
        return res
