# ユースケース：ゲノム毎に文献頻度情報を作成

## 事前準備
- NCBI datasets command-line toolsをインストール
    * https://www.ncbi.nlm.nih.gov/datasets/docs/v2/command-line-tools/download-and-install/

- gene2accession.gz をダウンロード
    * https://ftp.ncbi.nih.gov/gene/DATA/gene2accession.gz
    * https://ftp.ncbi.nih.gov/gene/DATA/README

- 必要なパッケージのインストール
    ```
    pip install biopython
    pip install requests
    ```

- ソースコードのダウンロード、ディレクトリ移動
    ```
    git clone https://github.com/ddbj/universal-public-genome.git -b develop
    cd universal-public-genome/publication-count
    ```

- gene2accession.gz をsqliteのデータベース化
    * config.iniを作成
        ```
        cp config.ini-sample config.ini
        ```
    * config.iniの設定
        |項目名|説明|
        |:--|:--|
        |gz_file|ダウンロードしたgene2accession.gzを配置したパス|
        |db_file|gene2accession.gzをsqlite化したgene2accession.dbを出力するパス(30GB超のファイルが出力されるので、容量の空きがある場所にしてください)|
        |working_dir|ワーキングディレクトリ（この項目に指定された場所に、datasetsによってダウンロードされたファイルを配置したり、結果のGFFファイルを出力します）|
        |ncbi_dataset_zip_file|NCBI datasets command-line toolsでダウンロードされるファイル名（基本的にはncbi_dataset.zipのままで問題ないはずです）|
        |datasets_tool_path|NCBI datasets command-line toolsのパス（パスを通してある場合は設定不要です）|

    * 次のコマンドでデータベース化を実行
        ```
        python gene2accession_gz2db.py
        ```


## 実行手順
- 以下のpythonスクリプトを実行する。（-iオプションにAssembly Accessionを指定）
```
python publication-count-gff.py -i GCF_000968255.1
```
- 補足事項
    * SPARQLエンドポイントに負荷をかけないようにするため、開発中はGenbankファイルの1レコードのみを処理するように変えています。
    * 結果ファイルとしてGFFが出力されますが、現時点の内容は仮です。