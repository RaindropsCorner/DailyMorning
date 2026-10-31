# -*- coding: UTF-8 -*-
"""每日早安推送。

2026-11-01 健壮性修复：
  * 金句改为多源降级（词霸 → 一言 → 今日诗词 → 本地兜底），
    词霸接口返回非 JSON 时不再让整次推送崩掉；
  * 天气、金句均加超时与异常兜底，任一外部接口失败仍会推送其余内容；
  * 配置支持从环境变量读取（WX_APP_ID / WX_APP_SECRET），便于改用 Actions Secrets；
  * 去掉 Linux 上无意义的 os.system("pause")；
  * 单个用户推送失败不再中断其他用户的推送。
"""
import argparse
import json
import os
import random
import sys
from datetime import date, datetime
from time import localtime

import requests
from requests import get, post

import cityinfo
import frames
from zhdate import ZhDate

# (连接超时, 读取超时)
REQUEST_TIMEOUT = (3, 8)

ICIBA_URL = "https://open.iciba.com/dsapi/"
HITOKOTO_URL = "https://v1.hitokoto.cn/?c=i&c=k&encode=json"
JINRISHICI_URL = "https://v1.jinrishici.com/all.json"

USER_AGENT = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# 在线金句源全部不可用时使用的本地兜底（中文, 英文）
FALLBACK_QUOTES = [
    ("愿你今日所遇皆为温柔", "May today treat you gently."),
    ("慢慢来，比较快", "Slow is smooth, smooth is fast."),
    ("生活明朗，万物可爱", "The world is bright, and everything is lovely."),
    ("心之所向，素履以往", "Follow your heart, even in plain shoes."),
    ("保持热爱，奔赴山海", "Keep loving, keep moving toward the vast."),
    ("今天也要好好吃饭", "Remember to eat well today."),
    ("愿你眼里有光，心中有暖", "May your eyes hold light, your heart hold warmth."),
    ("不必追赶，自有花期", "No need to rush — everything blooms in its own time."),
    ("晴时有风，雨时有伞", "Wind on sunny days, an umbrella when it rains."),
    ("愿你被这个世界温柔以待", "May the world be gentle with you."),
    ("向阳而生，逐光而行", "Grow toward the sun, walk toward the light."),
    ("所有的美好，都在路上", "All good things are on their way."),
]


def get_color():
    # 获取随机颜色（微信已不支持自定义颜色，仅保留以兼容旧模板）
    get_colors = lambda n: list(map(lambda i: "#" + "%06x" % random.randint(0, 0xFFFFFF), range(n)))
    color_list = get_colors(100)
    return random.choice(color_list)


def get_access_token(app_id, app_secret):
    post_url = ("https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={}&secret={}"
                .format(app_id, app_secret))
    try:
        payload = get(post_url, timeout=REQUEST_TIMEOUT).json()
        return payload["access_token"]
    except KeyError:
        print("获取access_token失败，请检查app_id和app_secret是否正确")
        print("接口返回：{}".format(payload))
        sys.exit(1)


def get_weather(province, city):
    # 城市id
    try:
        city_id = cityinfo.cityInfo[province][city]["AREAID"]
    except KeyError:
        raise ValueError("推送消息失败，请检查省份或城市是否正确")

    t = int(round(datetime.now().timestamp() * 1000))
    headers = {
        "Referer": "http://www.weather.com.cn/weather1d/{}.shtml".format(city_id),
        'User-Agent': USER_AGENT
    }
    url = "http://d1.weather.com.cn/dingzhi/{}.html?_={}".format(city_id, t)
    response = get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    response.encoding = "utf-8"
    response_data = response.text.split(";")[0].split("=")[-1]
    response_json = json.loads(response_data)
    weatherinfo = response_json["weatherinfo"]
    weather = weatherinfo["weather"]
    # 微信模板消息会把 ℃ 滤掉（实测），换成 °C 才能完整显示
    temp = weatherinfo["temp"].replace("℃", "°C")
    tempn = weatherinfo["tempn"].replace("℃", "°C")
    return weather, temp, tempn


def get_birthday(birthday, year, today):
    birthday_year = birthday.split("-")[0]
    # 判断是否为农历生日
    if birthday_year[0] == "r":
        r_mouth = int(birthday.split("-")[1])
        r_day = int(birthday.split("-")[2])
        # 今年生日
        birthday = ZhDate(year, r_mouth, r_day).to_datetime().date()
        year_date = birthday
    else:
        # 获取国历生日的今年对应月和日
        birthday_month = int(birthday.split("-")[1])
        birthday_day = int(birthday.split("-")[2])
        # 今年生日
        year_date = date(year, birthday_month, birthday_day)
    # 计算生日年份，如果还没过，按当年减，如果过了需要+1
    if today > year_date:
        if birthday_year[0] == "r":
            # 获取农历明年生日的月和日
            r_last_birthday = ZhDate((year + 1), r_mouth, r_day).to_datetime().date()
            birth_date = date((year + 1), r_last_birthday.month, r_last_birthday.day)
        else:
            birth_date = date((year + 1), birthday_month, birthday_day)
        birth_day = str(birth_date.__sub__(today)).split(" ")[0]
    elif today == year_date:
        birth_day = 0
    else:
        birth_date = year_date
        birth_day = str(birth_date.__sub__(today)).split(" ")[0]
    return birth_day


def _split_two_lines(text, limit=20):
    """把一段话拆成两行，模板里分别占 note_xx 与 note_xx2。"""
    text = (text or "").strip()
    text = " ".join(text.split())
    if len(text) > limit:
        return text[:limit], text[limit:]
    return text, ""


def _fetch_iciba(session):
    response = session.get(ICIBA_URL, headers={'User-Agent': USER_AGENT}, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    data = response.json()
    note_ch = (data.get("note") or "").strip()
    note_en = (data.get("content") or "").strip()
    if not note_ch and not note_en:
        raise ValueError("词霸返回内容为空")
    return note_ch, note_en


def _fetch_hitokoto(session):
    response = session.get(HITOKOTO_URL, headers={'User-Agent': USER_AGENT}, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    data = response.json()
    note_ch = (data.get("hitokoto") or "").strip()
    if not note_ch:
        raise ValueError("一言返回内容为空")
    return note_ch, ""


def _fetch_jinrishici(session):
    response = session.get(JINRISHICI_URL, headers={'User-Agent': USER_AGENT}, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    data = response.json()
    note_ch = (data.get("content") or "").strip()
    if not note_ch:
        raise ValueError("今日诗词返回内容为空")
    return note_ch, ""


def _english_of_the_day():
    """在线源不提供英文时，按日期取一句固定的英文短句（当天稳定）。"""
    _, english = FALLBACK_QUOTES[date.today().toordinal() % len(FALLBACK_QUOTES)]
    return english


def get_ciba():
    """获取每日金句，多源降级，任何情况下都返回 4 个可直接塞进模板的字符串。"""
    session = requests.Session()
    sources = (
        ("词霸", _fetch_iciba),
        ("一言", _fetch_hitokoto),
        ("今日诗词", _fetch_jinrishici),
    )
    for name, fetch in sources:
        try:
            note_ch, note_en = fetch(session)
        except Exception as exc:  # 网络错误、超时、非 JSON、字段缺失都走这里
            print("[warn] 金句源「{}」不可用：{!r}".format(name, exc))
            continue
        if not note_en:
            note_en = _english_of_the_day()
        return _split_two_lines(note_ch) + _split_two_lines(note_en)

    print("[warn] 所有在线金句源均不可用，改用本地兜底金句")
    note_ch, note_en = FALLBACK_QUOTES[date.today().toordinal() % len(FALLBACK_QUOTES)]
    return _split_two_lines(note_ch) + _split_two_lines(note_en)


def send_message(to_user, access_token, city_name, weather, max_temperature, min_temperature,
                 note_ch, note_ch2, note_en, note_en2, config, dry_run=False):
    url = "https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={}".format(access_token)
    week_list = ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"]
    year = localtime().tm_year
    month = localtime().tm_mon
    day = localtime().tm_mday
    today = datetime.date(datetime(year=year, month=month, day=day))
    week = week_list[today.isoweekday() % 7]

    # 在一起的天数（未配置 love_date 时显示占位符）
    love_days = "-"
    if config.get("love_date"):
        love_year, love_month, love_day = (int(x) for x in config["love_date"].split("-"))
        love_date = date(love_year, love_month, love_day)
        love_days = str(today.__sub__(love_date)).split(" ")[0]

    # 获取所有生日数据
    birthdays = {}
    for k, v in config.items():
        if k[0:5] == "birth":
            birthdays[k] = v

    data = {
        "touser": to_user,
        "template_id": config["template_id"],
        "url": "http://weixin.qq.com/download",
        "topcolor": "#FF0000",
        "data": {
            "date": {
                "value": "{} {}".format(today, week),
                "color": get_color()
            },
            "city": {
                "value": city_name,
                "color": get_color()
            },
            "weather": {
                "value": weather,
                "color": get_color()
            },
            "min_temperature": {
                "value": min_temperature,
                "color": get_color()
            },
            "max_temperature": {
                "value": max_temperature,
                "color": get_color()
            },
            "love_day": {
                "value": love_days,
                "color": get_color()
            },
            "note_en": {
                "value": note_en,
                "color": get_color()
            },
            "note_en2": {
                "value": note_en2,
                "color": get_color()
            },
            "note_ch": {
                "value": note_ch,
                "color": get_color()
            },
            "note_ch2": {
                "value": note_ch2,
                "color": get_color()
            }
        }
    }

    for key, value in birthdays.items():
        try:
            birth_day = get_birthday(value["birthday"], year, today)
        except Exception as exc:
            print("[warn] 生日「{}」解析失败：{!r}".format(value.get("name"), exc))
            continue
        if birth_day == 0:
            birthday_data = "今天{}生日哦，祝{}生日快乐！".format(value["name"], value["name"])
        else:
            birthday_data = "距离{}的生日还有{}天".format(value["name"], birth_day)
        # 将生日数据插入data
        data["data"][key] = {"value": birthday_data, "color": get_color()}

    headers = {
        'Content-Type': 'application/json',
        'User-Agent': USER_AGENT
    }
    if dry_run:
        print("=== dry-run 消息体 ===")
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return True

    try:
        response = post(url, headers=headers, json=data, timeout=REQUEST_TIMEOUT).json()
    except Exception as exc:
        print("推送消息失败：{} 请求异常 {!r}".format(to_user, exc))
        return False

    errcode = response.get("errcode", -1)
    if errcode == 40037:
        print("推送消息失败，请检查模板id是否正确")
    elif errcode == 40036:
        print("推送消息失败，请检查模板id是否为空")
    elif errcode == 40003:
        print("推送消息失败，请检查微信号是否正确")
    elif errcode == 0:
        print("推送消息成功 -> {}".format(to_user))
        return True
    else:
        print("推送消息失败 -> {}：{}".format(to_user, response))
    return False


def load_config():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    try:
        with open(path, encoding="utf-8") as f:
            config = json.load(f)
    except FileNotFoundError:
        print("推送消息失败，请检查 config.json 是否与程序位于同一路径")
        sys.exit(1)
    except json.JSONDecodeError as exc:
        print("推送消息失败，请检查配置文件格式是否正确：{}".format(exc))
        sys.exit(1)

    # 环境变量优先，其次才是配置文件（便于把密钥放 Actions Secrets）
    config["app_id"] = os.environ.get("WX_APP_ID") or config.get("app_id", "")
    config["app_secret"] = os.environ.get("WX_APP_SECRET") or config.get("app_secret", "")
    return config


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LAST_PUSH_FILE = os.path.join(BASE_DIR, ".last_push")


def main():
    parser = argparse.ArgumentParser(description="每日早安微信推送")
    parser.add_argument("--dry-run", action="store_true", help="只打印消息体，不真正发送")
    parser.add_argument("--force", action="store_true", help="今天已推送过也强制再发一次")
    parser.add_argument("--frame", type=int, help="强制指定第几套装饰框（1~30），预览时用")
    parser.add_argument("--preview-frames", action="store_true", help="打印全部 30 套装饰框后退出")
    parser.add_argument("--only", type=int, metavar="N",
                        help="只发给 config.json 里第 N 个收件人（从 0 开始），测试用")
    args = parser.parse_args()

    if args.preview_frames:
        frames.preview()
        return 0

    config = load_config()
    if not config.get("app_id") or not config.get("app_secret"):
        print("推送消息失败：未找到 app_id / app_secret。")
        print("请在 config.json 中填写，或设置环境变量 WX_APP_ID / WX_APP_SECRET。")
        return 1

    today = date.today().isoformat()
    # 幂等：同一天只推一次，调度重复触发也不会连发
    if not args.dry_run and not args.force and os.path.exists(LAST_PUSH_FILE):
        with open(LAST_PUSH_FILE, encoding="utf-8") as f:
            if f.read().strip() == today:
                print("今天（{}）已经推送过了，跳过。要强制重发请加 --force".format(today))
                return 0

    accessToken = "DRY_RUN" if args.dry_run else get_access_token(config["app_id"], config["app_secret"])
    users = config["user"]
    if args.only is not None:
        if not 0 <= args.only < len(users):
            print("--only 超出范围：config.json 里共 {} 个收件人（0~{}）".format(len(users), len(users) - 1))
            return 2
        users = [users[args.only]]
        print("测试模式：只发给第 {} 个收件人 {}".format(args.only, users[0]))
    province, city = config["province"], config["city"]

    try:
        weather, max_temperature, min_temperature = get_weather(province, city)
    except Exception as exc:
        print("[warn] 天气获取失败，本次推送使用占位内容：{!r}".format(exc))
        weather, max_temperature, min_temperature = "暂时无法获取", "-", "-"

    note_ch, note_ch2, note_en, note_en2 = get_ciba()

    # 套上当天轮换的装饰框。模板里 note_ch 与 note_ch2 是拼接渲染的，
    # 所以装饰加在整段文字的头尾，折行落在中间，不会把框切坏。
    if config.get("frame_enabled", True):
        idx, frame_name, _, _ = frames.pick(date.today(), args.frame)
        framed, _ = frames.wrap(note_ch + note_ch2, date.today(), args.frame)
        if framed:
            note_ch, note_ch2 = _split_two_lines(framed)
        print("今日装饰框：第 {} 套「{}」".format(idx, frame_name))

    failed = 0
    for user in users:
        ok = send_message(user, accessToken, city, weather, max_temperature, min_temperature,
                          note_ch, note_ch2, note_en, note_en2, config, dry_run=args.dry_run)
        if not ok:
            failed += 1

    print("本次推送完成：成功 {} / {}，失败 {}".format(len(users) - failed, len(users), failed))

    if args.dry_run:
        print("（dry-run：未真正发送，也未记录推送日期）")
        return 0

    # 只在「发给全部收件人」且全部成功时才记录，测试/单发不会影响当天的正常推送
    if failed == 0 and args.only is None:
        with open(LAST_PUSH_FILE, "w", encoding="utf-8") as f:
            f.write(today)

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
