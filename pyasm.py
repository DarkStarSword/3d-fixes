#!/usr/bin/env python3

'''
Implements shader assembly like semantics in python

Provides a Register class which implements masks and swizzles, and a number of
functions which behave like the asm instructions.

The result is that shader assembly can be transformed to run in python without
too much massaging, increasing it's debuggability.

Note that the main difference when using this vs actual shader assembly is the
semantics of the destination register. Whereas in assembly you might do this:

mad r1, r2, r3, r4

Here you would move the destination register (r1) out like this:

r1 = mad(r2, r3, r4)

Make sure you use the mov() function to copy a register and not simply
assigning it, as the later would end up creating a reference, not a copy.
'''

class Register(object):
    # FUTURE: Might be better to make this type immutable so that something
    # like "r1 = r2; r2.x = 0" doesn't change r1.x (though this syntax should
    # not be used anyway: use r1 = mov(r2) and think like assembly)

    component_idx = {
        'x': 0, 'r': 0,
        'y': 1, 'g': 1,
        'z': 2, 'b': 2,
        'w': 3, 'a': 3,
    }

    def __init__(self, vals=None):
        if vals is None:
            vals = [0]*4
        else:
            try:
                if len(vals) != 4:
                    raise AttributeError(vals)
            except TypeError:
                vals = [vals]*4
        object.__setattr__(self, 'vals', vals)

    @classmethod
    def _validate_components(cls, components):
        if len(components) > 4:
            raise AttributeError(components)
        if set(components).difference(set(cls.component_idx)):
            raise AttributeError(components)

    def __getitem__(self, key):
        return self.vals[key]

    def __setitem__(self, key, value):
        self.vals[key] = value

    def __getattr__(self, components):
        # Read with swizzle
        self._validate_components(components)
        ret = Register()
        for i in range(4):
            try:
                component = self.component_idx[components[i]]
            except IndexError:
                # Short swizzle - reuse final component
                pass
            ret[i] = self.vals[component]
        return ret

    def __setattr__(self, components, value):
        # Write with mask
        self._validate_components(components)
        new_vals = self.vals[:]
        for component in 'xaybzcwd':
            if not components:
                break
            if component != components[0]:
                continue
            components = components[1:]
            component_idx = self.component_idx[component]
            try:
                val = value[component_idx]
            except TypeError:
                val = value
            new_vals[component_idx] = val;
        if components:
            raise AttributeError(components)
        object.__setattr__(self, 'vals', new_vals)

    def __neg__(self):
        return Register([ -x for x in self.vals ])

    def __len__(self):
        return 4

    def __repr__(self):
        return repr(self.vals)

def mov(source):
    return Register(source)

def add(source1, source2):
    return Register([ a + b for (a,b) in zip(source1, source2) ])

def mul(source1, source2):
    return Register([ a * b for (a,b) in zip(source1, source2) ])

def mad(source1, source2, source3):
    return Register([ a * b + c for (a,b,c) in zip(source1, source2, source3) ])

def dp3(source1, source2):
    return Register(sum(mul(source1.xyz, source2.xyz)[0:3]))

def dp4(source1, source2):
    return Register(sum(mul(source1.xyz, source2.xyz)))

def rcp(source):
    try:
        return Register(1 / source[0])
    except ZeroDivisionError:
        return Register(float('inf'))
