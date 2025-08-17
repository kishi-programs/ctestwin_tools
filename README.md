# CTESTWIN Setup GUI (v8.3)

CTESTWIN の運用準備（空の `.lg8` 作成 / `Ctestwin.ini` 更新）を GUI で行うためのツールです。Python と Tkinter のみで動作します。

---

## 特長

- **空の `.lg8` をワンクリックで作成**
  - ファイル名は `西暦_大会キー_周波数.lg8`（例: `2025_allja_7MHz.lg8`）
  - `.lg8` の「周波数」「モード」「ContestKind」「クラブ局 OP 名簿」「ユーザー定義マルチ（.md へのパス）」をトレーラーに格納
- **`Ctestwin.ini` を GUI で編集**
  - [UrCnum]（周波数帯ごとの送信ナンバー）を**左右 2 列**にレイアウトし、**右欄の値を全周波数へ一括適用**ボタンを用意
  - [Partial], [CW], [CurrentData], [Startup], [Contest] の主要項目に対応（詳細は下記）
  - すべてのパス入力に**参照ダイアログ**を設置（直打ち不要）
- **`.lg8` の簡易インスペクタ**
  - QSO 数、周波数/モード（ラベル付き）、ContestKind、トレーラーのオフセットを表示
- **コンテスト選択の柔軟性**
  - 定番コンテストのプルダウンに加え、**ユーザー定義 `.md`**や**番号直指定**に対応（`ContestKind`/`ContestKey` を取り込み）

---

## 動作環境

- Windows / macOS / Linux（CTESTWIN 自体は Windows を想定）
- Python **3.8+**（Tkinter 同梱必須）
- 追加ライブラリ不要（標準ライブラリのみ）

> 文字コードは CP932（Shift_JIS）を前提としており、`.ini` / `.lg8` の固定長文字列は CP932 + NUL でエンコードされます。

---

## セットアップ & 起動

1. Python をインストール（Windows なら「Add python.exe to PATH」にチェック）
2. 本リポジトリを取得し、次を実行：

```bash
python ctestwin_setup_automator.py
```

> EXE 化したい場合は PyInstaller などをご利用ください（例：`pyinstaller -F -w ctestwin_setup_automator.py`）。

---

## 使い方（ワークフロー）

### 1) 「基本」タブ
1. **西暦** … 「自動（今年）」のままで OK（固定したい場合はチェックを外す）
2. **大会** … プルダウンから選択。  
   - 「**その他（番号指定）**」では `大会キー（ファイル名用）` と `大会番号（ContestKind）` を入力  
   - 「**○○（.md 参照）**」では下の **ユーザー定義 .md** のメタデータを取り込みます
3. **周波数 / モード** … CTESTWIN の帯域ラベル・モード名を選択
4. **ユーザー定義 .md（任意）** … 後述のフロントマターを含む `.md` を指定可
5. **出力フォルダ** … `.lg8` の出力先
6. **.lg8 新規作成** … 空の `.lg8` を作成。作成後、パスが「2) INI 設定」タブの入力欄に引き継がれます
7. **この .lg8 を起動時に開くよう .ini へ設定** … `.ini` に書き込むための準備（実書き込みは「2) INI 設定」タブで実行）
8. **検査: .lg8 の周波数/モードを表示** … 既存 `.lg8` を解析表示

> **ファイル名規則**：`{year}_{contest_key}_{band_label}.lg8` 例：`2025_allja_7MHz.lg8`

### 2) 「INI 設定」タブ
- **Ctestwin.ini** … 参照ボタンで対象の INI を指定
- **送信ナンバー既定 [UrCnum]** … 各バンドの既定送信ナンバーを設定  
  - **右のナンバーを全周波数にセット** … 右側の入力欄の値を全バンドへ一括コピー
- **パーシャルファイル [Partial:Filename]** … `.pck`/`.scp`/`.txt` 等のパス  
  - リムーバブルドライブ（例：`E:\`, `F:\`）判定時は確認ダイアログを表示
- **CW 既定 [CW]** … `CQ`（例：`CQ TEST`）、`WPM_DEF`（数値）
- **起動時に開くログ [CurrentData:CloseFname]** … 起動時に自動で開く `.lg8` のフルパス
- **ユーザー定義 .md 既定 [Contest:UserContestMD]** … 既定の `.md` パス
- **起動時の周波数/モードを .ini へも反映**（基本タブのチェック）  
  - `[CurrentData] BandLabel / ModeLabel` と `[Startup] Band / Mode` を同期

最後に **「.ini へ書き込み」** を押して保存します。

### 3) 「OP名簿」タブ
- 1 行 1 名で最大 30 名まで入力し、**「名簿を .ini に反映」** を押します（`[CLUB] OP1..OP30` に出力）。

---

## ユーザー定義 `.md` のメタデータ（任意）

`.md` の先頭に **YAML 風フロントマター** または **key=value / key: value** 形式でメタデータを書くと、GUI が取り込みます。

### サポート項目
- `ContestKind`（数値）
- `ContestKey`（半角英数字/`_`/`-` のみ）
- `ContestName`（任意の文字列）

### 例（YAML 風フロントマター）
```md
---
ContestKind: 14
ContestKey: alltohoku
ContestName: オール東北コンテスト
---

（以下、ルールやマルチ一覧など）
```

> `.md` 側に `ContestKey` / `ContestKind` があれば GUI の入力より優先されます。`ContestKind` が確定しない場合は安全側で **14（ユーザー定義マルチ）** を既定値とします。

---

## `.ini` に書き込まれる主な項目

```ini
[UrCnum]
7MHz=001
...

[CLUB]
OP1=JA7XXX
OP2=...
...

[Partial]
Filename=C:\path\to\partial.pck

[CW]
CQ=CQ TEST
WPM_DEF=22

[CurrentData]
CloseFname=C:\logs\2025_allja_7MHz.lg8
BandLabel=7MHz
ModeLabel=SSB

[Startup]
Band=7MHz
Mode=SSB

[Contest]
UserContestMD=C:\path\to\contest.md
```

> バンドラベルは CTESTWIN に合わせて **`1.9MHz` ~ `248GHz`（全 23 帯）** を使用します。

---

## `.lg8` の作成仕様（概要）

- 先頭に **QSO 数 (uint16 little-endian)** を 0 で書き込み
- 一部ビルド互換のため、**レガシー 2B ヘッダ**を既定とし、後方に **トレーラー**を連結
- トレーラーには次の情報を格納：
  - `ModeCurrent`, `FreqCurrent`, `ContestKind`, `Is001Style`, `DupePolicy`, `TwiceMinusOne`
  - `PointPhone[23]`, `PointCW[23]`
  - `ClubOpName[30]`（各 20B、CP932 + NUL 固定長）
  - `UserDefinedMultiPath`（`.md` のパス、CP932 + NUL）

> **注意**：同名ファイルが存在する場合は**上書き**されます。必要に応じてバックアップを作成してください。

---

## 定番コンテスト（プルダウン）

- All JA / 6m and down / 全市全郡（ACAG）/ Field Day / All Asian DX / CQ WW DX など  
- 「オール東北」「オール宮城」は **`.md` 参照**運用を想定

---

## 既知の制限・注意事項

- `.lg8` は**空ファイル**として作成します（QSO データの書き込み機能はありません）
- パスのエンコードは CP932 ベース。OS 設定や Unicode パスで問題が出る場合は短い ASCII パスを推奨
- 一部の CTESTWIN ビルドにより、起動時のバンド/モード参照先が異なることがあります（`[CurrentData]` と `[Startup]` の両方へ書き込み）
- リムーバブルドライブのパスを直接参照すると、運用当日にドライブ文字が変わって参照不可になる恐れがあるため、**ローカルへコピー**を推奨

---

## 変更履歴（抜粋）

- **v8.3**
  - [UrCnum] レイアウトを**左右 2 列**に変更（左：1.9MHz〜144MHz / 右：430MHz〜136kHz）
  - **「右のナンバーを全周波数にセット」**ボタンを追加
  - すべてのファイル/フォルダ入力欄へ**参照ダイアログ**を配置

（ベース：v8_2_安定版.py）

---

## ライセンス

- **未設定**（必要に応じて本 README に追記してください）

---

## 開発メモ

- 主要モジュール：`tkinter`, `configparser`, `struct`, `pathlib`, `dataclasses`
- `.ini` は `configparser.RawConfigParser` で大小文字を保持して出力
- `.md` のメタデータは先頭 2,000 文字から抽出（YAML 風または `key=value` / `key: value`）
