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
mv datasets ~/.local/bin/

# PATH が通っているか確認
which datasets
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
npm install -g @jbrowse/cli
jbrowse --version
```


### Samtools のインストール

FASTA のインデックス作成に利用します。
実行環境において `samtools` コマンドが使用できる状態にしておいてください。  

インストール方法や詳細については公式ページを参照してください：  
- 公式サイト: http://www.htslib.org/
- GitHub: https://github.com/samtools/samtools

例として、Ubuntu22.04 では apt を用いて以下のようにインストールできます。
```bash
apt install samtools
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
  pip install biopython
  pip install requests
  ```
### bedGraphToBigWigコマンドのインストール
- バーグラフトラックで利用するBigWig変換時に必要
```
mamba install -c bioconda ucsc-bedgraphtobigwig
```

### ソースコードのダウンロード、ディレクトリ移動
```
git clone https://github.com/ddbj/universal-public-genome.git -b develop
cd universal-public-genome/publication-count
```

### 文献頻度情報作成スクリプトの設定ファイルの準備      
- config.iniを作成
  ```
  cp config.ini-sample config.ini
  ```

- config.iniの説明（基本的には変更不要。NCBI datasets command-line toolsの配置場所にパスが通っていない場合のみ、datasets_tool_pathを設定してください）
    |項目名|説明|
    |:--|:--|
    |working_dir|ワーキングディレクトリ（この項目で指定された場所に、スクリプト実行中にdatasetsによってダウンロードされたファイルを配置したり、結果のGFFファイルを出力）|
    |ncbi_dataset_zip_file|NCBI datasets command-line toolsでダウンロードされるファイル名|
    |datasets_tool_path|NCBI datasets command-line toolsのパス（パスを通してある場合は設定不要）|



## JBrowseに登録するデータの準備、プロジェクトの作成


<h3 id="prepare-jbrowse-script">
A. スクリプトによる自動実行の場合（通常はこちら）
</h3>

- 通常はこちらの方法を使用します。
- スペース区切りで複数のアセンブリアクセッションを指定できます。
- すでに JBrowse に登録されているアセンブリは自動的にスキップされます。
- 本手順では、アセンブリアクセッション（Assembly accession） 「GCA_000012525.1」「GCA_000005845.2」「GCA_000006745.1」 を例とします。

```bash
./prepare_jbrowse.sh GCA_000012525.1 GCA_000005845.2 GCA_000006745.1
```
- このスクリプト内で以下の処理が行われます。
  1. 文献頻度入り GFF の生成
  2. FASTA のダウンロード、解凍
  3. .fai ファイルの作成
  4. JBrowseプロジェクトの準備（$HOME/jbrowse/jbrowse2 への配置）
  5. アセンブリの追加
  6. GFFトラックの追加
  7. BigWigの作成とトラック追加
  8. 一時ファイルの削除（1,2,7で生成、ダウンロードした中間ファイル等）

  <details>
  <summary>（参考）実行結果の例（正常終了）</summary>
  
  ```text
  ============================================
  Summary
  ============================================
  Success:
    - GCA_000012525.1
    - GCA_000005845.2
    - GCA_000006745.1

  Skipped:
    (none)

  Failed:
    (none)
  ============================================
  ```
  </details>
<p></p>

- 詳細表示を行いたい場合は --verbose を指定してください。  
処理中の標準出力を画面およびログに出力します。
  ```bash
  ./prepare_jbrowse.sh --verbose GCA_000012525.1 GCA_000005845.2 GCA_000006745.1
  ```

- （参考）本手順では、ソースコードが配置されているディレクトリ（Git clone 先）と、JBrowse プロジェクトを作成するディレクトリは別の場所になります。  
以下に、上記の prepare_jbrowse.sh 実行後に生成される各ディレクトリの構造を示します。

  <details>
  <summary>実行後のディレクトリ構造（参考）</summary>

    - **ソースコード側（universal-public-genome/publication-count）**  
      … prepare_jbrowse.sh / publication-count-gff.py / ログ などが置かれる

      ```text
      universal-public-genome/
      └ publication-count/
          ├ prepare_jbrowse.sh
          ├ prepare_jbrowse_single.sh
          ├ prepare_jbrowse_bulk.sh
          ├ publication-count-gff.py
          ├ config.ini
          └ logs/
              ├ publication-count-gff/
              │   └ error.log
              └ prepare_jbrowse/
                  ├ summary.log
                  ├ GCA_000005845.2.log
                  ├ GCA_000006745.1.log
                  └ GCA_000012525.1.log
      ```

    - **JBrowse プロジェクト側（$HOME/jbrowse/jbrowse2）**  
      … assemblies, tracks, config.json が配置される

      ```text
      $HOME/jbrowse/jbrowse2/
      ├ assemblies/
      │   ├ GCA_000005845.2_ASM584v2_genomic.fna
      │   ├ GCA_000005845.2_ASM584v2_genomic.fna.fai
      │   ├ GCA_000006745.1_ASM674v1_genomic.fna
      │   ├ GCA_000006745.1_ASM674v1_genomic.fna.fai
      │   ├ GCA_000012525.1_ASM1252v1_genomic.fna
      │   └ GCA_000012525.1_ASM1252v1_genomic.fna.fai
      ├ tracks/
      │   ├ GCA_000005845.2_output.bw
      │   ├ GCA_000005845.2_output.gff
      │   ├ GCA_000006745.1_output.bw
      │   ├ GCA_000006745.1_output.gff
      │   ├ GCA_000012525.1_output.bw
      │   └ GCA_000012525.1_output.gff
      └ config.json
      ```
  </details>

<p></p>

<details>
<summary><span style="font-size:1.17em; font-weight:bold;">
B. 手動実行の場合（通常は使用しません）
</span></summary>

- 通常は、先述した [スクリプトによる自動実行の場合](#prepare-jbrowse-script) で対応できるため、本手順は不要です。  
トラブル対応・動作理解・検証目的で手動で実行したい場合は以下を参照してください。
- 本手順はローカル環境に対する作業例ですが、公開版のJBrowseを使用する場合は適宜読み替えてください。
- 本手順では、アセンブリアクセッション（Assembly accession）「GCA_000012525.1」を例とします。

#### B-1．文献頻度情報を含むGFFの作成
```bash
python publication-count-gff.py -i GCA_000012525.1
```

- このスクリプト内で以下の処理が行われます。
  1. NCBI datasetsで座標が表現されたファイル（gbff）を取得する
  2. 1で取得したGenBankファイルをパースしLocation IDと対応するprotein IDを取得する
  3. EMBL-CDS IDからUniProt / PubChemを利用して関連文献PubMed IDを取得する
  4. 関連文献数をscoreとして含むGFFファイルを出力する


#### B-2．FASTA のダウンロード、解凍（NCBI datasets command-line toolsを使用）

```bash
datasets download genome accession GCA_000012525.1 --include genome
unzip ncbi_dataset.zip -d ncbi_dataset/
```
- datasetsの実行ファイルを配置した場所にパスが通っていない場合は、フルパスで指定してください。

#### B-3．.fai ファイルの作成

```bash
samtools faidx ncbi_dataset/ncbi_dataset/data/GCA_000012525.1/GCA_000012525.1_ASM1252v1_genomic.fna
```

#### B-4．JBrowseのプロジェクト作成、アセンブリ・トラック追加に必要なファイルの移動、ディレクトリ移動

```bash
# JBrowse用のディレクトリを作成し、その中にプロジェクト作成
# この例では $HOME/jbrowse ディレクトリ内に、jbrowse2という名称でプロジェクトを作成します
mkdir -p $HOME/jbrowse
jbrowse create $HOME/jbrowse/jbrowse2

# アセンブリ・トラック追加用ファイルの配置場所を作成
mkdir -p $HOME/jbrowse/jbrowse2/{assemblies,tracks}

# アセンブリ追加用ファイルを移動
mv ncbi_dataset/ncbi_dataset/data/GCA_000012525.1/GCA_000012525.1_ASM1252v1_genomic.fna ncbi_dataset/ncbi_dataset/data/GCA_000012525.1/GCA_000012525.1_ASM1252v1_genomic.fna.fai $HOME/jbrowse/jbrowse2/assemblies/

# トラック追加用ファイルを移動（1で作成したGFF）
mv GCA_000012525.1_output.gff $HOME/jbrowse/jbrowse2/tracks/

# ディレクトリを移動
cd $HOME/jbrowse/jbrowse2
```


#### B-5．アセンブリの追加
```bash
jbrowse add-assembly assemblies/GCA_000012525.1_ASM1252v1_genomic.fna --load inPlace
# 成功すると "Added assembly "GCA_000012525.1_ASM1252v1_genomic.fna" to config.json" のようなメッセージが表示されます
```


#### B-6．トラックの追加（1）
- 1で作成したGFFを利用します

```bash
jbrowse add-track tracks/GCA_000012525.1_output.gff --assemblyNames GCA_000012525.1_ASM1252v1_genomic.fna --load inPlace --name "Gene annotation" --trackId GCA_000012525.1_gff
# 成功すると "Added track with name "GCA_000012525.1_output" and trackId "GCA_000012525.1_output" to ./config.json" のようなメッセージが表示されます
```

#### B-7. トラックの追加（2）
- 3で作成したfaidx および 1で作成したGFFを利用して BigWigを作成します。

```bash
#faidx GCA_000012525.1_ASM1252v1_genomic.fna
cut -f1,2 assemblies/GCA_000012525.1_ASM1252v1_genomic.fna.fai > GCA_000012525.1.chrom.sizes

awk -F'\t' 'BEGIN{OFS="\t"} tolower($3)=="gene" && $6!="." {print $1, $4-1, $5, $6}' \
  tracks/GCA_000012525.1_output.gff \
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

bedGraphToBigWig GCA_000012525.1_output.noOverlap.bedGraph   GCA_000012525.1.chrom.sizes   tracks/GCA_000012525.1_output.bw

rm GCA_000012525.1.chrom.sizes GCA_000012525.1_output.bedGraph GCA_000012525.1_output.noOverlap.bedGraph
```
- Trackに追加します。

```bash
jbrowse add-track tracks/GCA_000012525.1_output.bw  --assemblyNames GCA_000012525.1_ASM1252v1_genomic.fna --load inPlace --name "Publication count"  --trackId GCA_000012525.1_bw
```

</details>

## JBrowseの起動

### 1.ローカルサーバーの起動

```bash
cd $HOME/jbrowse/jbrowse2
npx serve . -l tcp://0.0.0.0:3333 --no-clipboard
```
- 初回実行時は、以下のように serve パッケージのインストール確認が表示される場合があります。その場合は y を入力して続行してください。
  ```bash
  Need to install the following packages:
    serve@14.2.5
  Ok to proceed? (y)
  ```

### 2．ブラウザからアクセス

- npx serve . でローカルサーバーを起動した際に表示されたURLにアクセスすることで表示できます。
  以下は例です。
  ```
  http://localhost:3333
  ```

- JBrowse の詳細な操作方法については、公式ドキュメントを参照してください。  
https://jbrowse.org/jb2/docs/
