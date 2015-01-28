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

def adjustment(w, separation, convergence):
    return separation * (w - convergence)

def correct(coord, separation, convergence):
    if isinstance(coord, np.matrix):
        x,y,z,w = coord.tolist()[0]
    else:
        x,y,z,w = coord
    a = adjustment(w, separation, convergence)
    return ([x-a, y, z, w], [x+a, y, z, w])

def multiply(m1, m2):
	'''
	Does a matrix multiplication in a manner than is closer to how it would
	be done in shader assembly.
	'''
	assert(m1.shape == (4,4))
	assert(m2.shape == (4,4))
	t = m2.T
	r = np.matrix([[0.0]*4]*4)
	for y in range(4):
		for x in range(4):
			# r_y = dp4 m1_y t_x
			r[y,x] = np.dot(m1[y].A1, t[x].A1)
	return r

def to_regs(m, start=210):
    for i in range(4):
        print('def c%i, %g, %g, %g, %g' % (start+i, m[i, 0], m[i, 1], m[i, 2], m[i, 3]))
