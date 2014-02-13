# Standard library imports.
import os.path

# Enthought library imports.
from envisage.api import ExtensionPoint, Plugin, ServiceOffer
from traits.api import List, Instance

from i_file_recognizer import IFileRecognizer

class FileTypePlugin(Plugin):
    """ Plugin for identifying file types
    """

    # The Ids of the extension points that this plugin offers.
    RECOGNIZER = 'peppy.file_type.recognizer'

    # Extension point IDs.
    SERVICE_OFFERS    = 'envisage.service_offers'

    #### 'IPlugin' interface ##################################################

    # The plugin's unique identifier.
    id = 'peppy.file_type'

    # The plugin's name (suitable for displaying to the user).
    name = 'File Type'

    #### Extension points offered by this plugin ##############################

    # The identify_bytes extension point.
    #
    # Notice that we use the string name of the 'IMessage' interface rather
    # than actually importing it. This makes sure that the import only happens
    # when somebody actually gets the contributions to the extension point.
    recognizers = ExtensionPoint(
        List(Instance(IFileRecognizer)), id=RECOGNIZER, desc="""
    
    This extension point allows you to contribute file scanners that determine
    MIME types from a byte stream or file name.
    
        """
    )

    #### Contributions to extension points made by this plugin ################

    service_offers = List(contributes_to=SERVICE_OFFERS)

    ###########################################################################
    # Protected interface.
    ###########################################################################

    def _service_offers_default(self):
        """ Trait initializer. """

        print "in _service_offers_default"
        offer1 = ServiceOffer(
            protocol = 'file_type.i_file_recognizer.IFileRecognizer',
            factory  = self._create_file_recognizer_driver_service
        )

        return [offer1]

    def _create_file_recognizer_driver_service(self):
        """ Factory method for the File Recognizer Driver service. """

        print "in _create_file_recognizer_driver_service."
        print "  recognizers: %s" % str(self.recognizers)

        # Only do imports when you need to! This makes sure that the import
        # only happens when somebody needs an 'IMOTD' service.
        from .driver import FileRecognizerDriver
        return FileRecognizerDriver(recognizers=self.recognizers)
