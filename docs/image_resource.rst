===============
Image Resources
===============

Image resources are enthought's way of caching images that are used in the UI.

Problems in image resource loading show up in py2exe/py2app bundles where
the use of the introspection provided by sys._getframe to get a path on the
filesystem doesn't work.

Debugging problems meant a lot of print statements...

In :py:class:`MImageResource`, _get_ref is called to find the pathname of the
image, so that's a good place for a debug print, using sys.stderr to make the
output show up in either the console (OS X) or the error log (Windows), e.g.::

    def _get_ref(self, size=None):
        """ Return the resource manager reference to the image. """

        if self._ref is None:
            self._ref = resource_manager.locate_image(self.name,
                    self.search_path, size)
            import sys
            print >> sys.stderr, "locating: %s %s %s %s" % (self.name, str(self.search_path), str(size), str(self._ref))

        return self._ref

Other places for debug printing::

    diff --git a/traitsui/image/image.py b/traitsui/image/image.py
    index b95a2a4..e719e09 100644
    --- a/traitsui/image/image.py
    +++ b/traitsui/image/image.py
    @@ -1220,6 +1220,7 @@ class ImageLibrary ( HasPrivateTraits ):
                 for path in paths.split( separator ):
                     result.extend( self._add_path( path ) )
     
    +        print >> sys.stderr, "traitsui.image.image: results=%s" % str([s.path for s in result])
             # Return the list of default volumes found:
             return result
     
    diff --git a/traitsui/ui_traits.py b/traitsui/ui_traits.py
    index c124c49..fd08709 100644
    --- a/traitsui/ui_traits.py
    +++ b/traitsui/ui_traits.py
    @@ -178,6 +178,9 @@ def convert_image ( value, level = 3 ):
                     result = ImageLibrary.image_resource( value )
                 except:
                     result = None
    +            import sys
    +            ref = result._get_ref()
    +            print >> sys.stderr, "value=%s, result=%s %s, ref=%s %s %s" % (value, str(result), str(result.absolute_path), str(ref), st
             else:
                 from pyface.image_resource import ImageResource
                 result = ImageResource( value, search_path = [ search_path ] )
