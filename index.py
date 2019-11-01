import xml.sax, re, time, psutil, heapq, sys, os, shlex
from nltk.corpus import stopwords 
from nltk import tokenize
from nltk.stem.porter import *
from itertools import chain
from collections import Counter, OrderedDict
from subprocess import Popen, PIPE


# Stage 1: XML Parsing

stop_words = set(stopwords.words('english'))
stemmer = PorterStemmer()

def isEnglish(s):
    try:
        s.encode(encoding='utf-8').decode('ascii')
    except UnicodeDecodeError:
        return False
    else:
        return True
    
def DecimalChecker(s):
    try:
        s = float(s)
        decimal = str(s - int(s))[2:]
        return len(decimal) < 3
    except:
        return True

compiledpattern = re.compile("^\W+|\W+$")

    
def multiple_replace(replaceDict, text):
    regex = re.compile("(%s)" % "|".join(map(re.escape, replaceDict.keys())))
    return regex.sub(lambda mo: replaceDict[mo.string[mo.start():mo.end()]], text) 

def convertToWords(string):
    tokens = re.split(" |\,|\-|\_|\/|\:|\+|=|\|\.|\#|\{|\}", string.lower())
    tokens = [compiledpattern.sub('', token) for token in tokens if len(token)<10]
    newTokens = [token for token in tokens if re.search("^\d{4}$|^[a-zA-Z]+$", token) and isEnglish(token)]
    filteredTokens = list(set(newTokens) - set(stop_words))
    stemmedTokens = [stemmer.stem(token) for token in filteredTokens]
    return Counter(stemmedTokens)
        
class AbstractHandler(xml.sax.handler.ContentHandler):
    def __init__(self):
        xml.sax.handler.ContentHandler.__init__(self)
        self._title = []
        self._text = []
        self._data = {}
        self._extracts = []
        self._extractsFile = open("extracts", "w+")
        self._id = ""
        self._foundID = False
        self._curr = ''
        self.doccnt = 0

    def characters(self, content):
        if self._curr == 'text':
            self._text.append(content)
        elif self._curr == 'title':
            self._title.append(content)
        elif self._curr == 'id' and not self._foundID:
            self._id = content

    def startElement(self, name, attrs):
        self._curr = name

    def endElement(self, name):
        if name == 'title':
            title = ' '.join(self._title)
            self._data[name] = convertToWords(title)
            self._data["unbrokenTitle"] = title
        elif name == 'text':
            text = ' '.join(self._text)
            self._data["categories"] = convertToWords(" ".join(re.findall("\[\[Category:(.*)\]\]",text)))
            try:
                tempInfobox = re.search("{{Infobox[\w\W]*}}",text).group()
                pos = 0
                for (idx,char) in enumerate(tempInfobox):
                    if char == "{":
                        pos += 1
                    elif char == "}":
                        pos -= 1
                    if pos == 0:
                        break
                infobox = []
                for elem in tempInfobox[:idx][:-1].split("|")[1:]:
                    if "=" not in elem or not "".join(elem.split("=")[1:]).strip():
                        continue
                    for line in multiple_replace({"=": "", "{{": ""}, elem).split("\n"):
                        if line:
                            if "[" not in line:
                                infobox.append(line.strip())
                            else:
                                app = " ".join(re.findall("\[\[(.*?)\]\]",line.strip())).strip()
                                if app:
                                    infobox.append(app)
                self._data["infobox"] = convertToWords(" ".join([el for el in infobox if el]))
            except:
                pass
            
            try:
                tempRef = re.findall("{{Cite([\w\W]*?)}}",text, re.I)
                references = []
                for datum in tempRef:
                    for elem in datum.split("|"):
                        if "http" not in elem:
                            references.append(multiple_replace({"[":"", "]":""},elem).strip())
                self._data["references"] = convertToWords(" ".join(references))
            except:
                pass
            
            self._data["body_text"] = convertToWords(text)
        elif name == "id" and not self._foundID:
            self._foundID = True
            self._data["id"] = self.doccnt
            self.doccnt += 1

        if name == 'page':
            self._curr = name
            self._title = []
            self._text = []
            self._id = ""
            self._foundID = False
            self._extracts.append(self._data.copy())
            if (psutil.virtual_memory().available < 100) or (int(self._data["id"]) % 10000 == 0):    
                self._extractsFile.write("\n".join([", ".join([el.strip() for el in str(extract).split(",")]) for extract in self._extracts]))
                self._extractsFile.write("\n")
                self._extracts = []
            self._data = {}


handler = AbstractHandler()
parser = xml.sax.make_parser()
parser.setContentHandler(handler)

dump = sys.argv[1]

data = open(dump, "r", encoding="utf8")
for line in data:
    try:
        parser.feed(line)
    except:
        handler._extractsFile.write("\n".join([", ".join([el.strip() for el in str(extract).split(",")]) for extract in handler._extracts]))
        handler._extractsFile.write("\n")
handler._extractsFile.write("\n".join([", ".join([el.strip() for el in str(extract).split(",")]) for extract in handler._extracts]))

# Stage 2: Creating unsorted vocabulary with duplicates

file = open("listofwords", "w+")
extractsFile = open("extracts", "r")
setofwords = []
i = 0
with open("extracts", "r") as f:
    for line in f:
        datum = eval(line)
        for key in datum:
            if key!="id" and key!="unbrokenTitle":
                file.write("\n".join(list(datum[key].keys())))
file.close()

# Stage 3: Creating unique (unsorted) list of words
fobj = open("uniqwords", "w+")
Popen(shlex.split("awk '!x[$0]++' listofwords"), stdout=fobj, shell=True)

p = Popen(shlex.split("wc -l uniqwords"), stdout=PIPE)
lines = p.communicate()[0].decode("utf-8").strip().split()[0]

# Stage 4: SPIMI (Single Pass In-Memory Indexing)

titles = open("titles", "w+")
N = 20
numLines = int(lines/N)

i = 0
j = 0
wordsSet = []
with open("uniqwords", "r") as f:
    for word in f:
        word = word.strip()
        if i == numLines:
            # Takes block of length numLines

            wordsSet = sorted(wordsSet)
            i=0
            approach1Dict = OrderedDict({word: {} for word in wordsSet})
            with open("extracts", "r") as f1:
                k=0
                for line in f1:
                    datum = eval(line)
                    if j==0:
                        if k!=0:
                            titles.write("\n")
                        titles.write(firstline["unbrokenTitle"])
                    for key in datum:
                        if key!="id" and key!="unbrokenTitle":
                            for word in datum[key]:
                                try:
                                    if datum["id"] in approach1Dict[word]:
                                        try:
                                            approach1Dict[word][datum["id"]][key] += datum[key][word]
                                        except:
                                            approach1Dict[word][datum["id"]][key] = datum[key][word]
                                    else:
                                        approach1Dict[word][datum["id"]] = {key: datum[key][word]}
                                except:
                                    continue
                    k+=1

            # Writes block to disk
            open("temp" + str(j), "w+").write("\n".join([str(el) for el in approach1Dict.items()]))
            j+=1
            wordsSet = []
        else:
            i+=1
            wordsSet.append(word)


filenames = ["temp" + str(i) for i in range(j)]
files = map(open, filenames)
outfile = open('approach1Dict', "w+")
sortedWords = open('wordsList', "w+")

# Merge blocks and write to final file "approach1Dict"
# Writes the keys to wordsList: contains sorted unique words
for line in heapq.merge(*files, key=lambda r: eval(r)[0]):
    outfile.write(line)
    sortedWords.write(eval(line)[0])


# Stage 5: Compression by indexing word using word number

sortedWords = open("wordsList", "r").read().split("\n")
wordsLen = 5*len(sortedWords)
invertedIndex = [{} for i in range(wordsLen)]
attribs = ["infobox", "title", "categories", "body_text", "references"]
i = 0
k = 0
with open("approach1Dict","r") as f:
    for line in f:
        parsed = eval(line)
        wordoccurences = approach1Dict[parsed[0]]
        idx = 5 * i
        for document in wordoccurences:
            for attrib in wordoccurences[document]:
                j = attribs.index(attrib)
                if document in invertedIndex[idx + j]:
                    invertedIndex[idx + j][document] += wordoccurences[document][attrib]
                else:
                    invertedIndex[idx + j][document] = wordoccurences[document][attrib]
        i+=1
    if psutil.virtual_memory().available < 100:
        currentFile = open("idx" + str(k), "w+").write("\n".join(invertedIndex))
        k+=1
        invertedIndex = [{} for i in range(wordsLen)]


fileObjs = [open("idx" + str(k),"r") for k in range(k)]
op = open("invertedIndex1", "w+")
for i in range(wordsLen):
    allCounters = [Counter(eval(f.readline())) for f in fileObjs]
    op.write(str(sum(allCounters,Counter())))
    if i!=(wordsLen-1):
        op.write("\n")
op.close()

# Stage 6: Compression by removing dict format and storing as list of lists of decreasing frequency

op = open("invertedIndex", "w+")
compressedIndex1 = []

p = Popen(shlex.split("wc -l invertedIndex1"), stdout=PIPE)
lines = p.communicate()[0].decode("utf-8").strip().split()[0]

i=0
with open("invertedIndex1","r") as f:
    for elem in f:
        currWordPos = []
        allVals = sorted(list(set(elem.values())), reverse=True)
        for n in allVals:
            currElem = [n]
            currElem.extend([k for k in elem.keys() if elem[k] == n])
            currWordPos.append(currElem)
        compressedIndex1.append(currWordPos)
        if psutil.virtual_memory().available < 100:
            op.write(str("\n".join(compressedIndex1)))
            if i!=(lines-1):
                op.write("\n")
            compressedIndex1 = []
        i += 1
         