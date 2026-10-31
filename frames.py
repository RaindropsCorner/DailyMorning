# -*- coding: UTF-8 -*-
"""每日金句的 30 套装饰框。

微信模板消息对「填进字段的值」有一层字符过滤（实测 2026-11-01）：
  ✅ 保留：中文标点「」《》【】〔〕〈〉『』〖〗（）、· ｜ °、ASCII 符号
  ❌ 滤掉：emoji（🌸✨🌙🍃…）、制表符（╭─│╰…）、℃、换行 \n

模板里的 emoji 是静态文字，不受影响；值里的一律会被吃掉。
所以这套装饰只用中文括号 + ASCII 分隔符，保证原样显示。

轮换：按日期序号 % 30，30 天一轮（约一个月）。
"""

# (名称, 前缀, 后缀)
FRAMES = [
    ("圈引",   "「 ",    " 」"),
    ("书名",   "《 ",    " 》"),
    ("方头",   "【 ",    " 】"),
    ("六角",   "〔 ",    " 〕"),
    ("单书",   "〈 ",    " 〉"),
    ("双引",   "『 ",    " 』"),
    ("粗方",   "〖 ",    " 〗"),
    ("圆括",   "（ ",    " ）"),
    ("点引",   "·「",    "」·"),
    ("点书",   "·《",    "》·"),
    ("点方",   "·【",    "】·"),
    ("波引",   "~「",    "」~"),
    ("波方",   "~【",    "】~"),
    ("破引",   "—「",    "」—"),
    ("日波",   "〜「",    "」〜"),
    ("内点引", "「·",    "·」"),
    ("内点书", "《·",    "·》"),
    ("内点方", "【·",    "·】"),
    ("内波引", "「~",    "~」"),
    ("内波方", "【~",    "~】"),
    ("内点粗", "〖·",    "·〗"),
    ("内点单", "〈·",    "·〉"),
    ("内波双", "『~",    "~』"),
    ("星引",   "*「",    "」*"),
    ("星方",   "*【",    "】*"),
    ("横引",   "-「",    "」-"),
    ("竖引",   "｜",     "｜"),
    ("尾点方", "【",     "】·"),
    ("头点圆", "·（",    "）"),
    ("尾点粗", "〖",     "〗·"),
]

FALLBACK = ("无框", "", "")


def _index_for(day):
    return day.toordinal() % len(FRAMES)


def pick(day, force_index=None):
    """返回 (序号, 名称, 前缀, 后缀)。force_index 从 1 开始。"""
    if force_index is not None:
        i = (int(force_index) - 1) % len(FRAMES)
    else:
        i = _index_for(day)
    name, left, right = FRAMES[i]
    return i + 1, name, left, right


def wrap(text, day, force_index=None):
    """把文字套进当天的框，返回 (结果, 框名称)。"""
    _, name, left, right = pick(day, force_index)
    text = (text or "").strip()
    if not text:
        return text, name
    return "{}{}{}".format(left, text, right), name


def preview(text="萧瑟秋风今又是，换了人间"):
    print("共 {} 套，按日期序号轮换\n".format(len(FRAMES)))
    for i, (name, left, right) in enumerate(FRAMES, 1):
        print("{:>3}. {:<7s}{}{}{}".format(i, name, left, text, right))
