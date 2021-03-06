from struct import error as struct_error, unpack
import re, sys, itertools

def _next(iterator):
    try:
        return iterator.next()
    except StopIteration:
        return None

def read_spec(spec_fi_name, suppress=False):
    '''
    Read and parse a SUMA spec file.
    Arguments:
    spec_fi_name: path to a spec file
    suppress: optional, boolean, whether to suppress errors
    Returns:
    spec: A list of the .spec file's root attributes. A list of 2-lists.
    surfaces: A list of maps with the attributes of each surface
    '''
    spec_fi = open(spec_fi_name, 'r')
    spec = []
    surfaces = []
    try:
        line = spec_fi.next()
        line = line.strip()
    except StopIteration:
        return {}

    while line != None:
        line = line.strip()
        # Skip comments
        if re.match('#', line):
            line = _next(spec_fi)
            continue

        # Read in info for a new surface and append it to the surface list
        if re.match("NewSurface", line):
            surf = {}
            line = _next(spec_fi)
            line = line.strip()
            while line:
                try:
                    field, value = line.split(' = ')
                    surf[field] = value
                except ValueError:
                    if not suppress:
                        raise ValueError("Invalid line in %s: %s"%(
                            spec_fi_name, line))
                line = _next(spec_fi)
                line = line.strip()
            
            """
            try:
                spec_fi[surf["FreeSurferSurface"]] = surf
            except KeyError:
                if not suppress:
                    raise ValueError("Surface in %s is missing ")
            """

            surfaces.append(surf)

        # If it's not a blank line, parse an attribute
        else:
            if line:
                spec.append(line.split(' = '))
                
        # Read in the next line
        line = _next(spec_fi)
    return (spec, surfaces)


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
    Arguments:
    annot_file_name: path to an annot file
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

def read_surface(surf_fi_name):
    '''
    Read and parse a FreeSurfer .asc surface file.
    Arguments:
    surf_fi_name: path to a .asc file
    '''
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
        raise ValueError("Error reading %s: "%(surf_fi_name)+
            "file is not a valid ASCII FreeSurfer surface.")
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
        

def read_ROI_Corr_Matrix(corr_matrix_name, roi_filter=None):
    corr_fi = open(corr_matrix_name, 'r')
    corr_raw = corr_fi.readlines()
    corr_fi.close()
    header_start = re.match(r"\s*#", corr_raw[0])
    corr_parsed = {}
    # Try to read the header, which associated each row/column with an ROI
    if header_start:
        print "Matched header ok"
    try:
        rois = [ int(i) for i in corr_raw[0][header_start.end():].split() ]
    except (ValueError, AttributeError):
        raise ValueError("Error reading %s: file is "%(corr_matrix_name)+
                            "missing the required header: #, then "+
                            "a space-separated list of the "+
                            "ROI corresponding to each column")
    
    for i in xrange(len(rois)):
        try:
            # Make a dictionary associating each ROI with its data
            corr_parsed[rois[i]] = [float(j) for j in corr_raw[i+1].split()]
        except ValueError:
            raise ValueError("Error reading %s:\n"%(corr_matrix_name)+
                "Encountered invalid character at line %i"%(i))
    corr_filtered = {}
    # Limit matrix values to the listed ROIs
    if roi_filter:
        filt = [i in roi_filter for i in rois]
        print filt
        if not True in filt:
            raise ValueError("None of the specified ROIs are present in "+
                "the matrix.")
        print roi_filter
        for i in roi_filter:
            it = itertools.izip(filt, corr_parsed[i])
            corr_filtered[i] = [j[1] for j in it if j[0]]

        corr_parsed = corr_filtered
        rois = roi_filter
        
    return [rois, corr_parsed]
    

def read_annot_1D_roi(annot_file_name):
    '''
    annot_file_name: an .annot.1D.roi file generated by SUMA_make_spec_*
    '''
    try:
        annot_fi = open(annot_file_name, 'r')
    except:
        raise
        return None

    header = annot_fi.readline()
    data = []
    
    for line in annot_fi:
        try:
            node, roi, r, g, b = line.split()
            node = int(node)
            roi = int(roi)
            r, g, b = (float(i) for i in (r, g, b))
            data.append([node, roi, r, g, b])
        except (TypeError, NameError, ValueError):
            raise ValueError("Error reading %s:\n"%(annot_file_name)+
                "The format for a .annot.1D.roi file is:\n"+
                "Integer node number, Integer ROI number, Float red, "+
                "Float green, Float blue")
    
    return data


"""
def read_matrix_corr_1D(matrix_file_name):
    '''
    Read the 1D results file from @ROI_Corr_Mat
    matrix_file_name: the 1D results file from @ROI_Corr_Mat
    '''
    try:
        matrix_fi = open(matrix_file_name, 'r')
    except:
        raise
        return None

    try:
        header = matrix_fi.readline()
        rois = [int(i) for i in header.split()[1:]]

        data = {}
        for roi, line in itertools.izip(rois, matrix_fi):
            data[roi] = [float(i) for i in line.split()]

    except (TypeError, NameError, ValueError):
        raise ValueError("Error reading %s:\n"%(annot_file_name)+
            "The format for a .corr.1D matrix file is:\n"+
            "# list of ROI numbers\n for each ROI:\n"
            "\ta line with correlations with each ROI separated by spaces")

    return data
"""

def read_1D_cmap(_1D_cmap_name):
    try:
        _1D_cmapfi = open(_1D_cmap_name, 'r')
    except:
        raise
        return None
    
    # Find the first non-commented line
    last = ''
    curr = _1D_cmapfi.readline()

    try:
        while re.match('\s*#', curr):
            last = curr
            curr = _1D_cmapfi.readline()
    except StopIteration:
        raise ValueError("Error reading %s:\n"%(_1D_cmap_name)+
            "There are no uncommented lines in the file.")
    header = []
    data = []

    for line in itertools.chain([last, curr], _1D_cmapfi):
        if re.match('\s*#', line):
            header = re.sub(r"[#\)\(]", "", line)
            try:
                name, ilabel, r, g, b, surf_annotation = header.split()
                header = [name, int(ilabel), int(r), int(g), int(b), 
                    int(surf_annotation)]
            except ValueError as e:
                print e
                raise ValueError("Error reading %s:\n"%(_1D_cmap_name)+
                    "%s is not a valid comment line"%line)
        else:
            try:
                roi, r, g, b, flag = line.split()
                roi, flag = int(roi), int(flag)
            except ValueError:
                raise ValueError("Error reading %s:\n"%(_1D_cmap_name)+
                    "%s is not a valid data line"%line)
            data.append(header)
            data[-1].extend([roi, flag])

    return data


if __name__ == '__main__':
    #read_surface('test_dset/rh.inflated.asc')
    #rois, corr = read_ROI_Corr_Matrix('sub06204_matrix_all_ROIs.corr.1D', roi_filter=[2,5])
    #matrix = read_matrix_corr_1D('sub06204_matrix_all_ROIs.corr.1D')
    #annot = read_annot_1D_roi('rh.aparc.a2009s.annot.1D.roi')
    data = read_1D_cmap('rh.aparc.a2009s.annot.1D.cmap')
    data = read_1D_cmap('lh.aparc.a2009s.annot.1D.cmap')
