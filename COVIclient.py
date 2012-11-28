'''
Created on Nov 12, 2012

@author: morganl
'''
import threading, itertools
from math import sqrt
class COVIclient(threading.Thread):
    '''
    The container class for the COVI Client. It contains instances of 
    COVIGuiThread, COVIProcessingThread, and COVINetworkThread
    '''

    '''
    Flow of execution for a clicked node:
        network_thread receives NIML 
    '''

    def __init__(self):
        '''
        Constructor
        '''
        threading.Thread.__init__(self)

class COVIProcessingThread(threading.Thread):
        
    def __init__(self):
        '''
        Constructor
        '''
        threading.Thread.__init__(self)
        
    
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
            offset = p1[i]
            line[i] = [ j for j in itertools.imap(make_line, xrange(n+1)) ]
        
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
        
    def create_nido(self):
        