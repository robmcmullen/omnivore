#!/usr/bin/env python

from omnivore.utils.archutil import Labels

import logging
log = logging.getLogger(__name__)


if __name__ == "__main__":
    filename = "./omnivore/templates/atari800.labels"
    text = open(filename).read()
    labels1 = Labels.from_text(text)
    print(str(labels1))
    labels1.labels.print_all()
    filename = "./omnivore/templates/atari_basic.labels"
    text = open(filename).read()
    labels2 = Labels.from_text(text)
    print(str(labels2))
    labels1.labels.print_all()
    labels2.labels.print_all()
    labels1.update(labels2)
    labels1.labels.print_all()
    labels2.labels.print_all()
    filename = "./omnivore/templates/atari5200.labels"
    text = open(filename).read()
    labels2 = Labels.from_text(text)
    labels1.update(labels2)
    print(str(labels1))
