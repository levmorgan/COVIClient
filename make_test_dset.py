from math import ceil
from random import gauss
'''
This is a quick and dirty script to create a valid COVI test dataset.
It creates the dataset in the directory the script is being run from.
'''
# Whether to make stat.1D files, or just the cluster file
make_stat_files = True

nodes_per_clust = 64
num_nodes = 135374

num_clusters = ceil(float(num_nodes)/nodes_per_clust)
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


