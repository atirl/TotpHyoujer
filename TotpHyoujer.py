#=============================================
# TOTP表示ツール
# 2024/08/28 atirl　作成
# 2024/08/29 atirl　小型モード追加
# 2026/10/22 公開用対応（秘密鍵を外部ファイル選択式に）
#=============================================

import configparser
import os
import random
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import pyotp
import pyperclip

APP_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(APP_DIR, "config.txt")

def load_config():
    """設定からウインドウタイトルと鍵のパスを読み込む"""
    config = configparser.ConfigParser()
    config_path = None

    # UTF-8を先に使ってデコードエラーならCP932試行
    for encoding in ("utf-8-sig", "cp932"):
        try:
            if os.path.isfile(CONFIG_PATH):
                config.read(CONFIG_PATH, encoding=encoding)
                config_path = CONFIG_PATH
            break
        except UnicodeDecodeError:
            continue

    title = ""
    secret_path = ""

    if config_path and config.has_section("settings"):
        title = config.get("settings", "title", fallback="")
        secret_path = config.get("settings", "secret_path", fallback="")

    return title, secret_path


class TOTPViewer:
    def __init__(self):
        self.title_text, self.secret_path = load_config()
        self.totp = None
        self.after_id = None
        self.current_code = ""
        self.urgent_message = ""
        self.desperate_message = ""
        self.is_compact = False
        self.settings_window = None

        self.window = tk.Tk()
        self.window.iconbitmap(
            os.path.join(os.path.dirname(__file__), "blue.ico")
        )
        self.window.title(self.title_text if self.title_text else "Verification Code")
        self.window.geometry("300x180")
        self.window.resizable(False, False)

        # 画面中央に配置
        self.window.update_idletasks()
        w = self.window.winfo_width()
        h = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (w // 2)
        y = (self.window.winfo_screenheight() // 2) - (h // 2)
        self.window.geometry(f"{w}x{h}+{x}+{y}")

        # メインコンテナ
        self.main_container = tk.Frame(self.window)
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # ゲージの上のメッセージ
        self.title_var = tk.StringVar(value="Verification Code")
        self.title_label = tk.Label(
            self.main_container,
            textvariable=self.title_var,
            font=("Meiryo", 11)
        )
        self.title_label.pack(pady=(18, 4))

        # コード表示
        self.code_var = tk.StringVar()
        self.code_label = tk.Label(
            self.main_container,
            textvariable=self.code_var,
            font=("Consolas", 36, "bold"),
            fg="#1a6fc4"
        )
        self.code_label.pack()

        # バー用のキャンバス
        self.canvas = tk.Canvas(
            self.main_container,
            width=220,
            height=20,
            highlightthickness=0
        )
        self.canvas.pack(pady=(8, 0))
        self.progress_bar = self.canvas.create_rectangle(
            0, 0, 220, 20, fill="#00ff00", outline=""
        )

        # ボタンフレーム（通常用）
        self.btn_frame_normal = tk.Frame(self.main_container)
        self.btn_frame_normal.pack(pady=(10, 0))

        self.compact_btn = tk.Button(
            self.btn_frame_normal,
            text="小型前面",
            width=10,
            command=self.toggle_compact
        )
        self.compact_btn.grid(row=0, column=0, padx=5, ipady=4)

        self.copy_btn = tk.Button(
            self.btn_frame_normal,
            text="コピー",
            width=10,
            command=self.copy_code
        )
        self.copy_btn.grid(row=0, column=1, padx=5, ipady=4)

        self.settings_btn = tk.Button(
            self.btn_frame_normal,
            text="設定",
            width=10,
            command=self.open_settings
        )
        self.settings_btn.grid(row=0, column=2, padx=5, ipady=4)

        # ボタンフレーム（小型用）
        self.btn_frame_compact = tk.Frame(self.main_container)

        self.expand_btn = tk.Button(
            self.btn_frame_compact,
            text="拡大",
            width=6,
            command=self.toggle_compact,
            font=("Meiryo", 8)
        )
        self.expand_btn.grid(row=0, column=0, padx=2, ipady=2)

        self.copy_btn_compact = tk.Button(
            self.btn_frame_compact,
            text="コピー",
            width=6,
            command=self.copy_code,
            font=("Meiryo", 8)
        )
        self.copy_btn_compact.grid(row=0, column=1, padx=2, ipady=2)

        self.settings_btn_compact = tk.Button(
            self.btn_frame_compact,
            text="設定",
            width=6,
            command=self.open_settings,
            font=("Meiryo", 8)
        )
        self.settings_btn_compact.grid(row=0, column=2, padx=2, ipady=2)

        # ×ボタンで閉じる
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

        # 認証鍵の読み込みと初回更新
        self.load_totp()
        self.update_code()
        self.update_bar()
        self.window.mainloop()

    def load_totp(self):
        """鍵ファイルを読み込んでTOTPを準備"""
        self.totp = None

        if not self.secret_path or not os.path.isfile(self.secret_path):
            return

        try:
            with open(self.secret_path, "r", encoding="utf-8-sig") as secret_file:
                secret = secret_file.read().strip()

            if not secret:
                return

            self.totp = pyotp.TOTP(secret)

            # 鍵の形式を簡易確認
            self.totp.now()
        except (OSError, UnicodeError, ValueError, TypeError):
            self.totp = None

    def toggle_compact(self):
        """小型/通常モードの切り替え"""
        if self.is_compact:
            self.is_compact = False
            self.window.geometry("300x180")
            self.window.attributes("-topmost", False)

            self.btn_frame_compact.pack_forget()
            self.code_label.config(font=("Consolas", 36, "bold"))

            self.title_label.pack(pady=(18, 4))
            self.canvas.pack(pady=(8, 0))
            self.btn_frame_normal.pack(pady=(10, 0))
        else:
            self.is_compact = True
            self.window.geometry("200x70")
            self.window.attributes("-topmost", True)

            self.title_label.pack_forget()
            self.canvas.pack_forget()
            self.btn_frame_normal.pack_forget()

            self.code_label.config(font=("Consolas", 18, "bold"))
            self.btn_frame_compact.pack(pady=(5, 5))

    def update_code(self):
        if self.totp is None:
            self.current_code = ""
            self.code_var.set("鍵ファイルを確認してください")
            self.code_label.config(font=("Meiryo", 14, "bold"))
        else:
            try:
                new_code = self.totp.now()
                self.current_code = new_code
                self.code_var.set(new_code)
                self.code_label.config(font=("Consolas", 36, "bold"))
            except Exception:
                self.totp = None
                self.current_code = ""
                self.code_var.set("鍵ファイルを確認してください")
                self.code_label.config(font=("Meiryo", 14, "bold"))

        self.after_id = self.window.after(1000, self.update_code)

    def update_bar(self):
        # 小型モード時はバー更新をスキップ
        if self.is_compact:
            self.window.after(100, self.update_bar)
            return

        remain = 30 - (time.time() % 30)

        #メッセージ更新
        if remain <= 0.5:
            if self.desperate_message == "":
                desperate_messages = ["あ……", "もう駄目だ…", "くっ…！"]
                self.desperate_message = random.choice(desperate_messages)
            self.title_var.set(self.desperate_message)
            self.title_label.config(fg="#8b0000", font=("Meiryo", 11, "bold"))
        elif remain <= 5:
            if self.urgent_message == "":
                messages = ["早くしろ……！！", "もう…間に合わん…", "急げ！急がないと……"]
                self.urgent_message = random.choice(messages)
            self.title_var.set(self.urgent_message)
            self.title_label.config(fg="red", font=("Meiryo", 11, "bold"))
        else:
            self.title_var.set("Verification Code")
            self.title_label.config(fg="black", font=("Meiryo", 11))
            self.urgent_message = ""
            self.desperate_message = ""

        # プログレスバーの幅
        bar_width = (remain / 30) * 220
        self.canvas.coords(self.progress_bar, 0, 0, bar_width, 20)

        # 色
        if remain > 15:
            ratio = (30 - remain) / 15
            r = int(255 * ratio)
            g = 255
            b = 0
        else:
            ratio = (15 - remain) / 15
            r = 255
            g = int(255 * (1 - ratio))
            b = 0

        color = f"#{r:02x}{g:02x}{b:02x}"
        self.canvas.itemconfig(self.progress_bar, fill=color)

        self.window.after(100, self.update_bar)

    def open_settings(self):
        """設定画面を開く"""
        if self.settings_window is not None and self.settings_window.winfo_exists():
            self.settings_window.lift()
            self.settings_window.focus_force()
            return

        dialog = tk.Toplevel(self.window)
        self.settings_window = dialog
        dialog.title("設定")
        dialog.resizable(False, False)
        dialog.transient(self.window)
        dialog.grab_set()

        title_var = tk.StringVar(value=self.title_text)
        path_var = tk.StringVar(value=self.secret_path)

        tk.Label(dialog, text="ウィンドウ名：").grid(
            row=0, column=0, padx=(12, 6), pady=(12, 6), sticky="w"
        )
        title_entry = ttk.Entry(dialog, textvariable=title_var, width=38)
        title_entry.grid(row=0, column=1, columnspan=2, padx=(0, 12), pady=(12, 6))

        tk.Label(dialog, text="秘密鍵のパス：").grid(
            row=1, column=0, padx=(12, 6), pady=6, sticky="w"
        )
        path_entry = ttk.Entry(dialog, textvariable=path_var, width=30)
        path_entry.grid(row=1, column=1, padx=(0, 6), pady=6)

        def select_secret_file():
            selected = filedialog.askopenfilename(
                title="認証鍵ファイルを選択",
                filetypes=[
                    ("テキストファイル", "*.txt"),
                    ("すべてのファイル", "*.*")
                ],
                parent=dialog
            )
            if selected:
                path_var.set(selected)

        ttk.Button(
            dialog,
            text="参照...",
            command=select_secret_file
        ).grid(row=1, column=2, padx=(0, 12), pady=6)

        def save_config():
            config = configparser.ConfigParser()
            config["settings"] = {
                "title": title_var.get(),
                "secret_path": path_var.get()
            }

            try:
                with open(CONFIG_PATH, "w", encoding="utf-8") as config_file:
                    config.write(config_file)
            except OSError as error:
                messagebox.showerror(
                    "保存エラー",
                    f"設定ファイルを保存できませんでした。\n{error}",
                    parent=dialog
                )
                return

        def apply_and_close():
            self.title_text = title_var.get()
            self.secret_path = path_var.get()
            self.window.title(
                self.title_text if self.title_text else "Verification Code"
            )
            self.load_totp()
            self.update_code()
            dialog.destroy()
            self.settings_window = None

        def on_save():
            #設定適用＋保存
            save_config()
            if os.path.isfile(CONFIG_PATH):
                apply_and_close()

        def on_ok():
            #設定適用のみ
            apply_and_close()

        def on_cancel():
            dialog.destroy()
            self.settings_window = None

        button_frame = ttk.Frame(dialog)
        button_frame.grid(
            row=2, column=0, columnspan=3, pady=(8, 12)
        )

        ttk.Button(button_frame, text="保存", command=on_save).grid(
            row=0, column=0, padx=5
        )
        ttk.Button(button_frame, text="OK", command=on_ok).grid(
            row=0, column=1, padx=5
        )
        ttk.Button(button_frame, text="キャンセル", command=on_cancel).grid(
            row=0, column=2, padx=5
        )

        dialog.protocol("WM_DELETE_WINDOW", on_cancel)
        title_entry.focus_set()

    def copy_code(self):
        if not self.current_code:
            return

        try:
            pyperclip.copy(self.current_code)
        except pyperclip.PyperclipException:
            return

        if self.is_compact:
            self.copy_btn_compact.config(text="完了", fg="green")
            self.window.after(
                2000,
                lambda: self.copy_btn_compact.config(text="コピー", fg="black")
            )
        else:
            self.copy_btn.config(text="コピー完了", fg="green")
            self.window.after(
                2000,
                lambda: self.copy_btn.config(text="コピー", fg="black")
            )

    def on_close(self):
        if self.after_id:
            self.window.after_cancel(self.after_id)

        if self.settings_window is not None and self.settings_window.winfo_exists():
            self.settings_window.destroy()

        self.window.destroy()


if __name__ == "__main__":
    TOTPViewer()