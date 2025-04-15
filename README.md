# universal-public-genome

## Motivation
DBCLS has been collaborating with various domestic and international researchers to study machine-processable methods for genome location information, such as participating in the proposal of Feature Annotation Location Description Ontology (FALDO), which uses RDF to represent the location and extent of genomes. information. In a situation where a large amount of genome-related information is expected to continue to be made public in the future, location information needs to be distributed unambiguously in various databases, applications, and literature, and a concise and easy-to-share method of expressing genome location information is required. On the other hand, various notations for location information, such as INSDC, GFF/GVF/GTF, and VCF, are in circulation, causing interoperability problems among genomic data written in different notations.
To address this problem, we develop a tool to convert these different notations into an integrated notation with assembly identifiers, and to express them as URLs for efficient distribution on the Web. The unified notation shall include Assembly, Sequence, and Location.


## Command Line Interface

$ python main.py -h
```
usage: main.py [-h] [-i [INPUT]] [--context-url CONTEXT_URL] [--id-base-url ID_BASE_URL]

INSDC ID ⇔ FALDO JSON-LD Converter

options:
  -h, --help            show this help message and exit
  -i, --input [INPUT]   ID or FALDO JSON-LD to be converted
  --context-url CONTEXT_URL
                        URL of context
  --id-base-url ID_BASE_URL
                        Base URL for ID
```

## Examples

$ python main.py -i 'GCA000000000-J00000:467'
```
{
  "@context": "http://example.org/context/faldo.jsonld",
  "id": "http://example.org/GCA000000000-J00000-467",
  "location": {
    "type": "ExactPosition",
    "position": 467,
    "reference": "insdc:J00000"
  }
}
```


$ python main.py -i '{
  "@context": "http://example.org/context/faldo.jsonld",
  "id": "http://example.org/GCA000000000-J00000-467",
  "location": {
    "type": "ExactPosition",
    "position": 467,
    "reference": "insdc:J00000"
  }
}'
```
GCA000000000-J00000:467
```

$ echo 'GCA000000000-J00000:467' | python main.py
```
{
  "@context": "http://example.org/context/faldo.jsonld",
  "id": "http://example.org/GCA000000000-J00000-467",
  "location": {
    "type": "ExactPosition",
    "position": 467,
    "reference": "insdc:J00000"
  }
}
```

$ cat sample.json | python main.py
```
GCA000000000-J00000:467
```