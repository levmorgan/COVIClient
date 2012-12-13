import ServerCommunication as sc
import threading, socket, ssl
from Queue import Queue

class NetworkThread(threading.Thread):
    def __init__(self):
        super(NetworkThread, self).__init__()
        self.job_q = Queue()
        self.res_q = Queue()

        self.dispatch = {
            "auth":sc.auth,
            "lst":sc.lst,
            "new_dset":sc.new_dset,
            "matrix_req":sc.matrix_req,
            "surface":sc.surface,
            "rename":sc.rename,
            "share":sc.share,
            "unshare":sc.unshare,
            "copy":sc.copy,
            "copy_shared":sc.copy_shared,
            "remove":sc.remove,
            "remove_shared":sc.remove_shared,
            "close":sc.close,
            "rename_admin":sc.rename_admin,
            "remove_admin":sc.remove_admin,}
 

    def run(self):
        # Take a job off the job queue, 
        # blocking if it's empty
        job = self.job_q.get()
        if job[0] == 'connect':
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock = ssl.wrap_socket(sock)
                self.sock.set_timeout(10)
                self.sock.connect((job[1], job[2]))
                self.res_q.put(True)
            except Exception as e:
                self.res_q.put(e)
            finally:
                return

        try:
            res = self.dispatch[job[0]](self.sock, *job[1:])
        except Exception as e:
            res = e
        self.res_q.put(res)
        self.job_q.task_done()

        
