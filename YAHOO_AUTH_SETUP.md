# Yahooアカウント認証設定ガイド

## 概要

Yahooアカウントを使用することで、レート制限を回避し、より安定した株価データの取得が可能になります。

## 設定方法

### コンフィグファイルを使用（推奨）

アプリケーションの設定は`config.json`ファイルで管理します。

1. **サンプルコンフィグファイルをコピー**
   ```bash
   cp config.json.example config.json
   ```

2. **ブラウザでYahoo Financeにログイン**
   - https://finance.yahoo.com にアクセス
   - Yahooアカウントでログイン

3. **Cookieを取得**
   - ブラウザの開発者ツールを開く（F12）
   - Networkタブを開く
   - ページをリロード（F5）
   - 任意のリクエストを選択
   - Headersタブで「Cookie:」の値をコピー

4. **config.jsonファイルを編集**

   `config.json`ファイルの`yahoo_auth`セクションを編集：

   ```json
   {
     "yahoo_auth": {
       "enabled": true,
       "cookie": "your_cookie_string_here",
       "username": "",
       "password": ""
     }
   }
   ```

   **注意**: 
   - `config.json`ファイルは`.gitignore`に含まれているため、Gitにコミットされません
   - Cookieを設定する場合は`enabled`を`true`に設定してください

## Cookieの取得例

開発者ツールで取得したCookieの例：

```
A3=d=AQABBN...&b=2&c=...; A1=d=AQABBN...&b=3&c=...; GUC=AQABBAFh...; A1S=d=AQABBN...&b=2&c=...
```

この文字列全体を`config.json`の`yahoo_auth.cookie`に設定します。

## 認証状態の確認

アプリケーション起動時に、認証状態が表示されます：

```
Yahoo認証: 有効
```

認証が無効な場合：

```
Yahoo認証: 無効（匿名アクセス）
```

## トラブルシューティング

### Cookieが無効になった場合

- Cookieは一定期間で期限切れになることがあります
- 期限切れの場合は、再度Cookieを取得して設定してください

### レート制限が発生する場合

- Cookieが正しく設定されているか確認
- Yahoo Financeにログインした状態でCookieを取得しているか確認
- ブラウザでYahoo Financeにアクセスできるか確認

### 認証が機能しない場合

1. `config.json`ファイルがプロジェクトディレクトリにあるか確認
2. `yahoo_auth.enabled`が`true`に設定されているか確認
3. `yahoo_auth.cookie`が正しく設定されているか確認
4. アプリケーションを再起動

## セキュリティに関する注意

- Cookieは機密情報です。他人と共有しないでください
- `config.json`ファイルはGitにコミットしないでください（`.gitignore`に含まれています）
- 本番環境では、`config.json`ファイルの権限を適切に設定してください
- Cookieは定期的に更新することを推奨します（期限切れになる可能性があります）

## 参考

- [Yahoo Finance](https://finance.yahoo.com)
- [python-dotenv ドキュメント](https://pypi.org/project/python-dotenv/)
