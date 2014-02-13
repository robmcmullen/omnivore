# Standard library imports.
import os.path

# Enthought library imports.
from envisage.api import ExtensionPoint, Plugin, ServiceOffer
from traits.api import List


class FileTypePlugin(Plugin):
    """ Plugin for identifying file types
    """

    # Extension point IDs.
    SERVICE_OFFERS    = 'envisage.service_offers'

    #### 'IPlugin' interface ##################################################

    # The plugin's unique identifier.
    id = 'peppy.file_type'

    # The plugin's name (suitable for displaying to the user).
    name = 'File Type'

    #### Contributions to extension points made by this plugin ################

    service_offers = List(contributes_to=SERVICE_OFFERS)

    ###########################################################################
    # Protected interface.
    ###########################################################################

    def _service_offers_default(self):
        """ Trait initializer. """

        print "in _service_offers_default"
        offer1 = ServiceOffer(
            protocol = 'file_type.i_filetype.IFileType',
            factory  = self._create_image_file_type_service
        )

        return [offer1]

    def _create_image_file_type_service(self):
        """ Factory method for the ImageFileType service. """

        # Only do imports when you need to! This makes sure that the import
        # only happens when somebody needs an 'IMOTD' service.
        from .image import ImageFileType

        return ImageFileType()
