# ユースケース：ゲノム毎に文献頻度情報を作成

以下は、Streptomyces avermitilis MA-4680 = NBRC 14893 を例とする
[GCF_000968255.1](https://www.ncbi.nlm.nih.gov/datasets/genome/GCF_000968255.1/)

## 入力
Assembly Accession: GCF_000968255.1

## 出力
GFF: JBrowseTracに表示するための以下のようなGFFを出力する

```
##gff-version 3
NZ_JZJK01000011.1    .       .       3091        4134        3       .       .       .
NZ_JZJK01000079.1    .       .       256349        258310        1       .       .       .
```
## 事前準備
- NCBI datasets command-line toolsをインストール
    * https://www.ncbi.nlm.nih.gov/datasets/docs/v2/command-line-tools/download-and-install/
-  gene2accession.gz をダウンロード
    * https://ftp.ncbi.nih.gov/gene/DATA/gene2accession.gz
    * https://ftp.ncbi.nih.gov/gene/DATA/README

## 実行手順
以下のpythonスクリプトを実行する　TODO: 実装

```
python publication-count-gff.py -i GCF_000968255.1
```

## プロセス説明


### 1. NCBI datasetsで座標が表現されたファイル（gbff）を取得する
* datasets download genome accession GCF_000968255.1 --include gbff
* https://www.ncbi.nlm.nih.gov/datasets/genome/GCF_000968255.1/　からも取れる

### 2. GenBankファイルをパースしLocation IDと対応するprotein IDを取得する


### 3. protein IDとncbigene IDの関係を取得する
```
 [tf@gwb universal-public-genome]$ zcat gene2accession.gz |grep WP_010982378.1
    227882    41538051    PIPELINE    -    -    WP_010982378.1    499291120    NC_003155.5    1012131129    1168502    1169545    +    -    -    -    aveC
     /protein_id="WP_010982378.1" から gene2accession.gzでncbigene IDに辿れる
    https://ftp.ncbi.nih.gov/gene/DATA/README
    https://ftp.ncbi.nih.gov/gene/DATA/gene2accession.gz
```
### 4. PubChem cooccurrence のGeneが言及された文献数を取得する
* https://is.gd/YkGbUN

課題
*「PubChem cooccurrence のGeneが言及された文献数を取得する 」SPARQLは現時点ではGene-Geneで共起のSubject側で言及されたncbigeneのみ取得。ObjectのgeneやGene-Compound, Gene-DiseaseのGeneは未取得なのでSPARQLを更新する必要がある

### 5. JBrowseTracに表示するための以下のようなGFFを出力する
