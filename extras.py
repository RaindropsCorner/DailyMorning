# -*- coding: UTF-8 -*-
"""每日推送的附加信息：农历、二十四节气、节日、天气提醒。

节气用「寿星公式」按 2000–2099 年计算：
    日 = int(Y * 0.2422 + C) - L
其中 Y 是年份后两位，C 是每个节气的常数，L 为闰年修正。
个别年份会差一天，但对"当天提醒"这种用途足够了。
"""
from datetime import date, datetime, timedelta

from zhdate import ZhDate

_NUM = "一二三四五六七八九十"

# 节气：(名称, 21 世纪常数 C, 是否用 (Y-1)/4 作闰年修正)
_SOLAR_TERMS = [
    ("小寒", 5.4055, True),  ("大寒", 20.12, True),
    ("立春", 3.87, True),    ("雨水", 18.73, True),
    ("惊蛰", 5.63, False),   ("春分", 20.646, False),
    ("清明", 4.81, False),   ("谷雨", 20.1, False),
    ("立夏", 5.52, False),   ("小满", 21.04, False),
    ("芒种", 5.678, False),  ("夏至", 21.37, False),
    ("小暑", 7.108, False),  ("大暑", 22.83, False),
    ("立秋", 7.5, False),    ("处暑", 23.13, False),
    ("白露", 7.646, False),  ("秋分", 23.042, False),
    ("寒露", 8.318, False),  ("霜降", 23.438, False),
    ("立冬", 7.438, False),  ("小雪", 22.36, False),
    ("大雪", 7.18, False),   ("冬至", 21.94, False),
]

# 公历节日
_SOLAR_FESTIVALS = {
    (1, 1): "元旦", (2, 14): "情人节", (3, 8): "妇女节", (3, 12): "植树节",
    (4, 1): "愚人节", (5, 1): "劳动节", (5, 4): "青年节", (6, 1): "儿童节",
    (7, 1): "建党节", (8, 1): "建军节", (9, 10): "教师节", (10, 1): "国庆节",
    (11, 11): "光棍节", (12, 24): "平安夜", (12, 25): "圣诞节",
    (10, 31): "万圣夜",
}

# 农历节日：(月, 日): 名称
_LUNAR_FESTIVALS = {
    (1, 1): "春节", (1, 15): "元宵节", (2, 2): "龙抬头",
    (5, 5): "端午节", (7, 7): "七夕", (7, 15): "中元节",
    (8, 15): "中秋节", (9, 9): "重阳节",
    (12, 8): "腊八节", (12, 23): "小年",
}


def _lunar_day_name(n):
    if n <= 10:
        return "初" + _NUM[n - 1]
    if n < 20:
        return "十" + _NUM[n - 11]
    if n == 20:
        return "二十"
    if n < 30:
        return "廿" + _NUM[n - 21]
    return "三十"


def _lunar_month_name(n):
    if n == 1:
        return "正月"
    if n == 11:
        return "冬月"
    if n == 12:
        return "腊月"
    return _NUM[n - 1] + "月"


def _to_lunar(d):
    return ZhDate.from_datetime(datetime(d.year, d.month, d.day))


def lunar_text(d):
    """返回「农历九月廿三」这种形式。"""
    z = _to_lunar(d)
    prefix = "闰" if getattr(z, "leap_month", False) else ""
    return "农历{}{}{}".format(prefix, _lunar_month_name(z.lunar_month),
                             _lunar_day_name(z.lunar_day))


def solar_term(d):
    """当天是节气就返回名称，否则 None。"""
    y = d.year % 100
    for i, (name, c, use_prev) in enumerate(_SOLAR_TERMS):
        month = i // 2 + 1
        if month != d.month:
            continue
        base = int(y * 0.2422 + c)
        leap = int((y - 1) / 4) if use_prev else int(y / 4)
        if base - leap == d.day:
            return name
    return None


def festival(d):
    """当天是节日就返回名称，否则 None。支持公历、农历和浮动节日。"""
    if (d.month, d.day) in _SOLAR_FESTIVALS:
        return _SOLAR_FESTIVALS[(d.month, d.day)]

    try:
        z = _to_lunar(d)
        if not getattr(z, "leap_month", False):
            name = _LUNAR_FESTIVALS.get((z.lunar_month, z.lunar_day))
            if name:
                return name
        # 除夕：明天是正月初一
        tomorrow = _to_lunar(d + timedelta(days=1))
        if tomorrow.lunar_month == 1 and tomorrow.lunar_day == 1:
            return "除夕"
    except Exception:
        pass

    # 浮动节日
    if d.month == 5 and d.weekday() == 6 and 8 <= d.day <= 14:
        return "母亲节"
    if d.month == 6 and d.weekday() == 6 and 15 <= d.day <= 21:
        return "父亲节"
    if d.month == 11 and d.weekday() == 3 and 22 <= d.day <= 28:
        return "感恩节"
    return None


def day_note(d):
    """拼成一行附加信息：立冬 · 农历九月廿三。"""
    parts = [festival(d), solar_term(d), lunar_text(d)]
    return " · ".join(p for p in parts if p)


def _to_temp_num(text):
    try:
        return int("".join(ch for ch in str(text) if ch.isdigit() or ch == "-"))
    except ValueError:
        return None


def weather_tip(weather, max_temp, min_temp):
    """根据天气和温度给一句提醒，没有需要提醒的就返回空串。"""
    w = weather or ""
    hi = _to_temp_num(max_temp)
    lo = _to_temp_num(min_temp)

    if "雪" in w:
        return "路滑慢行"
    if "雨" in w:
        return "记得带伞"
    if "雾" in w or "霾" in w:
        return "注意防护"

    if hi is not None and lo is not None:
        if hi - lo >= 12:
            return "早晚温差大"
        if hi >= 30:
            return "注意防晒"
        if lo <= -10:
            return "注意保暖"
    return ""


def preview(start, days=10):
    for i in range(days):
        d = start + timedelta(days=i)
        print("  {} {}  {}".format(d, "周" + "一二三四五六日"[d.weekday()], day_note(d)))
