'''
Created on Nov 30, 2012

@author: morganl
'''
import unittest, ssl, socket


class TestServerCommunication(unittest.TestCase):


    def __init__(self):
        client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sec_clisock = ssl.wrap_socket(client_sock)
        sec_clisock.settimeout(10)
        sec_clisock.connect((socket.gethostname(), 14338))  
        self.socket = sec_clisock


    def __del__(self):
        self.socket.close()


    def testName(self):
        pass


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()