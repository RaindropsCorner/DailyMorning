# -*- coding: UTF-8 -*-
"""每日金句的 30 套装饰框。

微信模板消息的边框/背景由模板本身决定，改不了；能动的只有填进字段的字符串。
模板里 `{{note_ch.DATA}}{{note_ch2.DATA}}` 是拼接在同一行渲染的，
所以把装饰加在整段文字的头尾即可 —— 折行会落在中间，装饰不会被切开。

轮换规则：按日期序号 % 30，每 30 天循环一次（正好约一个月）。
想要固定某一天用哪套，可以改 frame_index 的取法。
"""

FRAMES = [
    ("圈引",  "「 ", " 」"),
    ("书名",  "《 ", " 》"),
    ("方头",  "【 ", " 】"),
    ("六角",  "〔 ", " 〕"),
    ("花枝",  "❀ ", " ❀"),
    ("星芒",  "✦ ", " ✦"),
    ("弯月",  "☾ ", " ☽"),
    ("波纹",  "﹏ ", " ﹏"),
    ("音符",  "♪ ", " ♪"),
    ("菱形",  "◇ ", " ◇"),
    ("实心",  "◆ ", " ◆"),
    ("空星",  "☆ ", " ☆"),
    ("雪花",  "❅ ", " ❅"),
    ("叶枝",  "❧ ", " ❧"),
    ("花苞",  "✿ ", " ✿"),
    ("双线",  "══ ", " ══"),
    ("细线",  "── ", " ──"),
    ("角标",  "⌜ ", " ⌝"),
    ("方锁",  "⟦ ", " ⟧"),
    ("括号",  "❨ ", " ❩"),
    ("心形",  "♡ ", " ♡"),
    ("四叶",  "✤ ", " ✤"),
    ("小圆",  "◦ ", " ◦"),
    ("竖盒",  "│ ", " │"),
    ("星点",  "⋆ ", " ⋆"),
    ("水滴",  "≈ ", " ≈"),
    ("羽翼",  "❦ ", " ❦"),
    ("方框",  "▢ ", " ▢"),
    ("花环",  "❃ ", " ❃"),
    ("云朵",  "☁ ", " ☁"),
]

FALLBACK = ("无框", "", "")


def _index_for(day):
    """按日期取一套框，30 天一轮。"""
    return day.toordinal() % len(FRAMES)


def pick(day, force_index=None):
    """返回 (序号, 名称, 前缀, 后缀)。force_index 从 1 开始，方便人工指定。"""
    if force_index is not None:
        i = (int(force_index) - 1) % len(FRAMES)
    else:
        i = _index_for(day)
    name, left, right = FRAMES[i]
    return i + 1, name, left, right


def wrap(text, day, force_index=None):
    """把一段文字套进当天的框里，返回 (完整字符串, 框的名称)。"""
    _, name, left, right = pick(day, force_index)
    text = (text or "").strip()
    if not text:
        return text, name
    return "{}{}{}".format(left, text, right), name


def preview(text="萧瑟秋风今又是，换了人间"):
    """终端里预览全部 30 套。"""
    print("共 {} 套，按日期序号轮换\n".format(len(FRAMES)))
    for i, (name, left, right) in enumerate(FRAMES, 1):
        line = "{}{}{}".format(left, text, right)
        print("{:>3}. {:<6s} {}".format(i, name, line))
