from __future__ import division
from datetime import datetime
import config
import logging
import os
import pickle
import re
import simplejson as json

logger = logging.getLogger("ghc.repos")

class Repo:
    def __init__(self, id, user, name, date, fork=None):
        self.id = int(id)
        self.user = user
        self.name = name
        self.created = datetime.strptime(date, '%Y-%m-%d').date()
        self.fork = int(fork) if fork != None else None
        # References to Repo objects that this is a direct
        # or indirect fork of.
        self.ancestors = []
        # References to Repo objects that directly or indirectly
        # fork this project
        self.descendants = []
        # An array of tuples that contains (language, raw lines, %lines)
        self.languages =[]

    def __eq__(self, other):
        return self.id == other.id

    def __str__(self):
        return "({0.id}, '{0.user}', '{0.name}', '{1}', {0.fork})".format(self, self.created.strftime('%Y-%m-%d'))

    def __repr__(self):
        return "Repo({0.id}, '{0.user}', '{0.name}', '{1}', {0.fork})".format(self, self.created.strftime('%Y-%m-%d'))

    def is_forked(self):
        return self.fork != None

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
                '__user': self.user, 
                '__name': self.name, 
                '__created': self.created.strftime('%Y-%m-%d'), 
                '_fork': self.fork,
                'ancestors': [ancestor.id for ancestor in self.ancestors],
                'descendants': [descendant.id for descendant in self.descendants],
                'languages' : self.languages
                }, sort_keys=True, indent=2)

def get_repos():
    """
    Pull the data out of repos.txt into Repo objects.
    Hashes them by repo id
    """
    repos = _load_repos()

    if repos:
        return repos
    
    logger.debug("Building repos")

    repos = {}

    for line in open(os.path.join(config.SRC_DATA_PATH, 'repos.txt')):
        repo = _read_repo(line)
        repos[repo.id] = repo
    _set_lineage(repos)
    _set_languages(repos)

    _store_repos(repos, debug=True)
    
    return repos
        
def _get_ancestry_cmp(repo_map):
    """
    Sort by created at. Time resolution is
    not in milliseconds and there are frequent
    ties. Use repo id as a tiebreaker.

    This method must ensure that ancestors
    show up before their dependents. There are
    cases where this is tricky, such as a repo
    forked from another repo that was itself
    forked, and all this happened on the same
    day. In that case, use the parent repos
    as the parameters and recurse until a
    definitive tie-breaking condition is found.
    """
    def repo_sort(x,y):
        ret = cmp(x.created, y.created)
        if ret != 0: return ret
        if not x.is_forked() and y.is_forked(): return -1
        if x.is_forked() and not y.is_forked(): return 1
        if x.is_forked() and y.is_forked(): return repo_sort(repo_map[x.fork], repo_map[y.fork])
        return cmp(x.id, y.id)

    return repo_sort

def _read_repo(line):
    """
    Given a line in repos.txt, create a basic Repo object.
    """
    tmp = line.rstrip().split(',')
    id, meta = tmp[0].split(':')
    user, name = meta.split('/')
    fork = tmp[2] if len(tmp) == 3 else None
    return Repo(id, user, name, tmp[1], fork)

def _set_lineage(repos):
    """
    Build the lineage data between repos
    """

    # The timestamps do not have a high enough resolution
    # for true sorting. This sorting algorithm will put
    # the repos in order by date, with the guarantee
    # that a given repo always comes after the repo
    # it was forked from.
    #
    # Note that the data from github contained a few
    # anomalies where the forked repo had a timestamp
    # that was later than it's child. The assert
    # statement later in this method catches these
    # cases. They were fixed by hand.
    sorted_repos = sorted(repos.values(), cmp=_get_ancestry_cmp(repos))
    
    for repo in sorted_repos:
        if repo.is_forked():

            forked = repos[repo.fork]

            repo.ancestors.append(forked)

            forked.descendants.append(repo)

            # Use a local function to recurse through each
            # ancestor
            def update_ancestry_chain(r, f):
                assert len(f.ancestors) > 0, "Forked project {0} from {1} has no ancestors".format(f, r)
                # Add the current project as a descendant of it's ancestors
                # Add each project as an ancestor of the current project
                for ancestor in f.ancestors:
                    if not ancestor in r.ancestors: 
                        r.ancestors.append(ancestor) 

                    if not r in ancestor.descendants: 
                        ancestor.descendants.append(r)

                    # Recurse
                    if ancestor.is_forked(): 
                        update_ancestry_chain(r, ancestor)

            if forked.is_forked(): 
                update_ancestry_chain(repo, forked)

def _set_languages(repos):
    """
    Given a map of repo.id -> repo, add the language data in
    the lang.txt file.
    """
    for line in open(os.path.join(config.SRC_DATA_PATH, 'lang.txt')):
        repo_id,languages = line.split(':')
        total_lines = sum([int(count) for count in re.findall(r';(\d+),?', languages)])

        if total_lines == 0: continue

        if int(repo_id) not in repos:
            logger.debug("Could not find repo {0} while setting lang".format(repo_id))
            continue

        repo = repos[int(repo_id)]

        for pair in languages.split(','):
            lang,lines = pair.split(';')
            repo.languages.append((lang, int(lines), int(lines)/total_lines))



def _store_repos(repo_map, debug=False, overwrite=False):
    """
    Stores the repos hash to a pickled file.
    If debug is true, als generates a readable
    JSON text file.
    """
    path = os.path.join(config.CALC_DATA_PATH, 'repos.pickle')

    if os.path.exists(path) and not overwrite:
        return
    
    logger.debug("Dumping pickle file {0}".format(path))

    pickle.dump(repo_map, open(path, "w"))

    logger.debug("Dumped pickle file {0}".format(path))

    
    if debug:
        json_file = open(os.path.join(config.CALC_DATA_PATH, 'repos.json'), "w")
        logger.debug("Dumping json file {0}".format(json_file.name))
        for repo in sorted(repo_map.values(), key=lambda x: x.id):
            json_file.write("{0}\n".format(repo.to_json()))
        logger.debug("Dumped json file {0}".format(json_file.name))
        json_file.close()

def _load_repos():
    """
    Loads a dict of repos from a pickled file.
    """
    path = os.path.join(config.CALC_DATA_PATH, 'repos.pickle')
    if not os.path.exists(path):
        return None

    logger.debug("Loading pickle file {0}".format(path))

    return pickle.load(open(path))
