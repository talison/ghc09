import collections
import config
import logging
import os.path
import pytc
import users

logger = logging.getLogger("ghc.tokyo")

def database_exists():
    return os.path.exists(os.path.join(config.CALC_DATA_PATH, 'cprob.tch'))

def compute_conditional_probabilities():
    logger.debug("Computing conditional probabilities.")

    user_watches = users.get_user_watches()
    repo_frequencies = users.get_repo_frequencies()

    # Prune watchlists to only those w/ greater than 1 watch
    watches_list = [w for w in user_watches.values() if len(w) > 1]
    watches_size = len(watches_list)
    
    logger.debug("Watches size {0}".format(watches_size))

    cprob = collections.defaultdict(dict)

    count = 0
    for watches in watches_list:
        count += 1
        logger.debug("Processing watch {0} of {1}".format(count, watches_size))
        
        for i in watches:
            for j in watches:
                if i == j: continue

                if not j in cprob[i]:
                    cprob[i][j] = 1, 1/repo_frequencies[i]
                else:
                    cofreq = cprob[i][j][0] + 1
                    cprob[i][j] = cofreq, cofreq/repo_frequencies[i]

    persist_conditional_probabilities(cprob)


def persist_conditional_probabilities(cprobs):
    """
    Persists a conditional probability object to Tokyo Cabinet.
    Keys are in the for 'i,j' and values are in the form of
    'freq,prob' where 'freq' is the # of times j was seen with
    i and 'prob' is the percentage of time j occurs with i.
    """
    epsilon = 0.001
    db_path = os.path.join(config.CALC_DATA_PATH, 'cprob.tch')
    db = pytc.BDB()
    db.open(db_path, pytc.BDBOWRITER | pytc.BDBOCREAT)

    logger.debug("Persisting probabilities to {0}".format(db_path))
    
    try:
        for i in cprobs:
            for j in cprobs[i]:
                if i == j:
                    continue

                cfreq, cprob = cprobs[i][j]

                if cmp(cprob, epsilon) < 0:
                    continue

                db.put("{0},{1}".format(i,j), 
                       "{0},{1:.4f}".format(cfreq, cprob))
            
    finally:
        db.close()
        logger.debug("Wrote probabilities to {0}".format(db_path))


class Reader:
    def __init__(self):
        self.db = pytc.BDB()
        self.db.open(os.path.join(config.CALC_DATA_PATH, 'cprob.tch'),
                     pytc.BDBOREADER)


    def get_related_repos(self, user_watches):
        """
        Returns a dict where the keys are the watched repos,
        and the values are a list of tuples:
        (watch, related_repo_id, cofrequency, conditional_probability)
        """
        related_repos = list()

        logger.debug("Retrieving related repos for {0} watches".format(len(user_watches)))

        for watch in user_watches:
            for pair in self.db.rangefwm("{0},".format(watch), 1000000):
                related = int(pair.split(',')[1])
                # Don't add any repos already being watched
                if related in user_watches:
                    continue
                cofreq, cprob = self.db.get(pair).split(',')
                related_repos.append((watch, related, int(cofreq), float(cprob)))

        logger.debug("Retrieved {0} related repos".format(len(related_repos)))
        return related_repos
                
            
    def close(self):
        self.db.close()
        
