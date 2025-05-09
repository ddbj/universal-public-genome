# universal-public-genome

## Motivation
DBCLS has been collaborating with various domestic and international researchers to study machine-processable methods for genome location information, such as participating in the proposal of Feature Annotation Location Description Ontology (FALDO), which uses RDF to represent the location and extent of genomes. information. In a situation where a large amount of genome-related information is expected to continue to be made public in the future, location information needs to be distributed unambiguously in various databases, applications, and literature, and a concise and easy-to-share method of expressing genome location information is required. On the other hand, various notations for location information, such as INSDC, GFF/GVF/GTF, and VCF, are in circulation, causing interoperability problems among genomic data written in different notations.
To address this problem, we develop a tool to convert these different notations into an integrated notation with assembly identifiers, and to express them as URLs for efficient distribution on the Web. The unified notation shall include Assembly, Sequence, and Location.


## Command Line Interface

```
$ python main.py -h
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

### Conversion from ID to FALDO JSON-LD

Simple input:
```bash
$ python main.py -i 'GCA000000000-J00000:467'
```

Expected output:
```json
{
  "@context": "http://example.org/context/faldo.jsonld",
  "id": "http://example.org/GCA000000000-J00000:467",
  "location": {
    "type": "ExactPosition",
    "position": 467,
    "reference": "insdc:J00000"
  }
}
```

Specify the context URL and the base URL of the ID, and pass the ID as standard input. Output the result to a file:
```bash
$ echo 'GCA000000000-J00000:join(complement(4918..5163),complement(2691..4571))' | python main.py --context-url http://example2.org/context/faldo.jsonld --id-base-url http://example3.org > sample.jsonld
```

Expected output:
```json
{
  "@context": "http://example2.org/context/faldo.jsonld",
  "id": "http://example3.org/GCA000000000-J00000:join(complement(4918..5163),complement(2691..4571))",
  "location": {
    "type": "ListOfRegions",
    "member": [
      {
        "type": "Region",
        "begin": {
          "type": "ExactPosition",
          "position": 4918,
          "reference": "insdc:J00000"
        },
        "end": {
          "type": "ExactPosition",
          "position": 5163,
          "reference": "insdc:J00000"
        },
        "strand": "NegativeStrand",
        "order": 1
      },
      {
        "type": "Region",
        "begin": {
          "type": "ExactPosition",
          "position": 2691,
          "reference": "insdc:J00000"
        },
        "end": {
          "type": "ExactPosition",
          "position": 4571,
          "reference": "insdc:J00000"
        },
        "strand": "NegativeStrand",
        "order": 2
      }
    ]
  }
}
```

### Conversion from FALDO JSON-LD to ID

Input via file:
```bash
$ python main.py -i sample.jsonld
```

Input via standard input (same as using -i with a file):
```bash
$ cat sample.jsonld | python main.py
```

Expected output（If the contents of sample.jsonld are to be those of the example immediately above）:
```text
GCA000000000-J00000:join(complement(4918..5163),complement(2691..4571))
```

Specify JSON content directly in the -i option:
```bash
$ python main.py -i '{
  "@context": "http://example.org/context/faldo.jsonld",
  "id": "http://example.org/GCA000000000-J00000:467",
  "location": {
    "type": "ExactPosition",
    "position": 467,
    "reference": "insdc:J00000"
  }
}'
```

Expected output:
```text
GCA000000000-J00000:467
```
