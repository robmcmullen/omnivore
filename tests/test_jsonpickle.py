import os

import jsonpickle

import omnivore.arch.machine as machine


class TestJsonPickle(object):
    def setup(self):
        self.machine = machine.Atari5200

    def test_simple(self):
        data = self.machine.__getstate__()
        print self.machine.all_trait_names()
        t = self.machine.trait('disassembler')
        print t
        print dir(t)
        for name in self.machine.all_trait_names():
            t = self.machine.trait(name)
            try:
                print name, t.transient, getattr(self.machine, name)
            except AttributeError:
                pass
        print data
        encoded = jsonpickle.encode(self.machine)
        print encoded
        decoded = jsonpickle.decode(encoded)
        print decoded
        print "Attributes!"
        for name in self.machine.all_trait_names():
            print name
        for name in decoded.all_trait_names():
            # a trait named "default_factory" shows up somehow in
            # all_trait_names, but not in the object itself, so ignore
            # anything not in the object's dict
            if hasattr(decoded, name):
                print name, getattr(decoded, name)
        print
        assert self.machine.disassembler == decoded.disassembler
        print self.machine.memory_map
        print decoded.memory_map
        assert self.machine.memory_map == decoded.memory_map
        assert self.machine == decoded

if __name__ == "__main__":
    t = TestJsonPickle()
    t.setup()
    t.test_simple()
