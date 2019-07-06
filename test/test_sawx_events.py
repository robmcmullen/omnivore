import sys
import unittest

from sawx import events


def mp_do_nothing(sender, *args):
    # Does nothing
    pass


class BasicEventHandlerTest(unittest.TestCase):
    def test_EventHandler(self):
        self.assertRaises(TypeError, events.EventHandler)
        self.assertIsInstance(events.EventHandler(None), events.EventHandler)
        self.assertIsInstance(events.EventHandler(132), events.EventHandler)
        self.assertIsInstance(events.EventHandler("Test"), events.EventHandler)

        ev = events.EventHandler(None)
        self.assertEqual(ev.sender, None)
        ev = events.EventHandler("Test")
        self.assertEqual(ev.sender, "Test")
        self.assertEqual(len(ev), 0)
        self.assertEqual(len(ev.callbacks), 0)

    def test_EventHandler_add__iadd__(self):
        ev = events.EventHandler(None)

        def doadd(ev, cb):
            ev += cb

        def callback():
            pass

        self.assertRaises(TypeError, doadd, ev, None)
        self.assertRaises(TypeError, doadd, ev, "Test")
        self.assertRaises(TypeError, doadd, ev, 1234)

        self.assertEqual(len(ev), 0)
        ev += callback
        self.assertEqual(len(ev), 1)
        for x in range(4):
            ev += callback
        self.assertEqual(len(ev), 5)

        self.assertRaises(TypeError, ev.add, None)
        self.assertRaises(TypeError, ev.add, "Test")
        self.assertRaises(TypeError, ev.add, 1234)

        self.assertEqual(len(ev), 5)
        ev.add(callback)
        self.assertEqual(len(ev), 6)
        for x in range(4):
            ev.add(callback)
        self.assertEqual(len(ev), 10)

    def test_EventHandler_remove__isub__(self):
        ev = events.EventHandler(None)

        def doremove(ev, cb):
            ev -= cb

        def callback():
            pass

        for x in range(10):
            ev += callback
        self.assertEqual(len(ev), 10)

        self.assertRaises(TypeError, ev.remove)
        for invval in ("Test", None, 1234, self.assertEqual):
            self.assertRaises(ValueError, ev.remove, invval)
            self.assertRaises(ValueError, doremove, ev, invval)
        self.assertEqual(len(ev), 10)
        ev.remove(callback)
        self.assertEqual(len(ev), 9)
        ev -= callback
        self.assertEqual(len(ev), 8)
        for x in range(3):
            ev.remove(callback)
            ev -= callback
        self.assertEqual(len(ev), 2)

    def test_EventHandler__call__(self):
        ev = events.EventHandler("Test")
        testsum = []

        def callback(evt):
            self.assertEqual(evt.sender, "Test")
            sumval = evt[0]
            sumval.append(1)

        for x in range(10):
            ev += callback
        self.assertEqual(len(ev), 10)
        results = ev(testsum)
        self.assertEqual(len(testsum), 10)
        for v in testsum:
            self.assertEqual(v, 1)
        self.assertEqual(len(results), 10)
        for v in results:
            self.assertIsNone(v)

    def test_EventHandler__call__WithKeywords(self):
        ev = events.EventHandler("Test")
        testsum = []

        def callback(evt):
            self.assertEqual(evt.sender, "Test")
            evt.testsum.append(1)

        for x in range(10):
            ev += callback
        self.assertEqual(len(ev), 10)
        results = ev(testsum=testsum)
        self.assertEqual(len(testsum), 10)
        for v in testsum:
            self.assertEqual(v, 1)
        self.assertEqual(len(results), 10)
        for v in results:
            self.assertIsNone(v)


class TestWeakrefEventHandler:
    def setup(self):
        pass

    def test_weakref_removal(self):
        ev = events.EventHandler("weakref")
        testsum = []

        def callback_function(evt):
            assert evt.sender == "weakref"
            sumval = evt[0]
            sumval.append(1)

        class receiver_object:
            def callback(self, evt):
                assert evt.sender == "weakref"
                sumval = evt[0]
                sumval.append(1)

        r = receiver_object()

        ev += r.callback
        ev += callback_function

        results = ev(testsum)
        assert len(testsum) == 2

        del r
        testsum = []

        results = ev(testsum)
        assert len(testsum) == 1

    def test_weakref_removal_with_keywords(self):
        ev = events.EventHandler("weakref")
        testsum = []

        def callback_function(evt):
            assert evt.sender == "weakref"
            evt.testsum.append(1)

        class receiver_object:
            def callback(self, evt):
                assert evt.sender == "weakref"
                evt.testsum.append(1)

        r = receiver_object()

        ev += r.callback
        ev += callback_function

        results = ev(testsum=testsum)
        assert len(testsum) == 2

        del r
        testsum = []

        results = ev(testsum=testsum)
        assert len(testsum) == 1





if __name__ == '__main__':
    sys.exit(unittest.main())
