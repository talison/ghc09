import logging
import os.path
import pickle
import simplejson as json

logger = logging.getLogger("ghc.util")

def load_pickle(path):
    """
    Loads a pickled object
    """
    if not os.path.exists(path):
        return None

    logger.debug("Loading pickle file {0}".format(path))

    return pickle.load(open(path))

def store_pickle(obj, path, debug=False, overwrite=False):
    """
    Stores the watches hash to a pickled file.
    If debug is true, also generates a readable
    JSON text file.
    """
    
    if not os.path.isdir(os.path.dirname(path)):
        raise IOError("Directory {0} does not exist".format(os.path.dirname(path)))
    
    if os.path.exists(path) and not overwrite:
        return
    
    logger.debug("Dumping pickle {0}".format(path))
    
    pickle.dump(obj, open(path, "w"))

    logger.debug("Finished dumping pickle {0}".format(path))
    
    if debug:
        json_file = open("{0}.json".format(path), "w")
        logger.debug("Dumping json file {0}".format(json_file.name))
        json.dump(obj, json_file, default=_json_convert, sort_keys=True, indent=2)
        logger.debug("Finished dumping json file {0}".format(json_file.name))
        json_file.close()

def _json_convert(set_):
    """
    Converts a set to a list for JSON dumps
    """
    if isinstance(set_, set):
        return list(set_)
    else:
        raise TypeError("Not a set")

def write_candidates(candidates, out_path, n):
    out = open(out_path, "w")

    try:
        logger.debug("Writing results to {0}".format(out.name))
        for k in sorted(candidates.keys()):
            out.write("{0}:{1}\n".format(k, ",".join(map(str, candidates[k][:n]))))

    finally:
        out.close()
        logger.debug("Wrote {0}".format(out.name))
    
def read_candidates(in_path):
    candidates = dict()
    logger.debug("Reading candidates from {0}".format(in_path))
    for line in open(in_path, 'r'):
        user, repos = line.rstrip().split(':')
        if not repos:
            candidates[int(user)] = []
            continue

        candidates[int(user)] = [int(r) for r in repos.split(',')]

    return candidates
