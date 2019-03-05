#!/usr/bin/env python
import os

from omnivore.utils.archutil import Labels, load_memory_map

from sawx.templates import template_subdirs
template_subdirs.append(os.path.abspath("./omnivore/templates"))

import logging
log = logging.getLogger(__name__)


if __name__ == "__main__":
    filename = "./omnivore/templates/atari800.labels"
    labels1 = Labels.from_file(filename)
    print(str(labels1))
    labels1.labels.print_all()
    filename = "./omnivore/templates/atari_basic.labels"
    labels2 = Labels.from_file(filename)
    print(str(labels2))
    labels1.labels.print_all()
    labels2.labels.print_all()
    labels1.update(labels2)
    labels1.labels.print_all()
    labels2.labels.print_all()
    labels2 = load_memory_map("atari5200")
    labels1.update(labels2)
    print(str(labels1))
    print(str(labels2))
