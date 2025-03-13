# annict-discord-bot

**Note**: これは[annict-discord-bot](https://github.com/naskya/annict-discord-bot)のforkです。詳細はfork元のリポジトリとブログを参照してください。変更した点は以下の通り。

- 放送シーズンの情報が未定である作品がリストに入っている場合、エラーが発生する点を修正。
- 「見てる」「見た」の他に「見たい」「一時中断している」「視聴中止した」の視聴状況も追跡するようにした。

---

[Annict](https://annict.com/) に記録したアニメの視聴記録（作品の視聴開始・終了のみ）を
[Discord](https://discord.com) の特定のチャンネルに転送します。

[Discord bot の作成](https://discord.com/developers/applications/)および投稿したいサーバーへの招待が必要です。

## 設定

`config` という名前のファイルに入っているダミーの文字列を置き換えて

- Annict のユーザー ID
- Annict のアクセストークン
- Discord bot のアクセストークン
- Discord チャンネルの ID

を設定します。

## 使用例

systemd timer を用いて定期的に実行します。

```
# /etc/systemd/system/annict-discord-bot.service

[Unit]
Description=forward activities recorded on Annict to Discord

[Service]
Type=simple
ExecStart=/path/to/annict-discord-bot/main.py
WorkingDirectory=/path/to/annict-discord-bot

[Install]
WantedBy=multi-user.target
```

```
# /etc/systemd/system/annict-discord-bot.timer

[Unit]
Description=run annict-discord-bot

[Timer]
OnCalendar=*-*-* *:00/20:00
Persistent=true

[Install]
WantedBy=timers.target
```

`/path/to/annict-discord-bot` はリポジトリを clone したディレクトリに置き換えてください。

`systemctl` コマンドで定期実行を有効化します。

```sh
# systemctl enable annict-discord-bot.service
# systemctl enable annict-discord-bot.timer
```

ログの確認は `journalctl` コマンドで行います。

```sh
$ journalctl -xeu annict-discord-bot
```

## 備考

一度投稿した内容は再投稿しないようになっています。そのため

```sh
$ ./main.py
$ ./main.py
```

とすると二度目の実行ではメッセージは投稿されません（実行すると実際に Discord チャンネルにメッセージが投稿される
のでご注意ください）。

メッセージを投稿すること無く、現在までに Annict に記録してあるもののデータの取得を行って投稿済みの扱いにしたい
（今後新たに記録したもののみを Discord チャンネルに投稿したい）場合には `dry` という引数をつけて実行します。

```sh
$ ./main.py dry
```
