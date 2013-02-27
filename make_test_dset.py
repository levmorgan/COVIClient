from sys import argv
from math import ceil
from random import gauss
'''
This is a quick and dirty script to create a valid COVI test dataset.
It creates the dataset in the directory the script is being run from.
'''

args = argv[1:]
try:
    num_nodes = int(args[0])
    if len(args) > 1:
        nodes_per_clust = int(args[1])
    else:
        nodes_per_clust = 64 
except:
    print "Usage: python create_test_dset.py <number of nodes> [nodes per cluster]"


# Whether to make stat.1D files, or just the cluster file
make_stat_files = True

num_clusters = int(ceil(float(num_nodes)/nodes_per_clust))
clust_fi = open('clusters.1D', 'w')
clust_fi.write('%i\n'%0)
for i in xrange(1,num_nodes):
    if i%nodes_per_clust == 0:
        clust_fi.write('\n')
    clust_fi.write('%i\n'%i)
    
if make_stat_files:
    for h in xrange(num_clusters):
        stat_fi = open('%i.stat.1D'%h, 'w')
        for i in xrange(num_clusters):
            clust_fi.write('\n')
            # Get a random probability
            stat_fi.write('%.3f\n'%max(0, min(1, gauss(0.5, 0.3))))
        stat_fi.close()


