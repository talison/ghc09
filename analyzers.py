from __future__ import division
import collections
import config
import logging
import math
import operator
import os.path
import re
import repos
import tokyo
import users
import util

logger = logging.getLogger("ghc.analyzers")

class Analysis:
    def __init__(self):
        self.user_watches = users.get_user_watches()
        self.repo_freqs = users.get_repo_frequencies()
        self.repos = repos.get_repos()
        self.test_users = users.get_test_user_ids()


    def get_probabilistic_candidates(self, n=10):
        """
        Gets the top n candidate repos for users in the
        test file.
        """
        candidates = collections.defaultdict(list)

        db = tokyo.Reader()

        try:
            for user in self.test_users:
                logger.debug("Getting top {0} for user {1}".format(n, user))
                self._fill_probabilistic(db, candidates[user], self.user_watches[user], n)
                logger.debug("Gathered {0} candidates for user {1}".format(len(candidates[user]), user))

        finally:
            db.close()

        return candidates


    def fill_candidates(self, candidates, n=10):
        
        db = tokyo.Reader()
        top_repos = sorted([r[0] for r in self.repo_freqs.values()], reverse=True)

        try:
            for user, suggestions in candidates.iteritems():
                
                # Add ancestors and descendents
                if len(suggestions) < n:
                    logger.debug("Filling candidates for user {0} with {1} candidates".format(user, len(suggestions)))

                    relatives = set()
                    for w in self.user_watches[user]:
                        relatives.update(map(operator.attrgetter('id'), self.repos[w].ancestors) + 
                                         map(operator.attrgetter('id'), self.repos[w].descendents))


                    logger.debug("Found {0} relatives".format(len(relatives)))

                    for r in sorted(relatives, 
                                    cmp=lambda x,y: cmp(self.repo_freqs[x],
                                                        self.repo_freqs[y]), reverse=True):
                        if not r in suggestions:
                            logger.debug("Adding relative {0}".format(r))
                            suggestions.append(r)
                            if len(suggestions) == n:
                                break

                if len(suggestions) < n:
                    # Fill with probabilistic candidates based on relatives
                    # and current watches (which may have been modified)
                    relatives.update(suggestions)

                    logger.debug("Looking for candidates for {0} relatives".format(len(relatives)))

                    self._fill_probabilistic(db, suggestions, relatives, n)

                if len(suggestions) < n:
                    logger.debug("Looking for similarly named repos")

                    # Look for similarly named repos
                    similar = self._find_similarly_named(self.user_watches[user])

                    logger.debug("Adding {0} similarly named items".format(len(similar)))

                    suggestions.extend(similar[:n - len(suggestions)])

                if len(suggestions) < n:
                    if len(similar) > 0:
                        self._fill_probabilistic(db, suggestions, similar, n)

                if len(suggestions) < n:
                    logger.debug("Filling {0} slots with top repos".format(n - len(suggestions)))

                    suggestions.extend(top_repos[:n - len(suggestions)])
        finally:
            db.close()


    def _fill_probabilistic(self, db, candidates, src_repos, n):
        related_repos = db.get_related_repos(src_repos)

        self._sort_related_repos(related_repos)

        while len(candidates) < n and len(related_repos) > 0:
            candidate = related_repos.pop()
            if candidate[1] not in candidates:
                logger.debug("Adding {0}".format(candidate))
                candidates.append(candidate[1])

    def _sort_related_repos(self, related_repos):
        weight = .15
        def sort_(x,y):
            return cmp((1 + weight * math.log(x[2])) * x[3],
                       (1 + weight * math.log(y[2])) * y[3])
        related_repos.sort(cmp=sort_)

    def _find_similarly_named(self, repo_ids):
        repo_names = set([self.repos[rid].name for rid in repo_ids])
        tokens = '|'.join(set(sum([re.findall('[a-z]+', name, re.I) for name in repo_names], [])))
        similar = sorted([repo.id for repo in self.repos.values() if re.search(tokens, repo.name, re.I)],
                         cmp=lambda x,y: cmp(self.repo_freqs[x], self.repo_freqs[y]), reverse=True)
        return list(set(similar) - set(repo_ids))
