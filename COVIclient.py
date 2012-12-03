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

        """
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
        """
        
    def interp_circle(self, p1, p2, normal, height=None, n=20):
        return [[i, i+1, i+2] for i in xrange(n)]
        
    def create_nido(self, src_node, matrix):
        '''
        Takes a source node and a list of nodes it's connected to. 
        Produces a displayable object of circles connecting the source node
        to destination nodes.
        '''
        
        src_coords = self.get_node_coords(src_node)
        src_normal = self.get_node_normal(src_node)
        for dst_node in matrix:
            dst_coords = self.get_node_coords(dst_node)
            dst_normal = self.get_node_normal(dst_node)
            average_normal = [(i[0]+i[1])/2. for i in itertools.izip(src_normal, dst_normal)]
            segments = self.interp_circle(src_coords, dst_coords, average_normal)
            segments_text = range(1, len(segments))
            for i in xrange(len(segments_text)):
                segments_text[i] = "%i %i %i %i %i %i\n"%(
                                                          segments[i-1][0],
                                                          segments[i-1][1],
                                                          segments[i-1][2],
                                                          segments[i][0],
                                                          segments[i][1],
                                                          segments[i][2])
        segments_text.insert(0, '#coordinate-based_segments')
            
                
        
        
    def get_node_coords(self, node):
        '''
        Look up a node's xyz coordinates from its node number.
        '''
        return range(3)
