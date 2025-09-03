import os

import numpy as np

from atrcopy import DefaultSegment, SegmentData

from omnivore.arch.disasm import parse_jumpman_level, get_jumpman_level, parse_jumpman_harvest, get_jumpman_harvest
from omnivore.utils.jumpman import *

class TestJumpmanLevel(object):
    def setup(self):
        self.items = [
            ([0xfe, 0x00, 0x04], 1),
            ([0xfc, 0x00, 0x40], 1),
            ([0xfd, 4, 9, 5], 1),
            ]

    def test_simple(self):
        for before, count in self.items:
            groups = parse_jumpman_level(before)
            for group in groups:
                text = get_jumpman_level(group)
                print("processed:", text)
            print("groups", groups)
            assert len(groups) == count

class TestJumpmanHarvest(object):
    def setup(self):
        self.items = [
            ([0x22, 0x04, 0x06, 0x4b, 0x28, 0x54, 0x2d], 1),
            ]

    def test_simple(self):
        for before, count in self.items:
            groups = parse_jumpman_harvest(before)
            for group in groups:
                text = get_jumpman_harvest(group)
                print("processed:", text)
            print("groups", groups)
            assert len(groups) == count

class TestJumpmanScreen(object):
    def setup(self):
        self.screen = np.zeros(40*90, dtype=np.uint8)
        data = np.frombuffer("\x04\x00\x00\x01\x01\x01\x01\x04\x00\x01\x01\x00\x01\x00\x04\x00\x02\x01\x01\x01\x01\xff\x04\x00\x00\x00\x00\x00\x00\x04\x00\x01\x00\x00\x00\x00\x04\x00\x02\x00\x00\x00\x00\xff\x02\x00\x00\x02\x02\x02\x06\x00\x02\x02\x02\x00\x01\x02\x02\x02\x06\x01\x02\x02\x08\x00\x02\x02\x02\x02\x02\x02\x02\x02\x02\x02\x00\x03\x02\x02\x02\x06\x03\x02\x02\xff\x08\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x08\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x08\x00\x03\x00\x00\x00\x00\x00\x00\x00\x00\xff\x04\x00\x00\x00\x03\x03\x00\x04\x00\x01\x03\x00\x00\x03\x04\x00\x02\x00\x03\x03\x00\xff\x04\x00\x00\x00\x00\x00\x00\x04\x00\x01\x00\x00\x00\x00\x04\x00\x02\x00\x00\x00\x00\xff\x01\x00\x00\x01\x01\x01\x01\x01\x01\x00\x02\x01\x01\x01\x03\x01\xff\x01\x00\x00\x02\x01\x00\x01\x02\x01\x01\x02\x02\x01\x01\x03\x02\xff\x02\x00\x00\x00\x00\x02\x00\x01\x00\x00\x02\x00\x02\x00\x00\x02\x00\x03\x00\x00\xff", dtype=np.uint8)
        r = SegmentData(data)
        segments = [DefaultSegment(r, 0x4000)]
        self.builder = JumpmanLevelBuilder(segments)

    def test_simple(self):
        level_defs = [
            # (
            #     0x2c00, 0x2ce9,
            #     "\xfe\x04\x00\xfc\x00@\xfd\x04\t\x05\xfd$\t\x06\xfdd\t\x06\xfd\x88\t\x05\xfd(\x19\x04\xfdh\x19\x04\xfd\x04\x1d\x05\xfdD\x1d\x06\xfd\x88\x1d\x05\xfd\x04-\x05\xfd$-\x02\xfd8-\x0c\xfdt-\x02\xfd\x88-\x05\xfd8=\x0c\xfd\x04E\x06\xfd\x84E\x06\xfd\x04U&\xfdHR\x04\xfe\x04\xff\xfd\x18\n\x01\xfd|\n\x01\xfd\x1c\x0b\x02\xfd\x80\x0b\x02\xfd<\x08\x03\xfd\\\x1c\x03\xfd\x1cD\x07\xfe\x04\x01\xfdX\x06\x03\xfd8\x1a\x03\xfdh>\x07\xfe\x00\x04\xfc,@\xfd\x0c\x05\x0b\xfd\x0cA\x05\xfd,\x05\x05\xfd<)\x05\xfdL\x19\x05\xfd\\)\x05\xfdl\x05\x05\xfd\x8c\x05\x0b\xfd\x8cA\x05\xfc\xaf@\xfd'0\x02\xfdw0\x02\xfc\x83@\xfd\x04\x06\x01\xfdD\x03\x01\xfdX\x03\x01\xfd\x98\x06\x01\xfd\x04\x15\x01\xfd\x98\x15\x01\xfd$%\x01\xfdx%\x01\xfd\x04R\x01\xfd@G\x01\xfd\\G\x01\xfd\x98R\x01\xff\x22\x04\x06K(T-bD\x03K(L(\x82X\x03K(L(\xc2\x98\x06K(d-$\x04\x15K(>-\xc4\x98\x15K(I-F$%K(L(\xa6x%K(L(,\x04RK(L(j@GK(L(\x8a\\GK(L(\xcc\x98RK(L(\xff\xfe\x00\x04\xfcV@\xfd\x0c!\x02\xff\xfe\x00\x04\xfcV@\xfd\x8c!\x02\xff\xfc\x16@\xfd\x18\n\x01\xfd\x1c\x0b\x01\xfd \n\x01\xff\xfc\x16@\xfd|\n\x01\xfd\x80\x0b\x01\xfd\x84\n\x01\xff",
            #     [
            #     Girder(-1, 50, 20, 5, 4, 0, 0xfff0),
            #     Ladder(-1, 60, 20, 5, 0, 4, 0xfff1),
            #     UpRope(-1, 70, 20, 5, 0, 4, 0xfff2),
            #     DownRope(-1, 80, 20, 5, 0, 4, 0xfff3),
            #     ],
            # ),
            (
                0x2c00, 0x2cd0,  # BUILDER
                '\xfe\x04\x00\xfc\x00@\xfd,\n\x03\xfdh\n\x03\xfd,\x1b\x03\xfdh\x1b\x03\xfd\x041\x08\xfd<1\n\xfd|1\x08\xfd\x04A\t\xfd0A\x07\xfdTA\x07\xfdxA\t\xfd\x04U\x05\xfd$Q\n\xfdTQ\n\xfd\x88U\x05\xfdN\x0f\x01\xfe\x04\xff\xfd\x18T\x03\xfd`\x1d\x02\xfd8\n\x06\xfe\x04\x01\xfd|R\x03\xfd8\x1c\x02\xfdP\x05\x06\xfe\x00\x04\xfc,@\xfd,\x07\x05\xfdl\x07\x05\xfd<-\t\xfd\\-\t\xfd\x1c-\x05\xfd|-\x05\xfd\x08=\x06\xfd\x90=\x06\xfc\xaf@\xfd/\x1e\x05\xfdo\x1e\x05\xfc\xc0@\xfdO\x1b\x04\xfc\x83@\xfdN\x02\x01\xfdN\x12\x01\xfd\n4\x01\xfd07\x01\xfdN6\x01\xfdl7\x01\xfd\x924\x01\xfd\x14R\x01\xfd*G\x01\xfdNG\x01\xfdrG\x01\xfd\x88R\x01\xff"\x14\x06K(L(bN\x02K(\x81-\xa2\x88\x06K(L($\x14\x14K(\xa2-dN\x12K(\x8c-\xa4\x88\x14K(\xb4-(\n4K(k-H07K(\xc6-hN6K(L(\x88l7K(\xce-\xa8\x924K(v-,\x14RK(A-J*GK(L(jNGK(L(\x8arGK(L(\xac\x88RK(V-\xff\xfe\x04\x00\xfc\x00@\xfd\x88\x1d\x05\xfe\x00\x04\xfc\xaf@\xfd\x8d \x03\xff\xfe\x04\x00\xfc\x00@\xfd\x04\x1d\x05\xfe\x00\x04\xfc\xaf@\xfd\x11 \x03\xff\xfe\x04\x00\xfc\x00@\xfd\x84\t\x06\xff\xfe\x04\x00\xfc\x00@\xfd\x04\t\x06\xff\xfe\x00\x04\xfc\xc0@\xfdO\x01\x07\xff\xfc\x83@\xfd\x14\x06\x01\xfd\x88\x06\x01\xfe\x00\x04\xfc\xc0@\xfdO\x01\x07\xff\xfe\x00\x04\xfc,@\xfd\x08\x05\x06\xfcV@\xfdl\x0f\x02\xff\xfe\x00\x04\xfc,@\xfd\x90\x05\x06\xfcV@\xfd,\x0f\x02\xff\xfc\x83@\xfd\x14\x14\x01\xff\xfc\x83@\xfd\x88\x14\x01\xff',
                []
                ),
            (
                0x2c00, 0x2c8e,
                '\xfe\x04\x00\xfc\x00@\xfd\x05\x0b%\xfc\x0e@\xfd%\x08\x02\xfdA\x08\x02\xfd\\\x08\x02\xfdy\x08\x02\xfd%T\x02\xfdAT\x02\xfd\\T\x02\xfdyT\x02\xfc\x00@\xfd\x16\x1d\x1d\xfd\x16.\x1d\xfd\x05?%\xfe\x00\x04\xfc,@\xfd\n\x07\x0e\xfd\x8e\x07\x0e\xfc\x83@\xfd(\x07\x01\xfdD\x07\x01\xfd_\x07\x01\xfd|\x07\x01\xfd(\x1a\x01\xfdD\x1a\x01\xfd_\x1a\x01\xfd|\x1a\x01\xfd(+\x01\xfdD+\x01\xfd_+\x01\xfd|+\x01\xfd(M\x01\xfdDM\x01\xfd_M\x01\xfd|M\x01\xffB(\x07\x00.L(bD\x07\x00.L(\x82_\x07\x00.L(\xa2|\x07\x00.L(D(\x1aK(\\-dD\x1aK(;-\x84_\x1aH(F-\xa4|\x1aK(v-F(+K(k-fD+K(\\-\x86_+K(Q-\xa6|+K(0-J(MK(L(jDMK(L(\x8a_MK(L(\xaa|MK(L(\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xfe\x00\x04\xfc\xaf@\xfd)A\x03\xff\xfe\x00\x04\xfc\xaf@\xfdEA\x03\xff\xfe\x00\x04\xfc\xaf@\xfd`A\x03\xff\xfe\x00\x04\xfc\xaf@\xfd}A\x03\xff\xfe\x00\x04\xfcV@\xfd\n/\x04\xfd\x8e/\x04\xff\xfe\x04\x00\xfc\x16@\xfd\x10?\x0e\xff\xfe\x04\x00\xfc\x16@\xfdP?\x10\xff',
                [],
                ),
            (
                0x2e80, 0x2ef4,  # GRAND PUZZLE II
                '\xfe\x04\x00\xfc\x00@\xfd\x04\x05&\xfd\x04U&\xfd\x04-&\xfd\x04\x19\t\xfdx\x19\t\xfd\x04A\t\xfdxA\t\xfdD\t\x06\xfd4\x19\x0e\xfdD\x1d\x06\xfdD1\x06\xfd4A\x0e\xfdDE\x06\xfe\x00\x04\xfc,@\xfd\x10\x01\x15\xfd\x88\x01\x15\xfc\x83@\xfd\x08\x02\x01\xfd\x94\x02\x01\xfd\x08\x16\x01\xfd\x94\x16\x01\xfd\x087\x01\xfd\x947\x01\xfd(R\x01\xfdtR\x01\xfd(\x02\x01\xfdt\x02\x01\xff\x22\x08\x02{/:/\xa2\x94\x02Z/L($\x08\x16{/O/\xa4\x94\x16u/L((\x087u/L(\xa8\x947b/L(L(Rj/L(\x8ctRj/L(B(\x02{/L(\x82t\x02{/L(\xfe\x04\x00\xfc\x16@\xfdL\t\x02\xfe\x00\x04\xfc\xaf@\xfdO\x08\x03\xff\xfe\x00\x04\xfc\xd1@\xfdO\x0c\x02\xff\xa9\x02\x8d\xc4/L{/\xa9\x02\x8d\xc5/L{/\xa9\x01\x8d\xc4/\x8d\xc5/L{/\xa9\x01\x8d\xff/`\xa9\x00\x8d\xff/',
                [],
                ),
            (
                0x2c00, 0x2c8e,
                '\xfc\x00@\xfe\x04\x00\xfd\x05\x0b%\xfc\x0e@\xfd%\x08\x02\xfdA\x08\x02\xfd\\\x08\x02\xfdy\x08\x02\xfd%T\x02\xfdAT\x02\xfd\\T\x02\xfdyT\x02\xfc\x00@\xfd\x16\x1d\x1d\xfd\x16.\x1d\xfd\x05?%\xfc,@\xfe\x00\x04\xfd\n\x07\x0e\xfd\x8e\x07\x0e\xfc\xc0@\xfd6\x0e\x0f\xfc\x83@\xfd(\x07\x01\xfdD\x07\x01\xfd_\x07\x01\xfd|\x07\x01\xfd(\x1a\x01\xfdD\x1a\x01\xfd_\x1a\x01\xfd|\x1a\x01\xfd(+\x01\xfdD+\x01\xfd_+\x01\xfd|+\x01\xfd(M\x01\xfdDM\x01\xfd_M\x01\xfd|M\x01\xff\xfcV@\xfe\x00\x04\xfd\n/\x04\xfd\x8e/\x04\xff\xfc\xaf@\xfe\x00\x04\xfdEA\x03\xff\xfc\xaf@\xfe\x00\x04\xfd`A\x03\xff\xfc\x16@\xfe\x04\x00\xfdP?\x10\xff\xfc\x16@\xfe\x04\x00\xfd\x10?\x0e\xff\xfcV@\xfe\x00\x04\xfd\n/\x04\xfd\x8e/\x04\xff\xfc\xaf@\xfe\x00\x04\xfd}A\x03\xff\xfc\xaf@\xfe\x00\x04\xfd)A\x03\xffB(\x07\x00.K(bD\x07\x00.K(\x82_\x07\x00.K(\xa2|\x07\x00.K(D(\x1aK(\x95,dD\x1aK(\xa4,\x84_\x1aH(\xaf,\xa4|\x1aK(\xba,F(+K(\xc5,fD+K(\xd0,\x86_+K(\xdf,\xa6|+K(\xea,J(MK(K(jDMK(K(\x8a_MK(K(\xaa|MK(K(\xff\xfd\x8e/\x04\xff\xfe\x04\x00\xfc\x16@\xfd\x10?\x0e\xff\xfe\x04\x00\xfc\x16@\xfdP?\x10\xff',
                [],
                ),




            # np.frombuffer("\xfe\x00\x04\xfcV@\xfd\n \x04\xfd\x8e \x04\xff", dtype=np.uint8),
            # np.frombuffer("\xfe\x04\x00\xfc\x16@\xfd\x10?\x0e\xff", dtype=np.uint8),
        ]

        for addr, haddr, d, objects in level_defs:
            if type(d) == str:
                d = np.frombuffer(d, dtype=np.uint8)
            c = self.builder.parse_objects(d)
            print("\n".join([str(a) for a in c]))
            #state = self.builder.draw_objects(self.screen, c)
            self.builder.parse_harvest_table(d, addr, haddr, c)
            self.builder.add_objects(objects, c)
            print("\n".join([str(a) for a in c]))

            d2, haddr2, rl, num_p = self.builder.create_level_definition(addr, 0, 6, c)
            print(d2[0:haddr2 - addr])
            print(d2[haddr2 - addr:])
            print(rl)
            c2 = self.builder.parse_objects(d2)
            self.builder.parse_harvest_table(d2, addr, haddr2, c2)
            print("\n".join([str(a) for a in c2]))
            for a1, a2 in zip(c, c2):
                print(a1 == a2)
                print(" 1)", a1)
                print(" 2)", a2)
                if not a1 == a2:
                    for h1, h2 in zip(a1.trigger_painting, a2.trigger_painting):
                        print("  ", h1 == h2)
                        print("  h1: %s" % h1)
                        print("  h2: %s" % h2)
                assert a1 == a2
                print()
            print(c == c2)

class TestJumpmanAdd(object):
    def setup(self):
        self.builder = JumpmanLevelBuilder(None)

    def test_simple(self):
        level_defs = [
            (
                "\xfe\x04\x00\xfc\x00@\xfd\x04\t\x05\xfc\x83@\xfd\x04\x06\x01\xfd\x44\x46\x01\xff",
                "\x22\x04\x06K(T-\xff",
                [(0x2d54, "\xfc\x16@\xfd\x18\n\x01\xfd\x1c\x0b\x01\xfd \n\x01\xff"),
                ],
                [
                Girder(-1, 50, 20, 5, 4, 0),
                Ladder(-1, 60, 20, 5, 0, 4),
                UpRope(-1, 70, 20, 5, 0, 4),
                DownRope(-1, 80, 20, 5, 0, 4),
                ],
            ),

        ]

        for obj_data, harvest_data, paint_data, objects in level_defs:
            d = np.zeros((512,), dtype=np.uint8)
            addr = 0x2c00
            haddr = addr + len(obj_data)
            t = np.frombuffer(obj_data + harvest_data, dtype=np.uint8)
            d[0:len(t)] = t
            for a, t in paint_data:
                t = np.frombuffer(t, dtype=np.uint8)
                d[a - addr:a - addr + len(t)] = t
            c = self.builder.parse_objects(d)
            print("\n".join([str(a) for a in c]))
            #state = self.builder.draw_objects(self.screen, c)
            self.builder.parse_harvest_table(d, addr, haddr, c)
            for a in c:
                print(a)
                if a.single and not a.trigger_painting:
                    self.builder.add_objects(objects, a.trigger_painting)
            #self.builder.add_objects(objects, c)
            print("\n".join([str(a) for a in c]))

            d2, haddr2, rl, num_p = self.builder.create_level_definition(addr, 0, 6, c)
            print(d2[0:haddr2 - addr])
            print(d2[haddr2 - addr:])
            print(rl)
            c2 = self.builder.parse_objects(d2)
            self.builder.parse_harvest_table(d2, addr, haddr2, c2)
            print("\n".join([str(a) for a in c2]))
            for a1, a2 in zip(c, c2):
                print(a1 == a2)
                print(" 1)", a1)
                print(" 2)", a2)
                if not a1 == a2:
                    for h1, h2 in zip(a1.trigger_painting, a2.trigger_painting):
                        print("  ", h1 == h2)
                        print("  h1: %s" % h1)
                        print("  h2: %s" % h2)
                print()
            print(c == c2)

class TestJumpmanPainting(object):
    def setup(self):
        self.builder = JumpmanLevelBuilder(None)
        self.addr = 0x2c00

    def test_simple(self):
        p1 = Peanut(1, 10, 10, 1)
        p2 = Peanut(2, 20, 20, 1)
        p3 = Peanut(3, 30, 30, 1)
        p1.trigger_painting = [p2]
        p2.trigger_painting = [p3]
        objects = [p1]
        print(p1)
        d2, haddr2, rl, num_p = self.builder.create_level_definition(self.addr, 0, 6, objects)
        print(d2[0:haddr2 - self.addr])
        print(d2[haddr2 - self.addr:])
        print(rl)
        print(num_p)
        assert num_p == 3
        c2 = self.builder.parse_objects(d2)
        self.builder.parse_harvest_table(d2, self.addr, haddr2, c2)
        print(c2)
        assert len(c2) == 1
        assert len(c2[0].trigger_painting) == 1
        assert len(c2[0].trigger_painting[0].trigger_painting) == 1

class TestJumpmanBounds(object):
    def setup(self):
        pass

    def test_simple(self):
        level_defs = [
            (
                DrawObjectBounds(((50, 20), (81, 39))),
                [
                Girder(-1, 50, 20, 5, 4, 0),
                Ladder(-1, 60, 20, 5, 0, 4),
                UpRope(-1, 70, 20, 5, 0, 4),
                DownRope(-1, 80, 20, 5, 0, 4),
                ],
            ),
            (
                DrawObjectBounds(((50, 20), (69, 22))),
                [
                Girder(-1, 50, 20, 5, 4, 0),
                ],
            ),
            (
                DrawObjectBounds(((34, 20), (53, 22))),
                [
                Girder(-1, 50, 20, 5, -4, 0),
                ],
            ),

        ]

        for expected, objects in level_defs:
            print(objects)
            bounds = DrawObjectBounds.get_bounds(objects)
            print(bounds)
            print(expected)
            assert expected == bounds
            print("works")

            for o in objects:
                o.flip_vertical(bounds)
                print(o)

            flipped_bounds = DrawObjectBounds.get_bounds(objects)
            print("flipped bounds", flipped_bounds)
            assert bounds == flipped_bounds


class TestJumpmanTriggers(object):
    def setup(self):
        with open("triggers1.s", "w") as fh:
            fh.write("""
*=$2910

trigger1
        RTS

*=$2920

trigger2
        RTS

*=$2930

trigger3
        RTS

*=$2940

trigger4
        RTS
                """)
        with open("triggers2.s", "w") as fh:
            fh.write("""
*=$2d10

trigger1
        RTS

*=$2d20

trigger2
        RTS

*=$2d30

trigger3
        RTS

*=$2d40

trigger4
        RTS
                """)
        with open("triggers3.s", "w") as fh:
            fh.write("""
*=$2e10

trigger1
        RTS

*=$2e20

trigger2
        RTS

*=$2e30

trigger3
        RTS
                """)
        self.builder = JumpmanLevelBuilder(None)
        self.addr = 0x2c00

    def get_sample_objects(self):
        p1 = Peanut(1, 10, 10, 1)
        p1.trigger_function = 0x2910
        p2 = Peanut(2, 20, 20, 1)
        p2.trigger_function = 0x2920
        p3 = Peanut(3, 30, 30, 1)
        p3.trigger_function = 0x2930
        p1.trigger_painting = [p2]
        p2.trigger_painting = [p3]
        p4 = Peanut(4, 40, 40, 1)
        p4.trigger_function = 0x2940
        p5 = Peanut(5, 50, 50, 1)
        p5.trigger_function = 0x4fff  # not pointing to anything in assembly
        objects = [p1, p4, p5]
        d2, haddr2, rl, num_p = self.builder.create_level_definition(self.addr, 0, 6, objects)
        print(d2[0:haddr2 - self.addr])
        print(d2[haddr2 - self.addr:])
        print(rl)
        print(num_p)
        assert num_p == 5
        c2 = self.builder.parse_objects(d2)
        self.builder.parse_harvest_table(d2, self.addr, haddr2, c2)
        print(c2)
        return c2

    def test_address_mapping(self):
        code1 = JumpmanCustomCode("triggers1.s")
        code2 = JumpmanCustomCode("triggers2.s")
        t = code1.triggers
        assert len(t) == 4
        t = code2.triggers
        assert len(t) == 4
        c2 = self.get_sample_objects()
        old_map = code1.triggers
        new_map = code2.triggers
        changed, orphaned, not_labeled = self.builder.update_triggers(old_map, new_map, c2)
        print(changed)
        print(orphaned)
        print(not_labeled)
        assert len(changed) == 4
        assert len(orphaned) == 0
        assert len(not_labeled) == 1
        p1, p4, p5 = c2
        assert p1.trigger_function == 0x2d10
        assert p4.trigger_function == 0x2d40

    def test_address_mapping_missing(self):
        code1 = JumpmanCustomCode("triggers1.s")
        code2 = JumpmanCustomCode("triggers3.s")
        t = code1.triggers
        assert len(t) == 4
        t = code2.triggers
        assert len(t) == 3
        c2 = self.get_sample_objects()
        old_map = code1.triggers
        new_map = code2.triggers
        changed, orphaned, not_labeled = self.builder.update_triggers(old_map, new_map, c2)
        print(changed)
        print(orphaned)
        print(not_labeled)
        assert len(changed) == 3
        assert len(orphaned) == 1
        assert len(not_labeled) == 1
        p1, p4, p5 = c2
        assert p1.trigger_function == 0x2e10
        assert p4.trigger_function == 0x2940


if __name__ == "__main__":
    t = TestJumpmanScreen()
    t.setup()
    t.test_simple()
    t = TestJumpmanAdd()
    t.setup()
    t.test_simple()
    t = TestJumpmanPainting()
    t.setup()
    t.test_simple()
    t = TestJumpmanBounds()
    t.setup()
    t.test_simple()

    o = Girder(-1, 50, 20, 5, -4, -1)
    print("object", o)
    bounds = DrawObjectBounds.get_bounds([o])
    print("bounds", bounds)
    o.flip_vertical(bounds)
    flipped_bounds = DrawObjectBounds.get_bounds([o])
    print("flipped bounds", flipped_bounds)
