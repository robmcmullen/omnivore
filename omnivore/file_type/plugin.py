# Standard library imports.
import os.path

# Enthought library imports.
from envisage.api import ExtensionPoint, Plugin, ServiceOffer
from traits.api import List, Instance

from i_file_recognizer import IFileRecognizer, IFileRecognizerDriver

import logging
log = logging.getLogger(__name__)


class FileTypePlugin(Plugin):
    """ Plugin for identifying file types
    """

    # The Ids of the extension points that this plugin offers.
    RECOGNIZER = 'omnivore.file_recognizer'

    # Extension point IDs.
    SERVICE_OFFERS    = 'envisage.service_offers'

    #### 'IPlugin' interface ##################################################

    # The plugin's unique identifier.
    id = 'omnivore.file_type.plugin'

    # The plugin's name (suitable for displaying to the user).
    name = 'File Type'

    #### Extension points offered by this plugin ##############################

    recognizers = ExtensionPoint(
        List(Instance(IFileRecognizer)), id=RECOGNIZER, desc="""
    
    This extension point allows you to contribute file scanners that determine
    MIME types from a byte stream.
    
        """
    )

    #### Contributions to extension points made by this plugin ################

    service_offers = List(contributes_to=SERVICE_OFFERS)

    ###########################################################################
    # Protected interface.
    ###########################################################################

    def _service_offers_default(self):
        """ Trait initializer. """

        log.debug("in _service_offers_default")
        offer1 = ServiceOffer(
            protocol = 'omnivore.file_type.i_file_recognizer.IFileRecognizerDriver',
            factory  = self._create_file_recognizer_driver_service
        )

        return [offer1]

    def _create_file_recognizer_driver_service(self):
        """ Factory method for the File Recognizer Driver service. """

        log.debug("known recognizers: %s" % str(self.recognizers))

        # Lazy importing, even though this is a fundamental service and
        # therefore doesn't buy us anything.  But as an example it's useful.
        from .driver import FileRecognizerDriver
        return FileRecognizerDriver(recognizers=self.recognizers, application=self.application)
