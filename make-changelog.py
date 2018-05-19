#!/usr/bin/env python

import os,sys,re,os.path,time, subprocess
from io import StringIO
from datetime import date
from optparse import OptionParser
from string import Template
from distutils.version import StrictVersion

module=None

dateformat = "%m/%d/%Y"

versionre = "([0-9]+(\.[0-9]+)+([ab][0-9]+)?)"
versionre = "(([0-9]+)\.([0-9]+)(?:\.([0-9]+))?(([ab])([0-9]+))?)"

author = "Rob McMullen <feedback@playermissile.com>"

def findLatestChangeLogVersion(options):
    fh = open("ChangeLog")
    release_date = date.today().strftime("%d %B %Y")
    version = "0.0.0"
    versions = []
    codename = ""
    for line in fh:
        match = re.match('(\d+-\d+-\d+).*',line)
        if match:
            if options.verbose: print('found date %s' % match.group(1))
            release_date = date.fromtimestamp(time.mktime(time.strptime(match.group(1),'%Y-%m-%d'))).strftime('%d %B %Y')
        match = re.match('\s+\*\s*[Rr]eleased Omnivore-([0-9]+\.[0-9]+(?:\.[0-9]+)?)',line)
        if match:
            if options.verbose: print('found version %s' % match.group(1))
            version = match.group(1)
            versions.append(version)
        release_date = None
    if release_date is None:
        release_date = date.today().strftime("%d %B %Y")
    if not versions:
        version = "0.0"
    else:
        version = versions[0]
    return version, release_date, versions

def findLatestInGit(options):
    version = StrictVersion("0.0.0")
    tags = subprocess.Popen(["git", "tag", "-l"], stdout=subprocess.PIPE).communicate()[0]
    for tag in tags.splitlines():
        match = re.match(r'%s$' % versionre, tag)
        if match:
            found = StrictVersion(match.group(1))
            if found > version:
                version = found
            if options.verbose: print("found %s, latest = %s" % (found, version))
    return str(version)

def next_version(tagged_version):
    t = tagged_version.split(".")
#    print t
    last = t[-1]
    try:
        last = str(int(last) + 1)
    except ValueError:
        for i in range(0, len(last) - 1):
            try:
                last = last[0:i+1] + str(int(last[i+1:]) + 1)
                break
            except ValueError:
                pass
    t[-1] = last
    return ".".join(t)

def getCurrentGitMD5s(tag, options):
    text = subprocess.Popen(["git", "rev-list", "%s..HEAD" % tag], stdout=subprocess.PIPE).communicate()[0]
    md5s = text.splitlines()
    return md5s

def getInitialsFromEmail(email):
    name, domain = email.split("@")
    names = name.split(".")
    initials = []
    for name in names:
        initials.append(name[0].upper())
    return "".join(initials)

def isImportantChangeLogLine(text):
    if text.startswith("Merge branch"):
        return False
    if text.startswith("updated ChangeLog & Version.py for"):
        return False
    return True

def verify_tag(tag):
    tag = str(tag)
    if tag == "HEAD":
        return tag
    verify = subprocess.Popen(["git", "tag", "-l", "%s" % (tag)], stdout=subprocess.PIPE).communicate()[0]
    if not verify:
        tag += ".0"
        verify = subprocess.Popen(["git", "tag", "-l", "%s" % (tag)], stdout=subprocess.PIPE).communicate()[0]
        if not verify:
            raise RuntimeError("tag not found! %s" % tag)
    return tag

def getGitChangeLogSuggestions(tag, options, top="HEAD"):
    tag = verify_tag(tag)
    top = verify_tag(top)
    if options.verbose: print(tag)
    suggestions = []
    text = subprocess.Popen(["git", "log", "--pretty=format:%ae--%B", "%s..%s" % (top, tag)], stdout=subprocess.PIPE).communicate()[0]
    lines = text.splitlines()
    print(lines)
    first = True
    for line in lines:
        if first:
            if "--" in line and "@" in line:
                print(line)
                email, text = line.split("--", 1)
                if isImportantChangeLogLine(text):
                    suggestions.append("* %s" % text)
                first = False
        elif not line:
            first = True
    return suggestions

def getChangeLogBlock(version, next_oldest_version, date, options):
    new_block = []
    suggestions = getGitChangeLogSuggestions(version, options, next_oldest_version)
    new_block.append("%s  %s" % (date, author))
    new_block.append("")
    if str(version) == "HEAD":
        new_block.append("...to be included in next version:")
    else:
        new_block.append("* Released Omnivore-%s" % version)
    for line in suggestions:
        new_block.append(line)
    new_block.append("")
    print("\n".join(new_block))
    return new_block

def prepend(filename, block):
    fh = open(filename)
    text = fh.read()
    fh.close()
    
    fh = open(filename, "w")
    fh.write("\n".join(block))
    fh.write("\n\n")
    fh.write(text)
    fh.close()

def replace(filename, block):
    fh = open(filename)
    current = []
    store = False
    for line in fh:
        if store:
            current.append(line)
        if not line.strip(): # skip until first blank line
            store = True
    fh.close()
    
    fh = open(filename, "w")
    fh.write("\n".join(block))
    fh.write("\n\n")
    fh.write("".join(current))
    fh.close()

def rebuild(options):
    # Command to list date of tag and tag (although newest to oldest which is
    # the opposite order than we need, hence the reversed below)
    tags = subprocess.Popen(["git", "log", "--tags", "--simplify-by-decoration", "--pretty=%ai %d"], stdout=subprocess.PIPE).communicate()[0]
    blocks = []
    next_oldest = StrictVersion("0.0.0")
    for line in reversed(tags.splitlines()):
        #day, _, _, tag = line.split()  # doesn't work; may list multiple tags
        stuff = line.split()
        day = stuff[0]
        for tag in stuff[3:]:
            if "." in tag:
                break
        tag = tag.strip("(").strip(")").strip(",")
        version = StrictVersion(tag)
        if version > next_oldest:
            if options.verbose: print("found %s" % (version))
            block = getChangeLogBlock(version, next_oldest, day, options)
            blocks[0:0] = "\n".join(block) + "\n"
            next_oldest = version
    version = "HEAD"
    day = date.today().strftime("%Y-%m-%d")
    block = getChangeLogBlock(version, next_oldest, day, options)
    print("\n".join(block) + "\n")
    
    if not options.dry_run:
        with open(options.outputfile, "w") as fh:
            for block in blocks:
                fh.write(block)

if __name__=='__main__':
    usage="usage: %prog [-m module] [-o file] [-n variablename file] [-t template] [files...]"
    parser=OptionParser(usage=usage)
    parser.add_option("-v", "--verbose", action="store_true", help="print debugging info")
    parser.add_option("--dry-run", action="store_true", help="don't actually change anything")
    parser.add_option("--version", action="store_true", help="display current version and exit")
    parser.add_option("--next-version", action="store_true", help="display what would be the next version and exit")
    parser.add_option("--rebuild", action="store_true", help="rebuild the entire ChangeLog")
    parser.add_option("-o", action="store", dest="outputfile", help="output filename", default="ChangeLog")
    (options, args) = parser.parse_args()

    tagged_version = findLatestInGit(options)
    if options.verbose:
        print("latest tagged in git: %s" % tagged_version)
    if options.version:
        print(tagged_version)
        sys.exit()
    if options.next_version:
        print(next_version(tagged_version))
        sys.exit()
    if options.rebuild:
        rebuild(options)
        sys.exit()
    
    version, latest_date, versions = findLatestChangeLogVersion(options)
    print("latest from changelog: %s" % version)
    print("all from changelog: %s" % str(versions))

    import importlib
    module = importlib.import_module("omnivore._omnivore_version")
    print(module)
    print("module version: %s" % module.version)
    
    v_changelog = StrictVersion(version)
    print(v_changelog)
    v_module = StrictVersion(module.version)
    print(v_module)
    v_tagged = StrictVersion(tagged_version)
    print(v_tagged)
    
    if v_module > v_changelog:
        print("adding to ChangeLog!")
        block = getChangeLogBlock(tagged_version, module.version, options)
        if not options.dry_run:
            prepend(options.outputfile, block)
    elif v_module == v_changelog and v_module > v_tagged:
        print("replacing ChangeLog entry!")
        block = getChangeLogBlock(tagged_version, module.version, options)
        if not options.dry_run:
            replace(options.outputfile, block)
    else:
            print("unhandled version differences...")
