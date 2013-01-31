import ServerCommunication as sc
import threading, socket, ssl
from Queue import Queue
from traceback import print_exc

class NetworkThread(threading.Thread):
    def __init__(self):
        super(NetworkThread, self).__init__()
        self.cont = True
        self.job_q = Queue()
        self.res_q = Queue()

        self.dispatch = {
            "auth":sc.auth,
            "list":sc.lst,
            "new_dset":sc.new_dset,
            "matrix_req":sc.matrix_req,
            "surface":sc.surface,
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
        self.authenticated = authed

    def run(self):
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
            else:
                try:
                    res = self.dispatch[job[0]](self.sock, *job[1:])
                except Exception as e:
#                    print "Could not execute job"
#                    print_exc()
                    res = e
                self.res_q.put(res)
                self.job_q.task_done()

        
