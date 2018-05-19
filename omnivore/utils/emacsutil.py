# peppy Copyright (c) 2006-2010 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Utility functions for interacting with emacs

These text utilities have no dependencies on any other part of peppy, and
therefore may be used independently of peppy.

The Emacs manual has a description of how U{file local
variables<http://www.gnu.org/software/emacs/manual/html_node/emacs/Specifying-File-Variables.html#Specifying-File-Variables>} are stored.
"""
import re


def parseModeline(line):
    """Determine if line specifies a major mode.
    
    Parse a potential emacs major mode specifier line into the
    mode and the optional variables.  The mode may appears as any
    of::

      -*-C++-*-
      -*- mode: Python; -*-
      -*- mode: Ksh; var1:value1; var3:value9; -*-

    @param header: first x bytes of the file to be loaded
    @return: two-tuple of the mode and a dict of the name/value pairs.
    @rtype: tuple
    """
    match=re.search(r'-\*\-\s*(mode:\s*(.+?)|(.+?))(\s*;\s*(.+?))?\s*-\*-',line)
    vars={}
    if match:
        varstring=match.group(5)
        if varstring:
            try:
                for nameval in varstring.split(';'):
                    s=nameval.strip()
                    if s:
                        name,val=s.split(':')
                        vars[name.strip()]=val.strip()
            except:
                pass
        if match.group(2):
            return (match.group(2),vars)
        elif match.group(3):
            return (match.group(3),vars)
    return None, vars


def applyEmacsFileLocalSettings(stc):
    """Scan the stc for file local settings.
    
    Emacs uses U{file local
    variables<http://www.gnu.org/software/emacs/manual/html_node/emacs/Specifying-    File-Variables.html#Specifying-File-Variables>}
    to customize major modes on a per-file basis.  This method parses both
    the modeline specifier (the second or first line depending on whether the
    file is a shell script or not) and the local variables list at the end of
    the file.
    
    Emacs modes can have many local variables, so it's left to the major mode
    itself to parse most of them.  There are, however, some U{standard buffer
    local variables<http://www.gnu.org/software/emacs/elisp/html_node/Standard-Buffer_002dLocal-Variables.html>}
    that emacs does recognize.
    
    @param stc: styled text control that will be used to apply settings
    
    @return: list of settings affected.  Settings changed are reported as the
    name of the wx.stc method used for each setting, with the 'Set' removed.
    If the tab width is changed, the setting is reported as 'TabWidth'.
    """
    modeline = stc.GetLine(0)
    if modeline.startswith("#!") and stc.GetLineCount() > 1:
        modeline = stc.GetLine(1)
    mode, vars = parseModeline(modeline)

    settings_changed = []

    # check for integers.  int_mapping takes the emacs string to the name of
    # the stc getter/setter function.
    int_mapping = {'fill-column': 'EdgeColumn',
                   'tab-width': 'TabWidth',
                   }
    for name, setting in list(int_mapping.items()):
        if name in vars:
            # Construct the name of the stc setting function and set the value
            func = getattr(stc, "Set%s" % setting)
            func(int(vars[name]))
            settings_changed.append(setting)

    # check for booleans -- emacs uses 'nil' for false, everything else for true
    bool_mapping = {'use-tabs': 'UseTabs',
                    }
    for name, setting in list(bool_mapping.items()):
        if name in vars:
            func = getattr(stc, "Set%s" % setting)
            func(vars[name] != 'nil')
            settings_changed.append(setting)

    # check for more complicated settings
    if 'cursor-type' in vars:
        text = vars['cursor-type']
        match = re.search(r'\(\s*bar\s*\.\s*([0-9]+)', text)
        if match:
            width = int(match.group(1))
            stc.SetCaretWidth(width)
            settings_changed.append('CaretWidth')

    return settings_changed, vars
