======
Traits
======


Trait Types
===========

Range
-----

The range trait is used to specify a bounded range of integers or floats.  I
can't seem to pick out the max value of the trait using any trait metadata
values.  E.g.  none of the following works to pull out the maximum value::

    class Helper(HasTraits):
        list_length = Range(low=4, high=50, value=10)
        
    helper = Helper()
    t = helper.trait('list_length')
    print t.high
    print dir(t)
    print helper.trait('list_length')
    print helper.trait('list_length').default
    print helper.trait('list_length')._high

The closest I can come is to use::

    print helper.trait('list_length').full_info(1,2,3)

which prints::

   4 <= an integer <= 50

so the trait obviously has knowledge of the max, but I can't get to it from
the outside.

Trait Notifications
===================

Apparently it's a bad idea to mix static and dynamic trait notifications on a
single object.  I tried that, anyway and couldn't get it to work.  Maybe I'm
just not understanding how it's supposed to work.

