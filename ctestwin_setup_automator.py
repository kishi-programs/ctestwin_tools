#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CTESTWIN Setup GUI (v8.3)
-------------------------
- INI 編集の「送信ナンバー [UrCnum]」のレイアウトを、
  画像のような左右2列（左：1.9MHz〜144MHz / 右：430MHz〜136kHz）に変更。
- 「右のナンバーを全周波数にセット」ボタンを追加（右側エントリの値を全バンドに一括適用）。
- すべてのファイル/フォルダ入力欄に選択ダイアログボタンを配置済み（直打ち不要）。

Base: v8_2_安定版.py
"""
from __future__ import annotations
import os
import struct
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from dataclasses import dataclass, field
from pathlib import Path
import configparser
from typing import List, Optional
from datetime import datetime
import re

# ------------------------------
# Constants / tables
# ------------------------------
MODE_TABLE = {
    0: "CW", 1: "RTTY", 2: "SSB", 3: "FM", 4: "AM", 5: "ATV", 6: "SSTV", 7: "PSK",
    8: "GMSK", 9: "MFSK", 10: "QPSK", 11: "FSK", 12: "D-STAR", 13: "C4FM",
    14: "JT65", 15: "JT9", 16: "ISCAT", 17: "FT8", 18: "JT4", 19: "QRA64",
    20: "MSK144", 21: "WSPR", 22: "JTMS", 23: "FT4", 24: "FST4",
}
MODE_TABLE_INV = {v:k for k,v in MODE_TABLE.items()}

BAND_TABLE = {
    0:"1.9MHz", 1:"3.5MHz", 2:"7MHz", 3:"10MHz", 4:"14MHz", 5:"18MHz", 6:"21MHz",
    7:"24MHz", 8:"28MHz", 9:"50MHz", 10:"144MHz", 11:"430MHz", 12:"1200MHz",
    13:"2400MHz", 14:"5600MHz", 15:"10GHz", 16:"24GHz", 17:"47GHz",
    18:"75GHz", 19:"77GHz", 20:"135GHz", 21:"248GHz", 22:"136kHz",
}
BAND_TABLE_INV = {v:k for k,v in BAND_TABLE.items()}
FREQNUM = 23

QSO_SIZE = 170
HEADER_EXTRA = 14

# ------------------------------
# Contest table（プルダウン用）
# display_name: {"key": ファイル名用キー, "kind": ContestKind番号 or None}
#   ※ kind が None のときは .md のメタデータや既定(14:ユーザ定義マルチ)で補う
# ------------------------------
CONTEST_TABLE = {
    "All JA":              {"key": "allja",  "kind": 1},
    "6m and down":         {"key": "6md",    "kind": 2},
    "全市全郡 (ACAG)":     {"key": "acag",   "kind": 4},
    "Field Day":           {"key": "fd",     "kind": 64},
    "All Asian DX":        {"key": "aa",     "kind": 8},
    "CQ WW DX":            {"key": "cqww",   "kind": 7},
    # .md参照で運用するローカル系（ContestKindは md に書く or 既定 14）
    "オール東北（.md参照）": {"key": "",       "kind": None},
    "オール宮城（.md参照）": {"key": "",       "kind": None},
    # 直指定
    "その他（番号指定）":    {"key": "",       "kind": None},
}

def parse_md_metadata(md_path: str):
    """
    .md の先頭付近からメタデータを抽出して返す。
    サポートする書式:
      - YAML風フロントマター:
          ---
          ContestKind: 14
          ContestKey: alltohoku
          ContestName: オール東北コンテスト
          ---
      - 行内キー=値 / キー: 値 形式（大文字小文字無視）:
          ContestKind=14, ContestKey=allmiyagi, ContestName=...
    戻り値: dict (例: {"ContestKind":14, "ContestKey":"alltohoku", "ContestName":"..." })
    """
    meta = {}
    if not md_path:
        return meta
    try:
        txt = Path(md_path).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        try:
            txt = Path(md_path).read_text(encoding="cp932", errors="ignore")
        except Exception:
            return meta
    head = txt[:2000]

    # YAML front matter
    m = re.search(r"^---\\s*(.*?)\\s*---", head, re.DOTALL | re.MULTILINE)
    block = m.group(1) if m else head

    # key: value OR key=value
    for line in block.splitlines():
        if not line.strip():
            continue
        if ":" in line:
            k, v = line.split(":", 1)
        elif "=" in line:
            k, v = line.split("=", 1)
        else:
            continue
        k = k.strip().lower()
        v = v.strip()
        if k == "contestkind":
            if re.match(r"^\\d+$", v):
                meta["ContestKind"] = int(v)
        elif k == "contestkey":
            meta["ContestKey"] = re.sub(r"[^A-Za-z0-9_\\-]", "", v)
        elif k == "contestname":
            meta["ContestName"] = v
    return meta

# ------------------------------
# Helpers for CP932 fixed strings
# ------------------------------
def enc_cp932_nul(s: str, size: int) -> bytes:
    b = (s or "").encode("cp932", errors="strict") + b"\\x00"
    if len(b) > size:
        raise ValueError(f"文字列が長すぎます（{len(b)}>{size}）: {s}")
    return b + b"\\x00" * (size - len(b))

# ------------------------------
# Trailer structure
# ------------------------------
@dataclass
class Trailer:
    ModeCurrent: int = 0
    Is001Style: int = 0
    DupePolicy: int = 0
    FreqCurrent: int = 0
    ContestKind: int = 0
    TwiceMinusOne: int = 0
    PointPhone: List[int] = field(default_factory=lambda: [1]*FREQNUM)
    PointCW: List[int] = field(default_factory=lambda: [1]*FREQNUM)
    ClubOpName: List[str] = field(default_factory=lambda: [""]*30)
    UserDefinedMultiPath: Optional[str] = None

    def pack(self) -> bytes:
        out = bytearray()
        out += struct.pack("<6H", self.ModeCurrent, self.Is001Style, self.DupePolicy,
                           self.FreqCurrent, self.ContestKind, self.TwiceMinusOne)
        out += struct.pack("<"+"H"*FREQNUM, *self.PointPhone)
        out += struct.pack("<"+"H"*FREQNUM, *self.PointCW)
        for name in (self.ClubOpName + [""]*30)[:30]:
            out += enc_cp932_nul(name, 20)
        if self.UserDefinedMultiPath:
            out += self.UserDefinedMultiPath.encode("cp932", errors="strict") + b"\\x00"
        return bytes(out)

# ------------------------------
# .lg8: create blank with trailer
# ------------------------------
def create_blank_lg8(out_path: Path, mode_code: int, band_code: int,
                     contest_kind: int = 1, is001: int = 0, dupe_policy: int = 0,
                     twice_minus_one: int = 0,
                     club_ops: Optional[List[str]] = None,
                     md_path: Optional[str] = None,
                     header_legacy_2bytes: bool = True) -> None:
    t = Trailer()
    t.ModeCurrent = int(mode_code)
    t.FreqCurrent = int(band_code)
    t.ContestKind = int(contest_kind)
    t.Is001Style = int(is001)
    t.DupePolicy = int(dupe_policy)
    t.TwiceMinusOne = int(twice_minus_one)
    if club_ops:
        t.ClubOpName = (club_ops + [""]*30)[:30]
    t.UserDefinedMultiPath = md_path

    data = bytearray()
    data += struct.pack("<H", 0)          # QsoCount=0
    if not header_legacy_2bytes:
        data += b"\\x00" * HEADER_EXTRA    # 14B padding (newer builds)
    # legacy mode leaves only 2B header
    data += t.pack()                       # trailer
    out_path.write_bytes(bytes(data))

# ------------------------------
# INI writer
# ------------------------------
def write_ini(ini_path: Path,
              urcnum_map: dict,
              club_ops: List[str],
              partial_path: Optional[str],
              cw_cq: Optional[str], cw_wpm: Optional[int],
              open_log_fullpath: Optional[str],
              user_md_path: Optional[str],
              startup_band_label: Optional[str] = None,
              startup_mode_label: Optional[str] = None) -> None:
    cfg = configparser.RawConfigParser()
    cfg.optionxform = str  # keep case
    if ini_path.exists():
        with ini_path.open("r", encoding="cp932", errors="replace") as f:
            cfg.read_file(f)

    # [UrCnum]
    if not cfg.has_section("UrCnum"):
        cfg.add_section("UrCnum")
    for band_label, num in urcnum_map.items():
        if num is None:
            continue
        cfg.set("UrCnum", band_label, num)

    # [CLUB]
    if not cfg.has_section("CLUB"):
        cfg.add_section("CLUB")
    for i in range(1, 31):
        val = club_ops[i-1] if i-1 < len(club_ops) else ""
        cfg.set("CLUB", f"OP{i}", val)

    # [Partial]
    if partial_path:
        if not cfg.has_section("Partial"):
            cfg.add_section("Partial")
        cfg.set("Partial", "Filename", partial_path)

    # [CW]
    if cw_cq or cw_wpm:
        if not cfg.has_section("CW"):
            cfg.add_section("CW")
        if cw_cq:
            cfg.set("CW", "CQ", cw_cq)
        if cw_wpm:
            cfg.set("CW", "WPM_DEF", str(cw_wpm))

    # 起動時のバンド/モード（v5互換: 一部CTESTWINビルドで参照）
    if (startup_band_label or startup_mode_label):
        if not cfg.has_section("CurrentData"):
            cfg.add_section("CurrentData")
        if startup_band_label:
            cfg.set("CurrentData", "BandLabel", startup_band_label)
        if startup_mode_label:
            cfg.set("CurrentData", "ModeLabel", startup_mode_label)

        if not cfg.has_section("Startup"):
            cfg.add_section("Startup")
        if startup_band_label:
            cfg.set("Startup", "Band", startup_band_label)
        if startup_mode_label:
            cfg.set("Startup", "Mode", startup_mode_label)

    # [CurrentData] 起動時に開くログ
    if open_log_fullpath:
        if not cfg.has_section("CurrentData"):
            cfg.add_section("CurrentData")
        cfg.set("CurrentData", "CloseFname", open_log_fullpath)

    # [Contest] ユーザー定義マルチの .md
    if user_md_path:
        if not cfg.has_section("Contest"):
            cfg.add_section("Contest")
        cfg.set("Contest", "UserContestMD", user_md_path)

    with ini_path.open("w", encoding="cp932", errors="strict") as f:
        cfg.write(f)

# ------------------------------
# GUI
# ------------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CTESTWIN Setup GUI (v8.3)")
        self.geometry("900x780")
        self.minsize(840, 660)
        self.create_widgets()

    def create_widgets(self):
        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True)

        self.page_basic = ttk.Frame(nb)
        self.page_ini = ttk.Frame(nb)
        self.page_ops = ttk.Frame(nb)
        nb.add(self.page_basic, text="1) 基本")
        nb.add(self.page_ini, text="2) INI 設定")
        nb.add(self.page_ops, text="3) OP名簿")

        # --- page_basic ---
        frm = ttk.Frame(self.page_basic, padding=12)
        frm.pack(fill=tk.BOTH, expand=True)

        # Vars
        self.var_year = tk.StringVar(value=str(datetime.now().year))
        self.var_year_auto = tk.BooleanVar(value=True)
        self.var_contest_name = tk.StringVar(value="Field Day")
        self.var_contest_key = tk.StringVar()    # 手入力 or mdから
        self.var_contest_kind = tk.StringVar()   # 手入力 or mdから
        self.var_band_label = tk.StringVar(value="7MHz")
        self.var_mode_label = tk.StringVar(value="SSB")
        self.var_md_path = tk.StringVar()
        self.var_out_dir = tk.StringVar(value=str(Path.cwd()))
        self.var_apply_startup = tk.BooleanVar(value=True)  # iniにも反映
        

        r=0
        # Year + auto
        ttk.Label(frm, text="西暦").grid(row=r, column=0, sticky="e")
        self.ent_year = ttk.Entry(frm, textvariable=self.var_year, width=10)
        self.ent_year.grid(row=r, column=1, sticky="w")
        ttk.Checkbutton(frm, text="自動（今年）", variable=self.var_year_auto,
                        command=self._toggle_year_auto).grid(row=r, column=1, sticky="e", padx=(0,120))

        # Contest dropdown
        ttk.Label(frm, text="大会").grid(row=r, column=2, sticky="e")
        self.cmb_contest = ttk.Combobox(frm, textvariable=self.var_contest_name,
                           values=list(CONTEST_TABLE.keys()), width=24, state="readonly")
        self.cmb_contest.grid(row=r, column=3, sticky="w")
        self.cmb_contest.bind("<<ComboboxSelected>>", lambda e: self._toggle_contest_extra())
        r+=1

        # Additional inputs shown for 特殊選択肢
        self.frm_other = ttk.Frame(frm)
        ttk.Label(self.frm_other, text="大会キー（ファイル名用）").grid(row=0, column=0, sticky="e")
        ttk.Entry(self.frm_other, textvariable=self.var_contest_key, width=18).grid(row=0, column=1, sticky="w")
        ttk.Label(self.frm_other, text="大会番号（ContestKind）").grid(row=0, column=2, sticky="e")
        ttk.Entry(self.frm_other, textvariable=self.var_contest_kind, width=8).grid(row=0, column=3, sticky="w")
        self.frm_other.grid(row=r, column=0, columnspan=4, sticky="we", pady=(0,6))
        self.frm_other.grid_remove()
        r += 1  # advance one row so Band/Mode won't collide with user-defined md block

        # Band/Mode
        ttk.Label(frm, text="周波数").grid(row=r, column=0, sticky="e")
        ttk.Combobox(frm, textvariable=self.var_band_label, values=list(BAND_TABLE_INV.keys()), width=12, state="readonly").grid(row=r, column=1, sticky="w")
        ttk.Label(frm, text="モード").grid(row=r, column=2, sticky="e")
        ttk.Combobox(frm, textvariable=self.var_mode_label, values=list(MODE_TABLE_INV.keys()), width=12, state="readonly").grid(row=r, column=3, sticky="w")
        r+=1

        # spacer (add one blank line between Band/Mode and user md path)
        frm.grid_rowconfigure(r, minsize=10)
        r+=1

        # md path
        ttk.Label(frm, text="ユーザー定義 .md（任意）").grid(row=r, column=0, sticky="e")
        ent_md = ttk.Entry(frm, textvariable=self.var_md_path, width=60)
        ent_md.grid(row=r, column=1, columnspan=3, sticky="we")
        ttk.Button(frm, text="参照", command=self.browse_md).grid(row=r, column=4, sticky="w")
        r+=1

        # out dir
        ttk.Label(frm, text="出力フォルダ").grid(row=r, column=0, sticky="e")
        ent_out = ttk.Entry(frm, textvariable=self.var_out_dir, width=60)
        ent_out.grid(row=r, column=1, columnspan=3, sticky="we")
        ttk.Button(frm, text="選択", command=self.browse_outdir).grid(row=r, column=4, sticky="w")
        r+=1

        # buttons
        ttk.Button(frm, text=".lg8 新規作成", command=self.create_lg8).grid(row=r, column=1, pady=6, sticky="w")
        ttk.Button(frm, text="この .lg8 を起動時に開くよう .ini へ設定", command=self.apply_currentdata).grid(row=r, column=3, pady=6, sticky="e")
        r+=1
        ttk.Button(frm, text="検査: .lg8 の周波数/モードを表示", command=self.inspect_lg8).grid(row=r, column=1, pady=2, sticky="w")
        r+=1


        # startup mirror
        ttk.Checkbutton(frm, text="起動時もこの周波数/モードに合わせる（iniにも反映）",
                        variable=self.var_apply_startup).grid(row=r, column=1, columnspan=3, sticky='w')

        for c in range(5): frm.grid_columnconfigure(c, weight=1)

        # --- page_ini ---
        fi = ttk.Frame(self.page_ini, padding=12)
        fi.pack(fill=tk.BOTH, expand=True)
        self.var_ini_path = tk.StringVar(value=str(Path.cwd()/ "Ctestwin.ini"))
        ttk.Label(fi, text="Ctestwin.ini").grid(row=0, column=0, sticky="e")
        ttk.Entry(fi, textvariable=self.var_ini_path, width=60).grid(row=0, column=1, sticky="we")
        ttk.Button(fi, text="参照", command=self.browse_ini).grid(row=0, column=2)

        # UrCnum map（バンド別 送信ナンバー）— 画像風 2カラム配置
        ttk.Label(fi, text="送信ナンバー既定 [UrCnum]（空欄可）").grid(row=1, column=0, columnspan=3, sticky="w", pady=(10,2))

        self.urcnum_vars = {}

        # 左列：index 0..10（1.9MHz〜144MHz）/ 右列：index 11..22（430MHz〜136kHz）
        items = list(BAND_TABLE.items())  # [(code,label), ...] 昇順
        left_items  = items[:11]
        right_items = items[11:]

        # コンテナフレームを2つ用意
        urc_frame = ttk.Frame(fi)
        urc_frame.grid(row=2, column=0, columnspan=3, sticky="we")
        left_fr = ttk.Frame(urc_frame)
        right_fr = ttk.Frame(urc_frame)
        left_fr.grid(row=0, column=0, sticky="nw", padx=(0, 24))
        right_fr.grid(row=0, column=1, sticky="ne")

        # 左列の部品
        for i, (code, label) in enumerate(left_items):
            v = tk.StringVar()
            self.urcnum_vars[label] = v
            ttk.Label(left_fr, text=label, width=8).grid(row=i, column=0, sticky="e", pady=1)
            ttk.Entry(left_fr, textvariable=v, width=16).grid(row=i, column=1, sticky="w", padx=(4, 6), pady=1)

        # 右列の部品
        for i, (code, label) in enumerate(right_items):
            v = tk.StringVar()
            self.urcnum_vars[label] = v
            ttk.Label(right_fr, text=label, width=8).grid(row=i, column=0, sticky="e", pady=1)
            ttk.Entry(right_fr, textvariable=v, width=16).grid(row=i, column=1, sticky="w", padx=(4, 0), pady=1)

        # 「右のナンバーを全周波数にセット」行（右側の直下に配置イメージ）
        self.var_urc_all = tk.StringVar()
        tools_fr = ttk.Frame(fi)
        tools_fr.grid(row=3, column=0, columnspan=3, sticky="w", pady=(8, 6))
        ttk.Button(tools_fr, text="右のナンバーを全周波数にセット", command=self.set_all_urcnum_from_right).grid(row=0, column=0, sticky="w")
        ttk.Entry(tools_fr, textvariable=self.var_urc_all, width=12).grid(row=0, column=1, sticky="w", padx=(8, 0))

        r = 4  # 次の行番号に進める

        ttk.Label(fi, text="パーシャルファイル [Partial:Filename]").grid(row=r, column=0, sticky="e")
        self.var_partial = tk.StringVar()
        ttk.Entry(fi, textvariable=self.var_partial, width=60).grid(row=r, column=1, sticky="we")
        ttk.Button(fi, text="参照", command=self.browse_partial).grid(row=r, column=2)
        r+=1

        ttk.Label(fi, text="CW 既定 [CW]").grid(row=r, column=0, sticky="e")
        self.var_cw_cq = tk.StringVar(value="CQ TEST")
        self.var_cw_wpm = tk.StringVar(value="22")
        ttk.Entry(fi, textvariable=self.var_cw_cq, width=40).grid(row=r, column=1, sticky="w")
        ttk.Entry(fi, textvariable=self.var_cw_wpm, width=6).grid(row=r, column=2, sticky="w")
        r+=1

        ttk.Label(fi, text="起動時に開くログ [CurrentData:CloseFname]").grid(row=r, column=0, sticky="e")
        self.var_open_log = tk.StringVar()
        ttk.Entry(fi, textvariable=self.var_open_log, width=60).grid(row=r, column=1, sticky="we")
        ttk.Button(fi, text="参照", command=self.browse_openlog).grid(row=r, column=2)
        r+=1

        ttk.Label(fi, text="ユーザー定義 .md 既定 [Contest:UserContestMD]").grid(row=r, column=0, sticky="e")
        self.var_user_md = tk.StringVar()
        ttk.Entry(fi, textvariable=self.var_user_md, width=60).grid(row=r, column=1, sticky="we")
        ttk.Button(fi, text="参照", command=self.browse_user_md).grid(row=r, column=2)
        r+=1

        ttk.Button(fi, text=".ini へ書き込み", command=self.write_ini_clicked).grid(row=r, column=1, pady=10)
        for c in range(3): fi.grid_columnconfigure(c, weight=1)

        # --- page_ops ---
        fo = ttk.Frame(self.page_ops, padding=12)
        fo.pack(fill=tk.BOTH, expand=True)
        ttk.Label(fo, text="クラブ局 OP 名簿（1行1名・最大30名） [CLUB:OP1..OP30]").pack(anchor="w")
        self.txt_ops = tk.Text(fo, height=18)
        self.txt_ops.pack(fill=tk.BOTH, expand=True)
        ttk.Button(fo, text="名簿を .ini に反映", command=self.apply_ops_to_ini).pack(pady=6)

        # init
        self._toggle_year_auto()

    # --- callbacks ---
    def _toggle_year_auto(self):
        if self.var_year_auto.get():
            self.var_year.set(str(datetime.now().year))
            self.ent_year.state(["disabled"])
        else:
            self.ent_year.state(["!disabled"])

    def _toggle_contest_extra(self):
        sel = self.var_contest_name.get()
        if sel in ("その他（番号指定）", "オール東北（.md参照）", "オール宮城（.md参照）"):
            self.frm_other.grid()
        else:
            self.frm_other.grid_remove()

    def browse_md(self):
        p = filedialog.askopenfilename(title="ユーザー定義 .md を選択", filetypes=[["MD","*.md"],["All","*.*"]])
        if p: self.var_md_path.set(p)

    def browse_outdir(self):
        p = filedialog.askdirectory(title="出力フォルダ")
        if p: self.var_out_dir.set(p)

    def browse_ini(self):
        p = filedialog.askopenfilename(title="Ctestwin.ini を選択", initialfile="Ctestwin.ini", filetypes=[["INI","*.ini"],["All","*.*"]])
        if p: self.var_ini_path.set(p)

    def browse_partial(self):
        p = filedialog.askopenfilename(title="パーシャルファイルを選択", filetypes=[["Partial","*.pck;*.scp;*.txt"],["All","*.*"]])
        if p: self.var_partial.set(p)

    def browse_openlog(self):
        p = filedialog.askopenfilename(title="起動時に開く .lg8 を選択", filetypes=[["LG8","*.lg8"],["All","*.*"]])
        if p: self.var_open_log.set(p)

    def browse_user_md(self):
        p = filedialog.askopenfilename(title="ユーザー定義 .md を選択", filetypes=[["MD","*.md"],["All","*.*"]])
        if p: self.var_user_md.set(p)

    def set_all_urcnum_from_right(self):
        """右側の小さなエントリに入れた番号を、全バンドに一括適用"""
        val = self.var_urc_all.get().strip()
        # 空なら何もしない（誤操作対策）
        if not val:
            messagebox.showwarning("未入力", "設定するナンバーを右の欄に入力してください。")
            return
        for _label, var in self.urcnum_vars.items():
            var.set(val)

    def _resolve_contest(self):
        """Combobox 選択 + .md メタデータ + 手入力から
        (key, kind) を決定し、未決定なら安全な既定値を補う。
        """
        sel = self.var_contest_name.get()
        info = CONTEST_TABLE.get(sel, {"key":"", "kind":None})
        key = info.get("key") or ""
        kind = info.get("kind")

        # .md メタデータ優先
        md_path = self.var_md_path.get().strip() or None
        md_meta = parse_md_metadata(md_path) if md_path else {}

        if md_meta.get("ContestKey"):
            key = md_meta["ContestKey"]
        if md_meta.get("ContestKind") is not None:
            try:
                kind = int(md_meta["ContestKind"])
            except Exception:
                pass

        # その他（番号指定）→ 手入力を使用
        if sel == "その他（番号指定）":
            key = self.var_contest_key.get().strip() or key
            kind_str = self.var_contest_kind.get().strip()
            if kind_str.isdigit():
                kind = int(kind_str)
            else:
                raise ValueError("『大会番号（ContestKind）』を数値で入力してください。")

        # kind 未確定ならユーザ定義マルチ 14 を既定に
        if kind is None:
            kind = 14

        # key 未指定なら ContestName or 選択名から生成
        if not key:
            base = md_meta.get("ContestName") or sel or "custom"
            key = re.sub(r"[^A-Za-z0-9_\\-]", "", base.lower()) or "custom"

        return key, kind, md_path

    def _build_filename(self, year: str, key: str, band_label: str) -> str:
        return f"{year}_{key}_{band_label}.lg8"

    def create_lg8(self):
        try:
            year = str(datetime.now().year) if self.var_year_auto.get() else self.var_year.get().strip()
            if not year:
                messagebox.showerror("入力不足", "西暦を入力してください。"); return

            key, kind, md_path = self._resolve_contest()

            band_label = self.var_band_label.get()
            mode_label = self.var_mode_label.get()
            band_code = BAND_TABLE_INV[band_label]
            mode_code = MODE_TABLE_INV[mode_label]
            file_name = self._build_filename(year, key, band_label)
            out_path = Path(self.var_out_dir.get())/file_name

            club_ops = [s.strip() for s in self.txt_ops.get("1.0","end").splitlines() if s.strip()][:30]

            create_blank_lg8(out_path, mode_code, band_code,
                             contest_kind=int(kind), md_path=md_path, club_ops=club_ops,
                             )
            messagebox.showinfo("完了", f".lg8 を作成しました:\\n{out_path}")
            self.var_open_log.set(str(out_path))
        except Exception as e:
            messagebox.showerror("エラー", str(e))

    def apply_currentdata(self):
        try:
            year = str(datetime.now().year) if self.var_year_auto.get() else self.var_year.get().strip()
            if not year:
                messagebox.showerror("入力不足", "西暦が未入力です。"); return
            key, _, _ = self._resolve_contest()
            band_label = self.var_band_label.get()
            file_name = self._build_filename(year, key, band_label)
            self.var_open_log.set(str(Path(self.var_out_dir.get())/file_name))
            messagebox.showinfo("設定", "[CurrentData:CloseFname] へ書く準備ができました。\\n『2) INI 設定』タブで書き込みを実行してください。")
        except Exception as e:
            messagebox.showerror("エラー", str(e))

    def write_ini_clicked(self):
        try:
            ini_path = Path(self.var_ini_path.get())
            urcnum_map = {label:self.urcnum_vars[label].get().strip() or None for label in self.urcnum_vars}
            club_ops = [s.strip() for s in self.txt_ops.get("1.0","end").splitlines() if s.strip()][:30]
            partial = self.var_partial.get().strip() or None
            cw_cq = self.var_cw_cq.get().strip() or None
            cw_wpm = int(self.var_cw_wpm.get().strip()) if self.var_cw_wpm.get().strip().isdigit() else None
            open_log = self.var_open_log.get().strip() or None
            user_md = self.var_user_md.get().strip() or None
            startup_band_label = self.var_band_label.get() if self.var_apply_startup.get() else None
            startup_mode_label = self.var_mode_label.get() if self.var_apply_startup.get() else None
            # USB直参照を避ける注意
            if partial and (partial.lower().startswith("e:\\\\") or partial.lower().startswith("f:\\\\")):
                if not messagebox.askyesno("確認", "パーシャルのパスがリムーバブルドライブに見えます。ローカルへコピー済みですか？\\n続行しますか？"):
                    return
            write_ini(ini_path, urcnum_map, club_ops, partial, cw_cq, cw_wpm, open_log, user_md,
                      startup_band_label=startup_band_label,
                      startup_mode_label=startup_mode_label)
            messagebox.showinfo("完了", f"Ctestwin.ini を更新しました:\\n{ini_path}")
        except Exception as e:
            messagebox.showerror("エラー", str(e))

    def apply_ops_to_ini(self):
        # ショートカット: INIパスが設定されていれば名簿だけ反映
        try:
            ini_path = Path(self.var_ini_path.get())
            if not ini_path:
                messagebox.showerror("エラー", "Ctestwin.ini のパスを指定してください。")
                return
            club_ops = [s.strip() for s in self.txt_ops.get("1.0","end").splitlines() if s.strip()][:30]
            # 読み出して CLUB だけ差し替え
            cfg = configparser.RawConfigParser(); cfg.optionxform = str
            if ini_path.exists():
                with ini_path.open("r", encoding="cp932", errors="replace") as f: cfg.read_file(f)
            if not cfg.has_section("CLUB"): cfg.add_section("CLUB")
            for i in range(1,31): cfg.set("CLUB", f"OP{i}", club_ops[i-1] if i-1<len(club_ops) else "")
            with ini_path.open("w", encoding="cp932", errors="strict") as f: cfg.write(f)
            messagebox.showinfo("完了", "[CLUB] 名簿を更新しました。")
        except Exception as e:
            messagebox.showerror("エラー", str(e))


    def inspect_lg8(self):
        path = filedialog.askopenfilename(title="検査する .lg8 を選択", filetypes=[["LG8","*.lg8"],["All","*.*"]])
        if not path:
            return
        try:
            b = Path(path).read_bytes()
            qso = struct.unpack("<H", b[:2])[0]
            off = 16 + qso*QSO_SIZE
            # レガシー（2Bヘッダ）の可能性も考慮
            if len(b) >= (2 + qso*QSO_SIZE + 12) and len(b) < off + 12:
                off = 2 + qso*QSO_SIZE
            vals = struct.unpack("<6H", b[off:off+12])
            mode,_,_,freq,kind,_ = vals
            mode_label = MODE_TABLE.get(mode, f"#{mode}")
            band_label = BAND_TABLE.get(freq, f"#{freq}")
            messagebox.showinfo("解析結果", f"QSO数: {qso}\nMode={mode} ({mode_label})\nFreq={freq} ({band_label})\nContestKind={kind}\nTrailer@{off} (0x{off:02X})")
        except Exception as e:
            messagebox.showerror("エラー", f".lg8 解析に失敗: {e}")

if __name__ == "__main__":
    app = App()
    app.mainloop()
