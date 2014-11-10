#!/usr/bin/env python3

import numpy as np
from math import *

def translate(x, y, z):
    return np.matrix([
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 1, 0],
        [x, y, z, 1],
    ])

def scale(x, y, z):
    return np.matrix([
        [x, 0, 0, 0],
        [0, y, 0, 0],
        [0, 0, z, 0],
        [0, 0, 0, 1],
    ])

def rotate_x(angle):
    a = radians(angle)
    return np.matrix([
        [1,       0,      0, 0],
        [0,  cos(a), sin(a), 0],
        [0, -sin(a), cos(a), 0],
        [0,       0,      0, 1],
    ])

def rotate_y(angle):
    a = radians(angle)
    return np.matrix([
        [cos(a), 0, -sin(a), 0],
        [     0, 1,       0, 0],
        [sin(a), 0,  cos(a), 0],
        [     0, 0,       0, 1],
    ])

def rotate_z(angle):
    a = radians(angle)
    return np.matrix([
        [ cos(a), sin(a), 0, 0],
        [-sin(a), cos(a), 0, 0],
        [      0,      0, 1, 0],
        [      0,      0, 0, 1],
    ])

def projection(near, far, fov_horiz, fov_vert):
    w = 1 / tan(radians(fov_horiz) / 2)
    h = 1 / tan(radians(fov_vert)  / 2)
    q = far / (far - near)

    return np.matrix([
        [w, 0,       0, 0],
        [0, h,       0, 0],
        [0, 0,       q, 1],
        [0, 0, -q*near, 0]
    ])

def fov_w(matrix):
    return degrees(2 * atan(1/matrix[0, 0]))

def fov_h(matrix):
    return degrees(2 * atan(1/matrix[1, 1]))
