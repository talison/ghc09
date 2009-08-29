#!/usr/bin/env python

from __future__ import division
import analyzers
import collections
import config
import logging
import os.path
import tokyo
import util

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s',
                    filename=os.path.join(config.LOG_PATH, 'log.txt'),
                    filemode='w')
logger = logging.getLogger('ghc')


analysis = analyzers.Analysis()

base_probabilistic_candidates = 'results-prob-20.txt'
filled_candidates = 'results-filled-20.txt'

candidates = None

if not tokyo.database_exists():
    tokyo.compute_conditional_probabilities()

if not os.path.exists(base_probabilistic_candidates):
    logger.debug("Could not find {0}, computing...".format(base_probabilistic_candidates))
    candidates = analysis.get_probabilistic_candidates(20)
    util.write_candidates(candidates, base_probabilistic_candidates, 20)

if not os.path.exists(filled_candidates):
    candidates = util.read_candidates(base_probabilistic_candidates)
    analysis.fill_candidates(candidates, 20)
    util.write_candidates(candidates, filled_candidates, 20)

# At this point, run 'blend_unwatched_sources.rb > results-filled-20.txt'


