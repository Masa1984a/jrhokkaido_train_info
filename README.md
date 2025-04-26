# JR北海道列車運行情報取得ツール

JR北海道の列車運行情報を取得するMCPサーバです。各エリア（札幌近郊、道央、道南、道北、道東、北海道新幹線）の運行情報を取得し、遅延や運休などの情報を提供します。

## 機能

- JR北海道の公式サイトから各エリアの運行情報を取得
- 「遅延」「運休」などの情報をカテゴリ分け
- エリア指定による情報取得（札幌/道央/道南/道北/道東/北海道新幹線）
- 漢字表記とローマ字コードの両方をサポート

## 要件

- Python 3.8以上
- 必要なパッケージは`requirements.txt`に記載

## インストール

```bash
git clone https://github.com/Masa1984a/jrhokkaido_train_info.git
```

## 使い方 (Windows Claude for Desktop)
Claudeの「claude_desktop_config.json」について、下記を参考にして追記する。
```json
{
  "mcpServers": {
    "jrhokkaido-train-info": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\<your folder>\\jrhokkaido_train_info", 
        "run",
        "jrhokkaido_train_info.py"
      ],
      "workingDirectory": "C:\\<your folder>\\jrhokkaido_train_info"
    }
  }
}
```
Claudeを再起動すると使えるようになります。

具体的には下記のように使用できます。
![alt text](image/Image.gif)

## ライセンス

MIT

## 謝辞

このツールはJR北海道の公式運行情報ページの情報を利用しています。
Tinjyuuさん、hfujikawa77さんが公開されているMCPサーバをかなり参考にしています。
https://github.com/tinjyuu/
https://github.com/hfujikawa77/
