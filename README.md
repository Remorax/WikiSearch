# Wikipedia Search Engine

A mini search engine that indexes Wikipedia and answers search queries. An inverted index is constructed after parsing the Wikipedia dump, tokenizing, stemming and storing the count of each word in each document. This index is compressed using various compression techniques. The compressed inverted index is used to answer user queries and the articles with the maximum hits are retreived.

## Index

To index, run `python3 index.py <name_of_wiki_dump>`

## Search

- Run `python3 search.py`
- Enter your query at the prompt
