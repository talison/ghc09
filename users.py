from __future__ import division
import collections
import config
import logging
import os.path
import util

logger = logging.getLogger("ghc.users")

class User:
    def __init__(self, id):
        self.id = int(id)
        self.repos = set()
        self.languages = []

    def __eq__(self, other):
        return self.id == other.id

    def __str__(self):
        return "({0.id})".format(self)

    def __repr__(self):
        return "User({0.id})".format(self)

    def __lt__(self, other):
        return self.id < other.id

    def __gt__(self, other):
        return self.id > other.id

    def __hash__(self):
        return self.id

    def to_json(self):
        # Use the underscore on certain attributes
        # to force more desirable ordering.
        return json.dumps({
                '_id': self.id, 
                '_repos': self.repos, 
                '__languages': self.languages, 
                }, sort_keys=True, indent=2)

_user_watches = None
_repo_freqs = None
_test_ids = None

def get_user_watches():
    """
    Returns an dict of user id keys mapped to a set
    of repo ids being watched by that user
    """
    path = os.path.join(config.CALC_DATA_PATH, 'user_watches.pickle')
    global _user_watches
    user_watches = _user_watches or util.load_pickle(path)
    if user_watches:
        _user_watches = user_watches
        return user_watches
    
    user_watches = collections.defaultdict(set)
    
    for line in open(os.path.join(config.SRC_DATA_PATH, 'data.txt')):
        k,v = line.rstrip().split(':')
        user_watches[int(k)].add(int(v))

    util.store_pickle(user_watches, path, debug=True)
    _user_watches = user_watches

    return user_watches

def get_repo_frequencies():
    """
    Returns a map of repo id to (frequency, relative_freq) tuples.
    """
    path = os.path.join(config.CALC_DATA_PATH, 'repo_frequencies1.pickle')
    global _repo_freqs
    repo_frequencies = _repo_freqs or util.load_pickle(path)
    if repo_frequencies:
        _repo_freqs = repo_frequencies
        return repo_frequencies

    user_watches = get_user_watches()

    total_watches = sum(len(w) for w in user_watches.values())
    logger.debug("Total watches is {0}".format(total_watches))
    
    repo_frequencies = dict()
    for repos in user_watches.values():
        for watch in repos:
            if not watch in repo_frequencies:
                repo_frequencies[watch] = (1, 1/total_watches)
            else:
                freq = repo_frequencies[watch][0] + 1
                repo_frequencies[watch] = (freq, freq/total_watches)


    util.store_pickle(repo_frequencies, path, debug=True)
    _repo_freqs = repo_frequencies

    return repo_frequencies

def get_test_user_ids():
    """
    Gets the user ids to guess repos for.
    """
    global _test_ids
    _test_ids = _test_ids or [int(line.rstrip()) for line in open(os.path.join(config.SRC_DATA_PATH, "test.txt"))]
    return _test_ids

