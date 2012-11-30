import socket, ssl, json, array, os, hashlib, random

class RequestFailureException(Exception):
    '''
    An exception for when the request to the server fails.
    '''
    
    # This is where we store whether we're debugging this module. 
    # It's a terrible hack, but there you go.
    debug = True
    def __init__(self, method, message):
        '''
        Constructor
        '''
        # Exception.__init__(self)
        super(RequestFailureException, self).__init__(method, message)
        self.message = "Error during %s request: %s"%(method, message)
        

def handle_response(reply, method, non_json_data=False):
    '''
    Handle responses from COVI server, raising exceptions if the request that 
    generated the response failed or if the response is invalid
    
    inputs:
    reply:    the unprocessed reply from the server
    method:   the method that sent the request
    non_json_data:    True if the data is not JSON-formatted, e.g. binary
    
    outputs:
    res: 1 if the request succeeded (req_ok), unprocessed data 
         if non_json_data is True, otherwise a processed JSON request
    '''
    try:
        reply = json.loads(reply)["covi-response"]
        if reply["type"] == "req fail":
            raise RequestFailureException(method, reply[""])
        elif reply["type"] == "req ok":
            return 1
        else:
            return reply
    except ValueError:
        if non_json_data:
            return reply
        else:
            raise RequestFailureException(method,
                    "Got a reply from the server that was not valid JSON.")
    except KeyError as e:
        if RequestFailureException.debug:
            print "KeyError: Reply from server is missing key %s"%(str(e.message))
        raise RequestFailureException(method,
                    "Got a reply from the server that was missing fields.")

def simple_request(sock, req, method):
    '''
    Convert the request to JSON, send it, and run handle_response on the reply
    '''    
    sock.send(json.dumps(req))
    try:
        reply = sock.recv()
        return handle_response(reply, method)
    except ssl.socket_error:
        raise RequestFailureException(method,
                    "Connection to server was lost. Try reconnecting.")

def auth(sock, username, password):
    method = "Authentication"
    req = { "covi-request": { 
                             "type":"auth", 
                             "username":username, 
                             "password":password } }
    simple_request(sock, req, method)

def lst(sock):
    method = "List"
    req = { "covi-request": { "type":"list" } }
    return simple_request(sock, req, method)
    
    """
    try:
        lst = res['list']
    except Exception as e:
        print "%s: %s"(type(e).__name__, str(e))
        return

    for i in lst:
        print i
    """

def new_dset(sock, dset_archive, dset_name):
    method = "New dataset"
    randf = open(dset_archive, 'rb')
    rsize = os.stat(randf.name).st_size
    arr = array.array('B')
    arr.fromfile(randf, rsize)
    arr = bytearray(arr)
    md5 = hashlib.md5(arr).hexdigest()
    randf.close()

    req = { "covi-request": { "type":"new", 
                             "dset":dset_archive, 
                             "len":rsize, 
                             "md5":md5 } }
    reply = simple_request(sock, req, method)
    print "Got reply"
    if not handle_response(reply):
        print "Request failed!"
        print reply
        return
    """
    for i in arr:
        sock.send(i)
    """
    sock.send(arr)
    print "Reply:"
    print sock.recv(2048)

def matrix_req(sock, dset, number):
    method = "Matrix request"
    req = { "covi-request": { 
                             "type":"matrix",
                             "dset":dset, 
                             "number":number } }
    res = simple_request(sock, req, method)
    
    # FIXME: MAKE ALL OF THIS WORK. I'm too tired right now and would screw it up.
    if not res:
        return
    else:
        print res
        length = res["len"]
        md5_hash = res["md5"]
        print "Sending recv ok"
        sock.send(json.dumps({ "covi-request": { "type":"resp ok" } }))
        reply = ''
        print "Starting to recv matrix"
        while len(reply) < length:
            # I know this is slow! This is just for debugging!
            res = sock.recv()
            res = handle_response(res, no_json=True)
            if not res:
                return
            reply += res
        recv_hash = hashlib.md5(res).hexdigest()
        print "Hash of received data:"
        print recv_hash
        print "Hash from server:"
        print md5_hash
        print "Equal? "
        print recv_hash == md5_hash
        
def rename(sock):
    method = "Rename"
    req = { "covi-request": { 
                             "type":"rename", 
                             "old":"fakedset1", 
                             "new":"fakedset2" } }
    simple_request(sock, req, method)

def share(sock):
    method = "Share"
    req = { "covi-request": { 
                             "type":"share", 
                             "dset":"fakedset2", 
                             "recipient":"bob", 
                             "write":0, 
                             "share":0 } }
    simple_request(sock, req, method)

def copy(sock):
    method = "Copy"
    req = { "covi-request": {
                             "type":"copy", 
                             "source":"fakedset2", 
                             "destination":"fakedset3", } }
    simple_request(sock, req, method)

def copy_shared(sock):
    method = "Copy shared"
    req = { "covi-request": { 
                             "type":"copy shared", 
                             "source":"fakedset2", 
                             "destination":"fakedset4", 
                             "owner":"bob" } }
    simple_request(sock, req, method)


def remove(sock, dset):
    method = "Remove"
    req = { "covi-request": { 
                             "type":"remove", 
                             "dset":dset } }
    simple_request(sock, req, method)

def close(sock):
    sock.send(json.dumps({ "covi-request": { "type":"close" } }))
   
    
def rename_admin(sock, old, new, owner):
    method = "Administrative Rename"
    req = { "covi-request": { 
                             "type":"rename admin", 
                             "owner":owner, 
                             "old":old, 
                             "new":new } }
    simple_request(sock, req, method)
    

def remove_admin(sock, dset, owner):
    method = "Administrative Remove"
    req = { "covi-request": { 
                             "type":"remove admin", 
                             "owner":owner, 
                             "dset":dset } }
    simple_request(sock, req, method)