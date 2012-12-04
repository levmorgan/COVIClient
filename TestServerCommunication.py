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
        xhandle_response
        xsafe_recv
        xsafe_send
        xsimple_request
        xauth
        xlst
        xnew_dset
        xmatrix_req
        xrename
        xshare
        xunshare
        xcopy
        copy_shared
        xremove
        remove_shared
        xclose
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
        sc.close(self.sock)
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
        self.assertTrue("list" in dkeys,
                        "list in lst response")
        self.assertTrue("shared" in dkeys,
                        "shared in lst response")
        self.assertTrue("requests" in dkeys,
                        "requests in lst response")
        self.assertTrue("user's shares" in dkeys, 
                        "user's shares in lst response")
        
        for i in itertools.chain(dsets['list']):
            # Request a random matrix for each dset
            # Nothing to assert here, the method checks the data
            sc.matrix_req(self.sock, i, random.randint(1,500))
            
    def test_copy_and_remove(self):
        dsets = sc.lst(self.sock)
        dsets = dsets['list']
        self.assertGreater(len(dsets), 0)
        test_elt = dsets[0]
        test_elt_copy = dsets[0]+"copied"
        sc.copy(self.sock, test_elt, test_elt_copy)
        dsets = sc.lst(self.sock)['list']
        self.assertTrue(test_elt_copy in dsets, "Copied element exists")
        sc.remove(self.sock, test_elt_copy)
        dsets = sc.lst(self.sock)['list']
        self.assertTrue(not (test_elt_copy in dsets), "Copied element deleted")
            
    def test_rename(self):
        # Get a list of datasets
        dsets = sc.lst(self.sock)['list']
        
        # Choose an elt and rename
        test_elt = dsets[0]
        test_elt_renamed = dsets[0]+'renamed'
        sc.rename(self.sock, test_elt, test_elt_renamed)
        
        # Get a new list of datasets
        dsets = sc.lst(self.sock)
        dsets = dsets['list']
        
        # Make sure original is not present and new one is
        self.assertTrue(
                        (test_elt_renamed in dsets)
                        and
                        (not (test_elt in dsets)), 
                        "Copied element deleted")
        
        sc.rename(self.sock, test_elt_renamed, test_elt)
        
        # Get a new list of datasets
        dsets = sc.lst(self.sock)
        dsets = dsets['list']
        
        # Make sure the second rename also worked
        self.assertTrue(
                        (not (test_elt_renamed in dsets))
                        and
                        (not (test_elt in dsets), 
                        "Copied element deleted"))
    
    def test_share_and_unshare(self):
        # Get a list of datasets
        dsets = sc.lst(self.sock)['list']
        test_elt = dsets[0]
        
        # Share the dataset with a user
        sc.share(self.sock, test_elt, 'bob', 0)
        dsets = sc.lst(self.sock)
        dsets = dsets["user's shares"]
        
        self.assertTrue((["lev", "bob", test_elt, 0, 1] in dsets), 
                        "Dataset shared successfully")
        
        # Unshare the shared dataset
        sc.unshare(self.sock, test_elt, 'bob')
        dsets = sc.lst(self.sock)["user's shares"]
        self.assertTrue(not (["lev", "bob", test_elt, 0, 1] in dsets), 
                        "Dataset unshared successfully")
        
        
        
if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
    #TestServerCommunication()
