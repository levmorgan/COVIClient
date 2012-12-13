import ServerCommunication as sc
import threading
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
        try:
            res = self.dispatch[job[0]](*job[1:])
        except Exception as e:
            res = e
        self.res_q.put(res)
        self.job_q.task_done()

        
