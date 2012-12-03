'''
Created on Nov 30, 2012

@author: morganl
'''
import unittest, ssl, socket, random, itertools
import ServerCommunication as sc


class TestServerCommunication(unittest.TestCase):

    '''
    Unit testing for the ServerCommunication module. Assumes there is a dataset called fakedset and 
    users called 'lev' (an administrator) and 'bob'
    
    
    Tests methods:
    handle_response
        xsafe_recv
        xsafe_send
        xsimple_request
        xauth
        xlst
        xnew_dset
        xmatrix_req
        rename
        share
        copy
        copy_shared
        xremove
        close
        rename_admin
        remove_admin

    '''
    
    def setUp(self):
        # Set up a socket        
        client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sec_clisock = ssl.wrap_socket(client_sock)
        sec_clisock.settimeout(10)
        sec_clisock.connect((socket.gethostname(), 14338))  
        self.sock = sec_clisock
        
        # Authenticate
        sc.auth(self.sock, 'lev', 'lev')
        
        # FIXME: Make sure lev, bob, and testdset exist

    def tearDown(self):
        self.sock.close()
    

    def test_new_dset_and_remove(self):
        res = sc.new_dset(self.sock, 
                    '/home/morganl/workspace/COVI Server/src/COVIServer/fakedset1.tar.gz', 
                    'fakedset1')
        self.assertTrue(res, "Reply for new_dset")
        print 'Uploaded dataset OK'
        
        res = sc.remove(self.sock, 'fakedset1')
        self.assertTrue(res, "Reply for remove")
        print 'Removed dataset OK'

    def test_list_and_matrix(self):
        dsets = sc.lst(self.sock)
        dkeys = dsets.keys()
        self.assertTrue("list" in dkeys)
        self.assertTrue("shared" in dkeys)
        self.assertTrue("requests" in dkeys)
        
        for i in itertools.chain(dsets['list'], dsets["shared"]):
            # Request a random matrix for each dset
            # Nothing to assert here, the method checks the data
            sc.matrix_req(self.sock, i, random.randint(1,500))
            
    def test_copy_and_remove(self):
        dsets = sc.lst(self.sock)
        dsets = dsets['list']
        

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
    #TestServerCommunication()
