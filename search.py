import sys, operator
from collections import Counter
from nltk.corpus import stopwords 
from nltk import tokenize
from nltk.stem.porter import *

invertedIndex = eval(open("invertedIndex").read())
wordsList =eval( open("wordsList").read())
titles = eval(open("titles").read())
stop_words = set(stopwords.words('english'))

while True:
    query = input("Enter your query here: ")
    query = query.strip()
    queryWords = query.split(" ")
    currElem = Counter()
    stemmer = PorterStemmer()
    for word in queryWords:
        word = word.lower()
        word = stemmer.stem(word)
        category = "all"
        if ":" in word:
            split = word.split(":")
            category = split[0]
            word = split[1]
        if word in stop_words:
            continue

        idx = bisect_left(wordsList, word)
        if idx == len(wordsList):
            continue
        if category!="all":
            categoryDict = {"infobox": 0, "title": 1, "category": 2, "body": 3,  "ref": 4}
            categoryNum = categoryDict[category]
            tempElem = invertedIndex[5 * idx + categoryNum]
            for sameCountDocuments in tempElem:
                count = sameCountDocuments[0]
                currElem += Counter({doc: count for doc in sameCountDocuments[1:]})
        else:
            for j in range(5):
                tempElem = invertedIndex[5 * idx + j]
                for sameCountDocuments in tempElem:
                    count = sameCountDocuments[0]
                    currElem += Counter({doc: count for doc in sameCountDocuments[1:]})

    results = [titles[x] for (x,y) in sorted(currElem.items(), key=operator.itemgetter(1), reverse=True) if ":" not in titles[x]][:10]
    print (results)
