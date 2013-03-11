from plotting import plotathing
import COVIclient as Cc

def test_interp_parabola(p1 = [0, 0, 0], p2 = [1, 1, 1], normal = [0, -1, 0], height = 5.0, n=20):
    proc = Cc.COVIProcessingThread()
    parab = proc.interp_parabola(p1, p2, normal, height, n)
    for i in xrange(len(parab[0])):
        print "%.3f, %.3f, %.3f"%(parab[0][i], parab[1][i], parab[2][i])
    plotathing(parab[0], parab[1], parab[2])


print "Testing interp_parabola"
test_interp_parabola()
