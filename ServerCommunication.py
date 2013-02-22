import ssl, json, array, os, hashlib, tarfile

'''
A module for communicating between COVI Client and COVI server.
Should throw only RequestFailureException as long as only expected
bad things happen.
'''


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
            raise RequestFailureException(method, reply["message"])
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
            print "KeyError: Reply from server is missing key '%s'"%(str(e))
        raise RequestFailureException(method,
                    "Got a reply from the server that was missing fields")

def safe_recv(sock, method):
    '''
    Try to recieve network data, catching timeouts
    '''
    try:
        reply = sock.recv()
        return reply
    except ssl.socket_error as e:
        raise RequestFailureException(method,
                    str(e))

def safe_send(sock, data, method):
    try:
        sock.send(data)
        
    except ssl.socket_error as e:
        raise RequestFailureException(method,
                    str(e))

def simple_request(sock, req, method):
    '''
    Convert the request to JSON, send it, and run handle_response on the reply
    '''
    try:
        sock.send(json.dumps(req))
        #reply = safe_recv(sock, method)
        # Let's not use safe_recv and return the actual exception on timeout
        reply = sock.recv()
        return handle_response(reply, method)
    except ssl.socket_error:
        #raise RequestFailureException(method,
        #            str(e))
        raise 
        
def auth(sock, username, password):
    method = "Authentication"
    req = { "covi-request": { 
                             "type":"auth", 
                             "username":username, 
                             "password":password } }
    return simple_request(sock, req, method)

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
                             "dset":dset_name, 
                             "len":rsize, 
                             "md5":md5 } }
    #FIXME: Should I try to deal with a non-req_ok response here?
    simple_request(sock, req, method)
    sock.send(arr)
    #return handle_response(safe_recv(sock, method), method)
    return handle_response(sock.recv(), method)

def recv_binary(sock, method, res):
    length = res["len"]
    md5_hash = res["md5"]
    reply = ''
    while len(reply) < length:
        # I know this is slow! This is just for debugging!
        #res = safe_recv(sock, method)
        res = sock.recv()
        res = handle_response(res, method, non_json_data=True)
        reply += res
    
    recv_hash = hashlib.md5(reply).hexdigest()
    if recv_hash != md5_hash:
        raise RequestFailureException(method, 
            "%s data from the server was invalid,"%(method) +
            " try your request again.")
    return reply

def matrix_req(sock, dset, number):
    method = "Matrix request"
    req = { "covi-request": { 
                             "type":"matrix",
                             "dset":dset, 
                             "number":number } }
    res = simple_request(sock, req, method)
    
    if not res:
        return
    else:
        sock.send(json.dumps({"covi-request":{"type":"resp ok"}}))
        return recv_binary(sock, method, res)

def cluster(sock, dset):
    method = "cluster"
    req = { "covi-request": { 
                             "type":"cluster",
                             "dset":dset } }
    res = simple_request(sock, req, method)
    
    if not res:
        return
    else:
        sock.send(json.dumps({"covi-request":{"type":"resp ok"}}))
        return recv_binary(sock, method, res)
    
def shared_cluster(sock, dset, owner):
    method = "Shared cluster"
    req = { "covi-request": { 
                             "type":"shared cluster",
                             "dset":dset,
                             "owner":owner } }
    res = simple_request(sock, req, method)
    
    if not res:
        return
    else:
        sock.send(json.dumps({"covi-request":{"type":"resp ok"}}))
        return recv_binary(sock, method, res)
        
    
def surface(sock, dset, destination_dir):
    '''
    Request an archive with surface, surfvol, and spec files from 
    the server and extract it into destination_dir
    '''
    method = "Surface"
    req = { "covi-request": { 
                             "type":"surface",
                             "dset":dset } }
    try:
        res = simple_request(sock, req, method)
    except:
        raise
    
    if not res:
        return
    else:
        sock.send(json.dumps({"covi-request":{"type":"resp ok"}}))
        reply = recv_binary(sock, method, res)
    
    # Write the data to disk and extract it
    try:
#        file_dir = os.path.dirname(inspect.stack[-1][1])
#        arch_fi_name = os.path.join(file_dir, dset+'-surfaces.tar.gz')
        arch_fi_name = os.path.join(destination_dir, dset+'-surfaces.tar.gz')
        arch_fi = open(arch_fi_name, 'wb')
        arch_fi.write(reply)
        arch_fi.close()
        
        arch_fi = open(arch_fi_name, 'rb')
        surface_dir = os.path.join(destination_dir, dset+'-surfaces')
        os.mkdir(surface_dir)
        tar = tarfile.TarFile.gzopen(name=None, mode='r', fileobj=arch_fi)
        tar.extractall(surface_dir)
        arch_fi.close()
        os.remove(arch_fi_name)
    except:
        raise
    
    return surface_dir

def shared_surface(sock, dset, owner, destination_dir):
    '''
    Request an archive with surface, surfvol, and spec files from 
    the server and extract it into destination_dir
    '''
    method = "Shared surface"
    req = { "covi-request": { 
                             "type":"shared surface",
                             "dset":dset,
                             "owner":owner } }
    try:
        res = simple_request(sock, req, method)
    except:
        raise
    
    if not res:
        return
    else:
        sock.send(json.dumps({"covi-request":{"type":"resp ok"}}))
        reply = recv_binary(sock, method, res)
    
    # Write the data to disk and extract it
    try:
#        file_dir = os.path.dirname(inspect.stack[-1][1])
#        arch_fi_name = os.path.join(file_dir, dset+'-surfaces.tar.gz')
        arch_fi_name = os.path.join(destination_dir, dset+'-surfaces.tar.gz')
        arch_fi = open(arch_fi_name, 'wb')
        arch_fi.write(reply)
        arch_fi.close()
        
        arch_fi = open(arch_fi_name, 'rb')
        surface_dir = os.path.join(destination_dir, dset+'-surfaces')
        os.mkdir(surface_dir)
        tar = tarfile.TarFile.gzopen(name=None, mode='r', fileobj=arch_fi)
        tar.extractall(surface_dir)
        arch_fi.close()
        os.remove(arch_fi_name)
    except:
        raise
    
    return surface_dir

def rename(sock, old, new):
    method = "Rename"
    req = { "covi-request": { 
                             "type":"rename", 
                             "old":old, 
                             "new":new } }
    return simple_request(sock, req, method)

def share(sock, dset, recipient, response):
    method = "Share"
    if (response != 0) and (response != 1):
        raise ValueError("response must be 0 or 1, not %s"%(str(response))) 
    req = { "covi-request": { 
                             "type":"share", 
                             "dset":dset, 
                             "recipient":recipient, 
                             "can share":response } }
    return simple_request(sock, req, method)

def share_response(sock, dset, owner, response):
    '''
    Accept or reject a share request from another user
    '''
    method = "Share response"
    if (response != 0) and (response != 1):
        raise ValueError("response must be 0 or 1, not %s"%(str(response))) 
    req = { "covi-request": { 
                             "type":"share response", 
                             "dset":dset, 
                             "owner":owner, 
                             "response":response } }
    return simple_request(sock, req, method)
    

def unshare(sock, dset, recipient):
    method = "Unshare"
    req = { "covi-request": { 
                             "type":"unshare", 
                             "recipient":recipient, 
                             "dset":dset } }
    return simple_request(sock, req, method)

def copy(sock, source, destination):
    method = "Copy"
    req = { "covi-request": {
                             "type":"copy", 
                             "source":source, 
                             "destination":destination, } }
    return simple_request(sock, req, method)

def copy_shared(sock, source, destination, owner):
    '''
    Copy a shared dataset to the user's directory
    '''
    method = "Copy shared"
    req = { "covi-request": { 
                             "type":"copy shared", 
                             "source":source, 
                             "destination":destination, 
                             "owner":owner } }
    return simple_request(sock, req, method)


def remove(sock, dset):
    method = "Remove"
    req = { "covi-request": { 
                             "type":"remove", 
                             "dset":dset } }
    return simple_request(sock, req, method)

def remove_shared(sock, dset, owner):
    '''
    Remove a dataset shared to the user
    '''
    method = "Remove shared"
    req = { "covi-request": { 
                             "type":"remove shared", 
                             "owner":owner, 
                             "dset":dset } }
    return simple_request(sock, req, method)

def close(sock):
    sock.send(json.dumps({ "covi-request": { "type":"close" } }))
   
    
def rename_admin(sock, old, new, owner):
    '''
    Rename an arbitrary user's dataset as an administrator
    '''
    method = "Administrative Rename"
    req = { "covi-request": { 
                             "type":"rename admin", 
                             "owner":owner, 
                             "old":old, 
                             "new":new } }
    return simple_request(sock, req, method)
    

def remove_admin(sock, dset, owner):
    '''
    Remove an arbitrary user's dataset as an administrator
    '''
    method = "Administrative Remove"
    req = { "covi-request": { 
                             "type":"remove admin", 
                             "owner":owner, 
                             "dset":dset } }
    return simple_request(sock, req, method)

if __name__ == '__main__':
    import socket
    client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sec_clisock = ssl.wrap_socket(client_sock)
    sec_clisock.settimeout(10)
    sec_clisock.connect((socket.gethostname(), 14338))
    sock = sec_clisock


