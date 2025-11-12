# ユースケース：ゲノムごとに文献頻度情報を作成 〜 JBrowseへの登録、閲覧まで

本手順では、指定したアセンブリアクセッション（Assembly accession）に対応する文献頻度情報を取得し、GFF形式で出力してJBrowseで可視化するまでの流れを示します。

## 動作確認済環境

| OS | Python | Node.js | JBrowse CLI | Samtools |
|:--|:--|:--|:--|:--|
| Ubuntu 22.04 | 3.9 | v22.20.0 | 3.6.5 | 1.13 |
| macOS Sequoia 15.7 | 3.13 | v22.7.0 | 3.6.4 | 1.22.1 |


## 事前準備

### NCBI datasets command-line toolsのインストール
インストール方法や詳細については公式ページを参照してください。
- https://www.ncbi.nlm.nih.gov/datasets/docs/v2/command-line-tools/download-and-install/

ダウンロードしたdatasetsツールのパスを通しておいてください。（datasets コマンドをどこからでも実行できるようにするため）
```bash
# 例：~/.local/bin に配置する場合
$ mv datasets ~/.local/bin/

# PATH が通っているか確認
$ which datasets
```

※ 配置した場所が PATH に含まれていない場合は、以下を `~/.bashrc` などに追加してください。（`~/.local/bin` の場合の例）
```bash
export PATH="$HOME/.local/bin:$PATH"
```


### JBrowseのインストール
npmでインストールするので、**Nodejs**が必要です。
Nodejsのインストール方法や詳細については公式ページを参照してください。
- https://nodejs.org/

Nodejsをインストールし、npmコマンドが使える状態になったら、以下のようにjbrowseをインストールできます。
```bash
$ npm install -g @jbrowse/cli
$ jbrowse --version
```


### Samtools のインストール

FASTA のインデックス作成に利用します。
実行環境において `samtools` コマンドが使用できる状態にしておいてください。  

インストール方法や詳細については公式ページを参照してください：  
- 公式サイト: http://www.htslib.org/
- GitHub: https://github.com/samtools/samtools

例として、Ubuntu22.04 では apt を用いて以下のようにインストールできます。
```bash
$ apt install samtools
```


### 文献頻度情報作成スクリプトに必要なパッケージのインストール

- **Python 3.9 以上** が必要です。Python がインストールされていない場合は、[公式サイト](https://www.python.org/downloads/) からインストールしてください。
  - 確認コマンド:
    ```bash
    $ python -V
    Python 3.13.3
    ```
    
- 以下のパッケージをインストールしてください。
  ```
  $ pip install biopython
  $ pip install requests
  ```
### bedGraphToBigWigコマンドのインストール
- バーグラフトラックで利用するBigWig変換時に必要
```
mamba install -c bioconda ucsc-bedgraphtobigwig
```

## 実行手順

- 本手順はローカル環境に対する作業例ですが、公開版のJBrowseを使用する場合は適宜読み替えてください。
- 本手順では、アセンブリアクセッション（Assembly accession）「GCA_000012525.1」を例とします。

### １．ソースコードのダウンロード、ディレクトリ移動
```
$ git clone https://github.com/ddbj/universal-public-genome.git -b develop
$ cd universal-public-genome/publication-count
```

### ２．文献頻度情報作成スクリプトの設定ファイルの準備      
- config.iniを作成
  ```
  $ cp config.ini-sample config.ini
  ```

- config.iniの説明（基本的には変更不要。NCBI datasets command-line toolsの配置場所にパスが通っていない場合のみ、datasets_tool_pathを設定してください）
    |項目名|説明|
    |:--|:--|
    |working_dir|ワーキングディレクトリ（この項目で指定された場所に、スクリプト実行中にdatasetsによってダウンロードされたファイルを配置したり、結果のGFFファイルを出力）|
    |ncbi_dataset_zip_file|NCBI datasets command-line toolsでダウンロードされるファイル名|
    |datasets_tool_path|NCBI datasets command-line toolsのパス（パスを通してある場合は設定不要）|


### ３．文献頻度情報を含むGFFの作成
```
$ python publication-count-gff.py -i GCA_000012525.1
```

- このスクリプト内で以下の処理が行われます。
  1. NCBI datasetsで座標が表現されたファイル（gbff）を取得する
  2. 1で取得したGenBankファイルをパースしLocation IDと対応するprotein IDを取得する
  3. EMBL-CDS IDからUniProt / PubChemを利用して関連文献PubMed IDを取得する
  4. 関連文献数をscoreとして含むGFFファイルを出力する


### ４．FASTA のダウンロード、解凍（NCBI datasets command-line toolsを使用）

```bash
$ datasets download genome accession GCA_000012525.1 --include genome
$ unzip ncbi_dataset.zip -d ncbi_dataset/
```
- datasetsの実行ファイルを配置した場所にパスが通っていない場合は、フルパスで指定してください。

### ５．.fai ファイルの作成

```bash
$ samtools faidx ncbi_dataset/ncbi_dataset/data/GCA_000012525.1/GCA_000012525.1_ASM1252v1_genomic.fna
```

### ６．JBrowseのプロジェクト作成、アセンブリ・トラック追加に必要なファイルの移動、ディレクトリ移動

```bash
# JBrowse用のディレクトリを作成し、その中にプロジェクト作成
# この例では $HOME/jbrowse ディレクトリ内に、jbrowse2という名称でプロジェクトを作成します
$ mkdir -p $HOME/jbrowse
$ jbrowse create $HOME/jbrowse/jbrowse2

# アセンブリ・トラック追加用ファイルの配置場所を作成
$ mkdir -p $HOME/jbrowse/jbrowse2/{assemblies,tracks}

# アセンブリ追加用ファイルを移動
$ mv ncbi_dataset/ncbi_dataset/data/GCA_000012525.1/GCA_000012525.1_ASM1252v1_genomic.fna ncbi_dataset/ncbi_dataset/data/GCA_000012525.1/GCA_000012525.1_ASM1252v1_genomic.fna.fai $HOME/jbrowse/jbrowse2/assemblies/

# トラック追加用ファイルを移動（３.で作成したGFF）
$ mv GCA_000012525.1_output.gff $HOME/jbrowse/jbrowse2/tracks/

# ディレクトリを移動
$ cd $HOME/jbrowse/jbrowse2
```


### ７．アセンブリの追加
```bash
$ jbrowse add-assembly assemblies/GCA_000012525.1_ASM1252v1_genomic.fna --load inPlace
# 成功すると "Added assembly "GCA_000012525.1_ASM1252v1_genomic.fna" to config.json" のようなメッセージが表示されます
```


### ８．トラックの追加（1）
- 3で作成したGFFを利用します

```bash
#$ jbrowse add-track tracks/GCA_000012525.1_output.gff --assemblyNames GCA_000012525.1_ASM1252v1_genomic.fna --load inPlace
$ jbrowse add-track tracks/GCA_000012525.1_output.gff --assemblyNames GCA_000012525.1_ASM1252v1_genomic.fna --load inPlace --name "Gene annotation" --trackId GCA_000012525.1_gff
# 成功すると "Added track with name "GCA_000012525.1_output" and trackId "GCA_000012525.1_output" to ./config.json" のようなメッセージが表示されます
```

### 9. トラックの追加（2）
- 5で作成したfaidx および 3で作成したGFFを利用して BigWigを作成します。

```
#faidx GCA_000012525.1_ASM1252v1_genomic.fna
cut -f1,2 assemblies/GCA_000012525.1_ASM1252v1_genomic.fna.fai > GCA_000012525.1.chrom.sizes

awk -F'\t' 'BEGIN{OFS="\t"} $6!="." && $3=="gene" {print $1, $4-1, $5, $6}' \
  input.gff3 \
  | sort -k1,1 -k2,2n > GCA_000012525.1_output.bedGraph


LC_ALL=C sort -k1,1 -k2,2n GCA_000012525.1_output.bedGraph \
| awk -F'\t' 'BEGIN{OFS="\t"}
  /^#/ {next}                          # コメント行は除外
  {
    chr=$1; s=$2+0; e=$3+0; v=$4
    # 染色体が変わったらリセット
    if (chr!=prev_chr) { prev_chr=chr; prev_end=0 }
    # 直前の出力区間(prev_end)と重なる先頭を切り上げ
    if (s < prev_end) s = prev_end
    # 長さが残っていれば出力し、prev_end を更新
    if (s < e) { print chr, s, e, v; prev_end = e }
    # もし s>=e になったら完全に食い込んでいるので捨てる（出力しない）
  }' > GCA_000012525.1_output.noOverlap.bedGraph

bedGraphToBigWig GCA_000012525.1_output.noOverlap.bedGraph   GCA_000012525.1.chrom.sizes   GCA_000012525.1_output.bw
```
- Trackに追加します。

```
jbrowse add-track tracks/GCA_000012525.1_output.bw  --assemblyNames GCA_000012525.1_ASM1252v1_genomic.fna --load inPlace --name "GFF score (bar)"  --trackId GCA_000012525.1_bw
```

**TODO: コマンド実行ディレクトリを固定して動作確認、一時ファイルの削除、assemblyNames、track name/Idの修正、コマンド実行省力化**

### 10．ローカルサーバーの起動

```bash
$ npx serve . -l tcp://0.0.0.0:3333 --no-clipboard
#$ npx serve .
```
- 初回実行時は、以下のように serve パッケージのインストール確認が表示される場合があります。その場合は y を入力して続行してください。
  ```bash
  Need to install the following packages:
    serve@14.2.5
  Ok to proceed? (y)
  ```

### 10．ブラウザからアクセス

- npx serve . でローカルサーバーを起動した際に表示されたURLにアクセスすることで表示できます。
  以下は例です。
  ```
  http://localhost:3333
  ```

- JBrowse の詳細な操作方法については、公式ドキュメントを参照してください。  
https://jbrowse.org/jb2/docs/
