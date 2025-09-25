# ユースケース：ゲノム毎に文献頻度情報を作成

## 事前準備

### NCBI datasets command-line toolsのインストール
インストール方法や詳細については公式ページを参照してください。
    https://www.ncbi.nlm.nih.gov/datasets/docs/v2/command-line-tools/download-and-install/

### jbrowse　のインストール
npmでインストールするので、Nodejsが必要です。
Nodejsのインストール方法や詳細については公式ページを参照してください。
- 公式サイト: https://nodejs.org/

Nodejsをインストールし、npmコマンドが使える状態になったら、以下のようにjbrowseをインストールできます。
    ```
    $ npm install -g @jbrowse/cli
    $ jbrowse --version
    ```

### Samtools のインストール

FASTA のインデックス作成に利用します。
実行環境において `samtools` コマンドが使用できる状態にしておいてください。  

インストール方法や詳細については公式ページを参照してください：  
- 公式サイト: http://www.htslib.org/
- GitHub: https://github.com/samtools/samtools

例として、macOS では Homebrew を用いて以下のようにインストールできます。
```bash
$ brew install samtools
```

### 文献頻度情報作成スクリプトの実行準備

- 必要なパッケージのインストール
    ```
    $ pip install biopython
    $ pip install requests
    ```

- ソースコードのダウンロード、ディレクトリ移動
    ```
    $ git clone https://github.com/ddbj/universal-public-genome.git -b develop
    $ cd universal-public-genome
    ```

- 設定ファイルの準備
    * config.iniを作成
        ```
        $ cp config.ini-sample config.ini
        ```
    * config.iniの設定
        |項目名|説明|
        |:--|:--|
        |working_dir|ワーキングディレクトリ（この項目で指定された場所に、スクリプト実行中にdatasetsによってダウンロードされたファイルを配置したり、結果のGFFファイルを出力します）|
        |ncbi_dataset_zip_file|NCBI datasets command-line toolsでダウンロードされるファイル名（基本的にはncbi_dataset.zipのままで問題ないはずです）|
        |datasets_tool_path|NCBI datasets command-line toolsのパス（パスを通してある場合は設定不要です）|


## 実行手順

以下は、GCA_000012525.1を例とします。
また、本手順はローカル環境に対する作業例ですが、公開版のJBrowseを使用する場合は適宜読み替えてください。

### １．文献頻度情報を含むGFFの作成
```
# このREADME.mdのあるディレクトリにいる場合
$ python publication-count-gff.py -i GCA_000012525.1
```

- このスクリプト内で以下の処理が行われます。
  1. NCBI datasetsで座標が表現されたファイル（gbff）を取得する
  2. 1で取得したGenBankファイルをパースしLocation IDと対応するprotein IDを取得する
  3. EMBL-CDS IDからUniProt / PubChemを利用して関連文献PubMed IDを取得する
  4. 関連文献数をscoreとして含むGFFファイルを出力する


### ２．FASTA のダウンロード:

```bash
$ datasets download genome accession GCA_000012525.1 --include genome
```

### ３．.fai ファイルを作成

```bash
$ samtools faidx path/to/GCA_000012525.1_ASM1252v1_genomic.fna
```

### ４．JBrowseの作業ディレクトリ作成 〜 ローカルサーバー起動

```bash
$ cd {任意の作業ディレクトリ}
$ jbrowse create jbrowse2
$ cd jbrowse2
$ npx serve .
```


### ５．アセンブリの追加

```bash
$ jbrowse add-assembly path/to/GCA_000012525.1_ASM1252v1_genomic.fna --load copy
```

注意: .fai ファイルが存在しない場合は以下のようなエラーが出ます。
```bash
Error: Could not resolve to a file or a URL: "path/to/GCA_000012525.1_ASM1252v1_genomic.fna.fai"
```


### ６．トラックの追加（1.で作成したGFFを利用します）

```bash
$ jbrowse add-track path/to/GCA_000012525.1_output.gff --assemblyNames GCA_000012525.1_ASM1252v1_genomic.fna --load copy
```

### ７．ブラウザからアクセス

npx serve . でローカルサーバーを起動した際に表示されたURLにアクセスすることで表示できます。
以下は例です。
```
http://localhost:3000
```

JBrowse の詳細な操作方法については、公式ドキュメントを参照してください。  
https://jbrowse.org/jb2/docs/