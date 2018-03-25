# -*- coding: utf-8 -*-
#
from __future__ import print_function, division

import os

import matplotlib.pyplot as plt
import numpy
from scipy.optimize import leastsq, least_squares, minimize
import yaml

import colorio

from pade2d import Pade2d


def f_ellipse(a_b_theta, x):
    a, b, theta = a_b_theta
    cos = numpy.cos(theta)
    sin = numpy.sin(theta)
    return (
        + a**2 * (x[0]*cos + x[1]*sin)**2
        + b**2 * (x[0]*sin - x[1]*cos)**2
        - 1.0
        )


def jac_ellipse(a_b_theta, x):
    a, b, theta = a_b_theta
    cos = numpy.cos(theta)
    sin = numpy.sin(theta)
    return numpy.array([
        + 2*a * (x[0]*cos + x[1]*sin)**2,
        #
        + 2*b * (x[0]*sin - x[1]*cos)**2,
        #
        + a**2 * 2*(x[0]*cos + x[1]*sin) * (-x[0]*sin + x[1]*cos)
        + b**2 * 2*(x[0]*sin - x[1]*cos) * (+x[0]*cos + x[1]*sin),
        ]).T


def _get_luo_rigg():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(dir_path, '../colorio/data/luo-rigg/luo-rigg.yaml')) as f:
        data = yaml.safe_load(f)

    centers = []
    J = []
    for _, data_set in data.items():
        for _, dat in data_set.items():
            x, y, Y, a, ab, theta, _ = dat
            a /= 1.0e4
            a *= (Y/30)**0.2
            b = a / ab

            centers.append([x, y])

            J.append(numpy.array([
                [a * numpy.cos(theta), -b * numpy.sin(theta)],
                [a * numpy.sin(theta), b * numpy.cos(theta)],
                ]))

    return numpy.array(centers), numpy.moveaxis(numpy.array(J), 0, -1)


def _get_macadam():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(dir_path, '../colorio/data/macadam1942/table3.yaml')) as f:
        data = yaml.safe_load(f)

    centers = []
    points = []
    for datak in data:
        # collect ellipse points
        _, _, _, _, delta_y_delta_x, delta_s = numpy.array(datak['data']).T
        if len(delta_s) < 2:
            continue
        center = [datak['x'], datak['y']]
        centers.append(center)
        offset = (
            numpy.array([numpy.ones(delta_y_delta_x.shape[0]), delta_y_delta_x])
            / numpy.sqrt(1 + delta_y_delta_x**2) * delta_s
            )
        points.append(numpy.column_stack([
            (center + offset.T).T,
            (center - offset.T).T,
            ]))

    centers = numpy.array(centers)
    J = get_local_linearizations1(centers, points)
    return centers, numpy.moveaxis(J, 0, -1)
    # return centers, self.get_local_linearizations2(centers, points)


def get_local_linearizations1(centers, points):
    # Get ellipse parameters
    X = [
        (pts.T - center).T
        for center, pts in zip(centers, points)
        ]
    a_b_theta = numpy.array([
        # Solve least squares problem for [1/a, 1/b, theta]
        # and pick [a, b, theta]
        leastsq(
            lambda a_b_theta: f_ellipse(a_b_theta, x),
            [1.0, 1.0, 0.0],
            Dfun=lambda a_b_theta: jac_ellipse(a_b_theta, x),
            )[0]
        for x in X
        ])
    a_b_theta = numpy.array([
        1 / a_b_theta[:, 0],
        1 / a_b_theta[:, 1],
        a_b_theta[:, 2]
        ]).T
    # Construct 2x2 matrices that approximately convert unit circles into
    # the ellipse defined by the points.
    J = []
    for abt in a_b_theta:
        a, b, theta = abt
        J.append(numpy.array([
            [a * numpy.cos(theta), -b * numpy.sin(theta)],
            [a * numpy.sin(theta), b * numpy.cos(theta)],
            ]))

    return numpy.array(J)


def get_local_linearizations2(centers, points):
    X = [
        (pts.T - center).T
        for center, pts in zip(centers, points)
        ]

    def f_linear_function(j, x):
        Jx = numpy.dot(j.reshape(2, 2), x)
        out = numpy.einsum('ij,ij->j', Jx, Jx) - 1.0
        return out

    def jac_linear_function(j, x):
        J = j.reshape(2, 2)
        return numpy.array([
            2*J[0, 0]*x[0]**2 + 2*J[0, 1]*x[0]*x[1],
            2*J[0, 1]*x[1]**2 + 2*J[0, 0]*x[0]*x[1],
            2*J[1, 0]*x[0]**2 + 2*J[1, 1]*x[0]*x[1],
            2*J[1, 1]*x[1]**2 + 2*J[1, 0]*x[0]*x[1],
            ]).T

    J = []
    for x in X:
        j, _ = leastsq(
            lambda J: f_linear_function(J, x),
            [1.0, 0.0, 0.0, 1.0],
            Dfun=lambda J: jac_linear_function(J, x),
            # full_output=True
            )
        J.append(numpy.linalg.inv(j.reshape(2, 2)))

    return numpy.array(J)


class EllipseCircle(object):
    def __init__(self, centers, J):
        self.centers = centers
        self.J = J

        self.target = 0.002
        self.J /= self.target

        self.num_f_eval = 0

        # self.J = numpy.array(self.get_local_linearizations2(centers, points))

        # # plot
        # for center, pts, j in zip(centers, points, self.J):
        #     # plot points
        #     p = (pts.T - center).T
        #     plt.plot(*p, '.')
        #     # plot circle
        #     t = numpy.linspace(0.0, 2.0*numpy.pi, 1000)
        #     xy = numpy.array([numpy.cos(t), numpy.sin(t)])
        #     plt.plot(*numpy.dot(j, xy), '-', label='ellipse')
        #     plt.legend()
        #     # # plot transformation
        #     # xy_new = numpy.dot(j, p)
        #     # plt.plot(*xy_new, 'x')
        #     plt.axis('equal')
        #     plt.show()

        return

    def get_q2_r2(self, f):
        # jacs and J are of shape (2, 2, k). M must be of the same shape and
        # contain the result of the k 2x2 dot products. Perhaps there's a
        # dot() for this.
        M = numpy.einsum('ijl,jkl->ikl', f.jac(), self.J)

        # One could use
        #
        #     M = numpy.moveaxis(M, -1, 0)
        #     _, sigma, _ = numpy.linalg.svd(M)
        #
        # but computing the singular values explicitly via
        # <https://scicomp.stackexchange.com/a/14103/3980> is faster.
        a = (M[0, 0] + M[1, 1]) / 2
        b = (M[0, 0] - M[1, 1]) / 2
        c = (M[1, 0] + M[0, 1]) / 2
        d = (M[1, 0] - M[0, 1]) / 2

        # From the square roots of q2 and r2, the ellipse axes can be computed,
        # namely
        #
        #   s1 = q + r
        #   s2 = q - r
        #
        q2 = a**2 + d**2
        r2 = b**2 + c**2

        return q2, r2, M

    def get_ellipse_axes(self, f):
        q, r = numpy.sqrt(self.get_q2_r2(f)[:2])
        sigma = numpy.array([q+r, q-r]) * self.target
        return sigma

    def cost(self, f):
        q2, r2, M = self.get_q2_r2(f)

        self.M = M

        # for least squares
        out = numpy.array([q2 - 1.0, r2]).flatten()

        if self.num_f_eval % 10000 == 0:
            # cost = numpy.sum([(numpy.sqrt(q2) - 1.0)**2, r2])
            cost = numpy.sum([(q2 - 1.0)**2, r2])
            print('{:7d}     {}'.format(self.num_f_eval, cost))
            # print(numpy.moveaxis(M, -1, 0))

        self.num_f_eval += 1
        return out



def _main():
    # centers, J = _get_macadam()
    centers, J = _get_luo_rigg()

    ec = EllipseCircle(centers, J)

    pade2d = Pade2d(centers.T, [2, 0, 2, 0])

    axes0 = ec.get_ellipse_axes(pade2d).T.flatten()
    print(axes0.shape)
    exit(1)


    def f(alpha):
        pade2d.set_alpha(alpha)
        return ec.cost(pade2d)

    # Create the identity function as initial guess
    print('num parameters: {}'.format(pade2d.total_num_coefficients))
    print('\ninitial parameters:')
    pade2d.print()

    alpha0 = pade2d.alpha.copy()

    print('f evals     cost')
    # out = minimize(
    #         f, pade2d.alpha,
    #         method='Nelder-Mead'
    #         # method='Powell'
    #         # method='CG'
    #         # method='BFGS'
    #         )

    # Create the parameter bounds such that the denominator coefficients are
    # nonnegative. This avoids division-by-zero in the transformation.
    # bounds = numpy.zeros((2, len(alpha0)))
    # bounds[0] = -numpy.inf
    # bounds[1] = +numpy.inf
    # #
    # num_coefficients = [(d+1)*(d+2)//2 for d in pade2d.degrees]
    # num_coefficients[1] -= 1
    # num_coefficients[3] -= 1
    # b0, b1, b2, b3 = \
    #     numpy.split(bounds.T, numpy.cumsum(num_coefficients[:-1]))
    # b1[:, 0] = 0.0
    # b3[:, 0] = 0.0
    # bounds = numpy.concatenate([b0, b1, b2, b3]).T

    # Levenberg-Marquardt (lm) is better suited for small, dense, unconstrained
    # problems, but it needs more conditions than parameters. This is not the
    # case for larger polynomial degrees.
    out = least_squares(
        f,
        pade2d.alpha,
        # bounds=bounds,
        method='trf'
        )

    print('{:7d}     {}'.format(ec.num_f_eval, ec.cost(pade2d)))

    print('\noptimal parameters:')
    pade2d.set_alpha(out.x)
    pade2d.print()

    # plot statistics
    pade2d.set_alpha(alpha0)
    axes0 = ec.get_ellipse_axes(pade2d).T.flatten()
    plt.plot(axes0, label='axes lengths before')
    pade2d.set_alpha(out.x)
    axes1 = ec.get_ellipse_axes(pade2d).T.flatten()
    plt.plot(axes1, label='axes lengths opt')
    plt.legend()
    plt.grid()

    # Plot unperturbed MacAdam
    plt.figure()
    # colorio.plot_macadam(
    #     ellipse_scaling=10,
    colorio.plot_luo_rigg(
        ellipse_scaling=1,
        plot_rgb_triangle=False,
        )

    # Plot perturbed MacAdam
    plt.figure()
    # colorio.plot_macadam(
    #     ellipse_scaling=10,
    colorio.plot_luo_rigg(
        ellipse_scaling=1,
        xy_to_2d=pade2d.eval,
        plot_rgb_triangle=False,
        )

    plt.show()

    # for M in numpy.moveaxis(macadam.M, -1, 0):
    #     print()
    #     print(M)
    #     # plot ellipse
    #     angles = numpy.pi * numpy.linspace(-1, +1, 100)
    #     v = numpy.array([numpy.cos(angles), numpy.sin(angles)])

    #     plt.plot(*numpy.dot(M, v), color='k')
    #     # plot arrows
    #     angles = numpy.pi * numpy.linspace(-0.5, 0.5, 6)
    #     v = numpy.array([numpy.cos(angles), numpy.sin(angles)])
    #     for vv in v.T:
    #         Mv = numpy.dot(M, vv)
    #         plt.plot([0, Mv[0]], [0, Mv[1]])

    #     plt.axis('equal')
    #     plt.show()
    return


if __name__ == '__main__':
    _main()
