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
    m = re.search(r'"user_id";(?:s:\d+:"|i:)(\d+)', raw)
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


def main():
    print("Открываю Chrome для авторизации на PocketOption...")
    chrome_options = Options()
    chrome_options.add_argument("--window-size=1280,800")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])

    service = Service()  # Selenium Manager подберёт драйвер автоматически
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_page_load_timeout(60)

    try:
        driver.get(LOGIN_URL)
        print("Войдите в аккаунт и отметьте 'Remember me'. После входа подождите, пока загрузится кабинет.")
        # Ждём появления признака рабочей области, но ограничим максимальным временем ожидания
        try:
            WebDriverWait(driver, 120).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        except Exception:
            pass

        print("Жду несколько секунд для фиксации cookies...")
        time.sleep(5)

        cookies = driver.get_cookies()
        # Нормализуем формат под запись в единый JSON
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
            print("❌ Не найдено 'ci_session' или 'autologin'. Проверьте, что Remember me отмечен.")
            return 2

        data = {
            "ssid": ssid,
            "cookies": norm,
            "expiry": expiry_dt.isoformat(),
        }
        OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"✅ Сохранено: {OUT_JSON}")
        print("Теперь отправьте этот файл боту (кнопка 'Загрузить JSON').")
        return 0
    finally:
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main()) 