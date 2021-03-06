import numpy

from ._color_space import ColorSpace
from ._linalg import dot, solve


class IPT(ColorSpace):
    """
    IPT color model.
    """

    def __init__(self):
        super().__init__()
        self.M1 = numpy.array(
            [
                [0.4002, 0.7075, -0.0807],
                [-0.2280, 1.1500, 0.0612],
                [0.0000, 0.0000, 0.9184],
            ]
        )
        self.M2 = numpy.array(
            [
                [0.4000, 0.4000, 0.2000],
                [4.4550, -4.8510, 0.3960],
                [0.8056, 0.3572, -1.1628],
            ]
        )
        self.labels = ["I", "P", "T"]
        self.k0 = 0  # the index that corresponds to luminosity

    def from_xyz100(self, xyz):
        lms = dot(self.M1, xyz)
        lms_ = numpy.sign(lms) * numpy.abs(lms) ** 0.43
        ipt = dot(self.M2, lms_)
        return ipt

    def to_xyz100(self, ipt):
        lms_ = solve(self.M2, ipt)
        lms = numpy.sign(lms_) * numpy.abs(lms_) ** (1 / 0.43)
        xyz = solve(self.M1, lms)
        return xyz
