# Major package imports.
import wx
import wx.adv

import logging
log = logging.getLogger(__name__)


class AboutDialog(object):
    """ The toolkit specific implementation of an AboutDialog.  See the
    IAboutDialog interface for the API documentation.
    """

    ###########################################################################
    # Protected 'IDialog' interface.
    ###########################################################################

    def __init__(self, parent, about):
        info = wx.adv.AboutDialogInfo()

        # Load the image to be displayed in the about box.
        #image = self.about_image.create_image()
        icon = wx.Icon()
        try:
            icon.CopyFromBitmap(about.about_image.create_bitmap())
            info.SetIcon(icon)
        except:
            log.error("AboutDialog: bad icon file: %s" % about.about_image.absolute_path)

        info.SetName(about.about_title)
        info.SetVersion(about.about_version)
        info.SetDescription(about.about_description)
        info.SetWebSite(about.about_website)

        dialog = wx.adv.AboutBox(info)
