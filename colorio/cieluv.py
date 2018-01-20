# -*- coding: utf-8 -*-
#
from __future__ import division

import numpy

from .illuminants import white_point, d65
from . import srgb_linear
from . import srgb1


def from_xyz(xyz, whitepoint=white_point(d65())):
    def f(t):
        delta = 6.0/29.0
        out = numpy.array(t, dtype=float)
        is_greater = out > delta**3
        out[is_greater] = 116*numpy.cbrt(out[is_greater]) - 16
        out[~is_greater] = out[~is_greater] / (delta/2)**3
        return out

    L = f(xyz[1]/whitepoint[1])

    x, y, z = xyz
    u = 4*x / (x + 15*y + 3*z)
    v = 9*y / (x + 15*y + 3*z)
    wx, wy, wz = whitepoint
    un = 4*wx / (wx + 15*wy + 3*wz)
    vn = 9*wy / (wx + 15*wy + 3*wz)
    return numpy.array([L, 13*L*(u - un), 13*L*(v - vn)])


def to_xyz(cieluv, whitepoint=white_point(d65())):
    def f1(t):
        out = numpy.array(t, dtype=float)
        is_greater = out > 8
        out[is_greater] = ((out[is_greater]+16)/116)**3
        out[~is_greater] = out[~is_greater] * (3.0/29.0)**3
        return out

    L, u, v = cieluv

    wx, wy, wz = whitepoint
    un = 4*wx / (wx + 15*wy + 3*wz)
    vn = 9*wy / (wx + 15*wy + 3*wz)

    uu = u/(13*L) + un
    vv = v/(13*L) + vn

    Y = wy * f1(L)
    X = Y * 9*uu/(4*vv)
    Z = Y * (12 - 3*uu - 20*vv) / (4*vv)
    return numpy.array([X, Y, Z])


def srgb_gamut(filename='srgb-cieluv.vtu', n=50):
    import meshio
    import meshzoo
    points, cells = meshzoo.cube(nx=n, ny=n, nz=n)

    # cut off [0, 0, 0] to avoid division by 0 in the xyz conversion
    points = points[1:]
    cells = cells[~numpy.any(cells == 0, axis=1)]
    cells -= 1

    pts = from_xyz(srgb_linear.to_xyz(points.T)).T
    rgb = srgb1.from_srgb_linear(points)
    meshio.write(
        filename,
        pts, {'tetra': cells},
        point_data={'srgb': rgb}
        )
    return