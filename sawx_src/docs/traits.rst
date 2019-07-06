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

Trait notifications will not work correctly if you have a trait notifier method
that ends with ``_changed`` or ``_fired`` **and** there is a trait that has
the same name as the prefix before that ending.  E.g.  if there is a trait in
your object named ``active_editor`` and you attempt to use a trait notifier
method ``active_editor_changed`` as a trait notifier for a different object,
it will not receive notifications::

    class FrameworkTask(Task):
        active_editor = Property(Instance(IEditor), depends_on='editor_area.active_editor')
        
        [...]
        
        @on_trait_change('editor_area:active_editor')
        def _active_editor_changed(self, event):

It appears best to not use those reserved suffixes on any decorator or dynamic
trait notifiers.

Apparently it's a bad idea to mix static and dynamic trait notifications on a
single object.  I tried that, anyway and couldn't get it to work.  Maybe I'm
just not understanding how it's supposed to work.

