import numpy as np
import matplotlib as mpl
from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d import Axes3D


def plotathing(x,y,z):
    fig = plt.figure()
    ax = fig.gca(projection='3d')
    ax.plot(x,y,z)
    plt.xlabel('x')
    plt.ylabel('y')
    plt.show()

