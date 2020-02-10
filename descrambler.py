import nltk
from nltk import corpus
from itertools import permutations
import random
import re
from multiprocessing import Process
import math

# nltk.download('words')


def find_match():
    check1 = re.compile("^[^aeiou ]{0,3}(([aeiouy]{1,2}[^aeiou ]{1,3})* ?)*[aeiouy]{0,2} *$")
    check2 = re.compile("^([^ ]{2,} ?)+ *$")
    origin = list("polydegmon purgation")
    # print(check1.match("".join(origin)))
    # print(check2.match("".join(origin)))
    random.shuffle(origin)
    perms = permutations(origin)
    print(math.factorial(len(origin)))

    for permutation in perms:
        perm = "".join(permutation)
        if check1.match(perm) and check2.match(perm):
            words = perm.split(" ")
            for word in words:
                if word in corpus.words.words():
                    print("".join(perm))
                    break


if __name__ == '__main__':
    for i in range(12):
        p = Process(target=find_match)
        p.start()
