=======
Plugins
=======

Plugins are subclassed from :py:class:`envisage.plugin.Plugin` (import as::

   from envisage.api Plugin

In your own subclass of Plugin, the methods :py:meth:`start` and :py:meth:`stop`
to provide some startup or shutdown code; these are not used by the Enthought
framework itself so they are free to be overridden in your own code.

Plugin Configuration Directory
==============================

Each plugin is also initialized with its own unique directory (based on
the plugin id) under the :py:attr:`envisage.application.Application.home`
directory.  This directory is intended to be used by this plugin only, for any
purpose needed by the plugin.

Traits Summary
==============

In addition to the traits defined in the interface
:py:class:`envisage.plugin.IPlugin` (the base class for
:py:class:`envisage.plugin.Plugin`), there are additional traits provided
by interfaces::

    # The activator used to start and stop the plugin.
    activator = Instance(IPluginActivator)

    # The application that the plugin is part of.
    application = Instance('envisage.api.IApplication')

    # The name of a directory (created for you) that the plugin can read and
    # write to at will.
    home = Str

    # The plugin's unique identifier.
    #
    # Where 'unique' technically means 'unique within the plugin manager', but
    # since the chances are that you will want to include plugins from external
    # sources, this really means 'globally unique'! Using the Python package
    # path might be useful here. e.g. 'envisage'.
    id = Str

    # The plugin's name (suitable for displaying to the user).
    #
    # If no name is specified then the plugin's class name is used with an
    # attempt made to turn camel-case class names into words separated by
    # spaces (e.g. if the class name is 'MyPlugin' then the name would be
    # 'My Plugin'). Of course, if you really care about the actual name, then
    # just set it!
    name = Str

    #### 'IExtensionPointUser' interface ######################################

    # The extension registry that the object's extension points are stored in.
    extension_registry = Property(Instance(IExtensionRegistry))

    #### 'IServiceUser' interface #############################################

    # The service registry that the object's services are stored in.
    service_registry = Property(Instance(IServiceRegistry))
