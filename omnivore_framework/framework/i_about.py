from traits.api import Interface, Instance, Str, Unicode
from pyface.api import ImageResource


class IAbout(Interface):

    about_title = Unicode

    about_version = Unicode

    about_description = Unicode

    about_website = Str

    about_image = Instance(ImageResource)
