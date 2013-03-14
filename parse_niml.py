#!/usr/bin/python2.7

import re, itertools, sys

class NIMLError(ValueError):
    pass

class NIML_node(object):
    '''
    A node in the NIML DOM. 
    '''
    def __init__(self, name=None, children={}, attribs={}):
        self.name = name
        self.children = children
        self.attribs = attribs

        # 
        for i in children:
            setattr(self, i, children[i])

        for i in attribs:
            setattr(self, i, attribs[i])

    def set_attr(self, name, value):
        self.attribs[name] = value
        setattr(self, name, value)

    def set_child(self, node):
        self.children[node.name] = node
        setattr(self, node.name, node)
        return node

    def del_attr(self, name, value):
        del self.attribs[name]
        setattr(self, name, None)

    def del_child(self, node):
        del self.children[node.name]
        setattr(self, node.name, None)

class NIMLParser(object):
    def __init__(self, niml_string):
        self.dat = niml_string
        self.ofst = 0
        self.end = len(niml_string)
        self.root = NIML_node('root')

        try:
            self.parse()
        except NIMLError as e:
            self.handle_error(e)

    def match(self, regex):
        mat = re.match(regex, self.dat[self.ofst:], flags=re.DOTALL)
        if mat:
            self.ofst += mat.end()
        return mat
    
    def handle_error(self, niml_error):
        print "Error:",
        print str(niml_error) 
        next_newline = re.search("\n", self.dat[self.ofst:]).start()
        print "Got:\n%s"%(self.dat[self.ofst:self.ofst+next_newline])
        print "on line %i"%(len(re.findall("\n", self.dat[:self.ofst]))+2)

    def parse(self):
        while self.ofst < self.end:
            if re.match("\s*$", self.dat[self.ofst:]):
                self.ofst += self.end
                continue

            self.group(self.root)

        return self.root

    def group(self, parent):
        '''
        Parse an opening tag, its attributes, the data,
        and the closing tag.
        '''
        node = NIML_node()
        self.open_tag(node)
        self.attribs(node)
        mat = self.match('\s*>\s*')
        if not mat:
            raise NIMLError("Expected >")
        self.data(node)
        parent.set_child(node)
        
        
    def open_tag(self, node):
        mat = self.match('\s*<\s*(\w+)\s*')
        if mat:
            node.name = mat.groups()[0]
            print "Got an opening tag %s"%(mat.groups()[0])
        else:
            raise NIMLError("Expected an opening tag")

    """
    def open_tag(self, node):
        tag = re.match('\s*<\s*(\w+)\s*', self.dat[self.ofst:])
        print "Got an open tag: "
        print tag.groups()[0]
        self.ofst += tag.end()
        self.attribs(node)

        #TODO: Parse data

        end_tag = re.match(r'\s*</%s\s*>\s*'%node.name, 
            self.dat[self.ofst:])
        
        #TODO: Catch an error
        if not end_tag:
            raise NIMLError("Error: opening %s tag without matching end tag"%(
                node.name))

        node.data = self.dat[self.ofst:end_tag.start()]
        self.offst = end_tag.end()
    """

    def attribs(self, node):
        mat = re.match('\s*(\w+)=\s*', self.dat[self.ofst:])
        while mat:
            attr_name = mat.groups()[0]
            self.ofst += mat.end()
            check_str_mat = re.match(r"([\"'])", self.dat[self.ofst:])
            if check_str_mat:
                str_sep = check_str_mat.groups()[0]
                # Attribute is a string
                str_mat = re.match("%s(.*?)%s"%(str_sep, str_sep), 
                    self.dat[self.ofst:], flags=re.DOTALL)
                if not str_mat:
                    raise NIMLError("expected a string")
                node.set_attr(attr_name, str_mat.groups()[0])
                self.ofst += str_mat.end()

            else:
                val_mat = re.match("\s*\(.*?\)\s+", self.dat[self.ofst:])
                if not val_mat:
                    raise NIMLError("expected an attribute")
                node.set_attr(attr_name, val_mat.groups()[0])
                self.ofst += mat.end()

            mat = re.match('\s*(\w+)=\s*', self.dat[self.ofst:])

        print "Got attribs:"
        [sys.stdout.write(i+'\n') for i in node.attribs]

    def data(self, node):
        '''
        Match data+closing tag
        '''
        mat = self.match('(.*)<\s*%s\s*>')
        if not mat:
            raise NIMLError("Expected data and closing tag")


if __name__ == '__main__':
    dat = open(sys.argv[-1], 'rb').read()
    parser = NIMLParser(dat)
    print parser.root.children
