import logging
log = logging.getLogger(__name__)


class Serializable:
    name = "<name>"

    serializable_attributes = []

    def __init__(self):
        for kls in self.__class__.__mro__:
            if hasattr(kls, 'init_computed_attributes'):
                kls.init_computed_attributes(self)

    def __getstate__(self):
        """Custom jsonpickle state save routine

        This routine culls down the list of attributes that should be
        serialized, and in some cases changes their format slightly so they
        have a better mapping to json objects. For instance, json can't handle
        dicts with integer keys, so dicts are turned into lists of lists.
        Tuples are also turned into lists because tuples don't have a direct
        representation in json, while lists have a compact representation in
        json.
        """
        state = dict()
        state['name'] = self.name
        for kls in self.__class__.__mro__:
            if hasattr(kls, 'serializable_attributes'):
                for key in kls.serializable_attributes:
                    state[key] = getattr(self, key)
        return state

    def __setstate__(self, state):
        """Custom jsonpickle state restore routine

        The use of jsonpickle to recreate objects doesn't go through __init__,
        so there will be missing attributes when restoring old versions of the
        json. Once a version gets out in the wild and additional attributes are
        added to a segment, a default value should be applied here.
        """
        if state['name'] != self.name:
            raise TypeError(f"Can't restore {state['name']} to {self.name}")
        already_seen = set()
        for kls in self.__class__.__mro__:
            if hasattr(kls, 'serializable_attributes'):
                print(f"restoring {kls}: {kls.serializable_attributes}")
                missing = []
                for key in kls.serializable_attributes:
                    if key in already_seen:
                        print(f"already restored {key}")
                        continue
                    try:
                        setattr(self, key, state[key])
                        print(f"restored {key}: {getattr(self, key)}")
                        already_seen.add(key)
                    except KeyError:
                        print(f"missing key: {key}")
                        missing.append(key)
                kls.restore_missing_attributes(self, state, missing)
                kls.restore_renamed_attributes(self)
                kls.init_computed_attributes(self)

    def init_computed_attributes(self):
        """Hook to initialize/restore attributes that depend on serialized
        attributes but aren't themselves serialized. Called during __init__ and
        after all serialized attributes have been restored to this subclass.
        """
        pass

    def restore_missing_attributes(self, state, missing):
        """Hook for the future when extra serializable attributes are added to
        subclasses so new versions of the code can restore old saved files by
        providing defaults to any missing attributes.
        """
        pass

    def restore_renamed_attributes(self):
        """Hook for the future if attributes have been renamed. The old
        attribute names will have been restored in the __dict__.update in
        __setstate__, so this routine should move attribute values to their new
        names.
        """
        pass
