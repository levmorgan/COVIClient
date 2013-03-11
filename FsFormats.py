from struct import error as struct_error, unpack
import re
import sys

def read_annot(annot_file_name):
    '''
    Based on read_annotation.m
    Takes the name of an aparc file
    Returns [data, color_table]
    data is a list of color table indices where data[x] is the
    table index for vertex x
    color_table is a map:
    table_index-> [ str label, int R, int G, int B ]
    '''

    try:
        aparc = open(annot_file_name, 'rb')
    except:
        raise
        return None
        
    num_records = unpack('>i', aparc.read(4))[0]
    data = unpack('>%ii'%(num_records*2), aparc.read(num_records*8))[1::2]
    try:
        # This record will exist if there is a color table.
        # I guess the value doesn't matter.
        has_colortable = unpack('>i', aparc.read(4))[0]
    except struct_error:
        #If there is no color table
        return [data,{}]
    # If num_entries > 0, file's version is 1. Otherwise, it should be 2.
    num_entries = unpack('>i', aparc.read(4))[0]
    # Read a string trimming off \0
    read_str = lambda x, y=aparc: ''.join(unpack('>%ic'%(x), y.read(x))[:-1])
    color_table = {}


    if num_entries > 0:
        orig_len = unpack('>i', aparc.read(4))[0]
        color_table['orig_tab'] = read_str(orig_len)
        for i in xrange(num_entries):
            name_len = unpack('>i', aparc.read(4))[0]
            name = read_str(name_len)
            entry = list(unpack('>4i', aparc.read(16)))
            entry.insert(0, name)
            index =(entry[1] | entry[2] << 8 | entry[3] << 16 | entry[4] << 32)
            color_table[index] = entry
    else:
        version = -num_entries
        if version != 2:
            raise ValueError('Only APARC versions 1 and 2 are supported.')
            return None

        num_entries = unpack('>i', aparc.read(4))[0]
        orig_len = unpack('>i', aparc.read(4))[0]
        color_table['orig_tab'] = read_str(orig_len)

        #There are two of these lines intentionally
        num_entries = unpack('>i', aparc.read(4))[0]

        for i in xrange(num_entries):
            structure = unpack('>i', aparc.read(4))[0] + 1
            name_len = unpack('>i', aparc.read(4))[0]
            name = read_str(name_len)
            entry = list(unpack('>4i', aparc.read(16)))
            entry.insert(0, name)
            index =(entry[1] | entry[2] << 8 | entry[3] << 16 | entry[4] << 32)
            color_table[index] = structure

    return [data, color_table]

def read_annot_pythonic(annot_file_name):
    '''
    Loads an annot file and returns a map from node numbers to color table rows
    '''
    data, color_table = read_annot(annot_file_name)
    return [color_table[i] for i in data]

def norm(t1):
    '''
    Take a triangle in 3D space and produce a 3D surface normal
    '''
    try:
        v0, v1, v2 = t1
    except:
        print t1
        raise
    v0v1 = [v1[i]-v0[i] for i in xrange(3)]
    v0v2 = [v2[i]-v0[i] for i in xrange(3)]
    norm = range(3)

    norm[1] = v0v1[0]*v0v2[2]-v0v2[0]*v0v1[2]
    norm[2] = v0v1[0]*v0v2[1]-v0v2[0]*v0v1[1]

    return norm


def read_binary_surface(surf_fi_name):
    print "Pretend we're reading a binary surface: %s"%(surf_fi_name)
    pass


def read_surface(surf_fi_name):
    if not re.match(r".*?\.asc$", surf_fi_name):
        raise ValueError("COVI only supports FreeSurfer ASCII "+
                         "surfaces at this time.")
    surf_fi = open(surf_fi_name, 'r')
    surf = surf_fi.read()
    
    # Load an ASCII surface
    surf = surf.split('\n')
    try:
        num_nodes = int(surf[1].split(' ')[0])
    except:
        raise ValueError("%s is not a valid ASCII FreeSurfer surface."%(
                         surf_fi_name))
    # Separate out the x y z locations of nodes and 
    # parse them to floats
    nodes = [i.split() for i in surf[2:num_nodes+2]]
    nodes = [[float(i) for i in node] for node in nodes]
    
    triangles = [i.split() for i in surf[num_nodes+2:(2*num_nodes)+2]]
    triangles = [[int(i) for i in triangle] for triangle in triangles]
    triangles_xyz = [[nodes[i] for i in triangle] for triangle in triangles]
    normals = [norm(triangle[:3]) for triangle in triangles_xyz]
    

    # Get mins and maxes of x,y,z for coloring
    x = [i[0] for i in nodes]
    y = [i[1] for i in nodes]
    z = [i[2] for i in nodes]
    
    x_range = max(x)-min(x)
    y_range = max(y)-min(y)
    z_range = max(z)-min(z) 
    
    return {"nodes":nodes, "triangles":triangles, "normals":normals,
            "x_range":x_range, "y_range":y_range, "z_range":z_range}
        
if __name__ == '__main__':
    read_surface('test_dset/rh.inflated.asc')
