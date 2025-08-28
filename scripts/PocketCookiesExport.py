#!/usr/bin/env python3
import json
import re
import time
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Simple GUI
import tkinter as tk
from tkinter import messagebox

LOGIN_URL = "https://pocketoption.com/en/login/"
DESKTOP = Path.home() / "Desktop"
OUT_JSON = DESKTOP / "pocket_ssid.json"


def build_ssid(cookies_list):
    ci = next((c for c in cookies_list if c.get("name") == "ci_session"), None)
    autologin = next((c for c in cookies_list if c.get("name") == "autologin"), None)
    platform = next((c for c in cookies_list if c.get("name") == "platform_type"), None)

    if not ci or not autologin:
        return None, 0, None

    raw = urllib.parse.unquote(autologin.get("value", ""))
    m = re.search(r'"user_id";(?:s:\\d+:"|i:)(\\d+)', raw)
    uid = int(m.group(1)) if m else None

    is_demo = 1 if (platform and str(platform.get("value", "")).strip() == "1") else 0
    session_val = urllib.parse.unquote(ci.get("value", ""))

    expiry_epoch = ci.get("expiry")
    expiry_dt = (
        datetime.fromtimestamp(int(expiry_epoch), tz=timezone.utc)
        if expiry_epoch
        else datetime.now(timezone.utc) + timedelta(days=7)
    )

    payload = {"session": session_val, "isDemo": is_demo, "uid": uid, "platform": 1}
    ssid = f'42["auth",{json.dumps(payload, separators=(",", ":"))}]'
    return ssid, is_demo, expiry_dt


def start_browser():
    chrome_options = Options()
    chrome_options.add_argument("--window-size=1280,800")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])

    service = Service()  # Selenium Manager подберёт драйвер автоматически
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_page_load_timeout(60)
    driver.get(LOGIN_URL)
    return driver


def export_now(driver: webdriver.Chrome) -> bool:
    try:
        # Немного подождём чтобы страница точно обновила cookies
        time.sleep(3)
        cookies = driver.get_cookies()
        norm = []
        for c in cookies:
            item = {"name": c.get("name"), "value": c.get("value")}
            if c.get("expiry") is not None:
                try:
                    item["expiry"] = int(c.get("expiry"))
                except Exception:
                    pass
            norm.append(item)

        ssid, is_demo, expiry_dt = build_ssid(norm)
        if not ssid:
            messagebox.showerror("Pocket Export", "Не найдено 'ci_session' или 'autologin'. Убедитесь, что вы вошли и отметили 'Remember me'.")
            return False

        DESKTOP.mkdir(parents=True, exist_ok=True)
        data = {"ssid": ssid, "cookies": norm, "expiry": expiry_dt.isoformat()}
        OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        messagebox.showinfo("Pocket Export", f"Файл сохранён:\n{OUT_JSON}")
        return True
    except Exception as e:
        messagebox.showerror("Pocket Export", f"Ошибка экспорта: {e}")
        return False


def main():
    driver = start_browser()

    # Небольшое окно управления
    root = tk.Tk()
    root.title("Pocket Cookies Export")
    root.geometry("420x200")
    root.resizable(False, False)

    instructions = (
        "1) Войдите в аккаунт PocketOption в открывшемся окне Chrome.\n"
        "2) Отметьте 'Remember me'.\n"
        "3) После загрузки кабинета нажмите кнопку ниже."
    )

    lbl = tk.Label(root, text=instructions, justify=tk.LEFT, wraplength=400)
    lbl.pack(padx=12, pady=12)

    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=8)

    def on_confirm():
        ok = export_now(driver)
        try:
            driver.quit()
        except Exception:
            pass
        if ok:
            root.destroy()
        else:
            # оставим окно открытым для повторной попытки
            pass

    def on_cancel():
        try:
            driver.quit()
        except Exception:
            pass
        root.destroy()

    btn_ok = tk.Button(btn_frame, text="Я вошёл в аккаунт", width=22, command=on_confirm)
    btn_ok.grid(row=0, column=0, padx=6)

    btn_cancel = tk.Button(btn_frame, text="Отмена", width=12, command=on_cancel)
    btn_cancel.grid(row=0, column=1, padx=6)

    # Дополнительная страховка: ждать до 2 минут видимость body (не блокирует GUI)
    def check_loaded():
        try:
            WebDriverWait(driver, 0.1).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        except Exception:
            pass
        # переустановим таймер; просто держим цикл событий
        root.after(500, check_loaded)

    root.after(500, check_loaded)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main()) 