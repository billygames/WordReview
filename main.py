# -*- coding: utf-8 -*-
"""
单词复习卡片 WordReview
====================================
功能：
  1. 单词增删（单词 + 中文翻译 + 词性）
  2. 随机单选卡片复习：
       - 卡片上方显示英文单词
       - 选项格式为「中文翻译，词性」
       - 选项从词库中随机组合，必含正确项
       - 选对 → 自动切下一题；选错 → 仅边框变红，可继续选
  3. 词库 JSON 导入 / 导出
  4. 字体读取主文件目录下的 font.ttf（缺失时自动回退默认字体）

UI：
  - 双层柔和阴影模拟动态模糊
  - 按钮按压阴影下沉反馈
  - 题目卡片 + 选项错峰渐显
  - 复习 → 词库向左滑，词库 → 复习向右滑
"""

import json
import os
import random
import sys
from pathlib import Path

from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.graphics import Color, Line, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.properties import (BooleanProperty, ColorProperty, NumericProperty,
                             StringProperty)
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen, ScreenManager, SlideTransition
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.utils import get_color_from_hex, platform

# --------------------------------------------------------------------------- #
# 目录 / 字体
# --------------------------------------------------------------------------- #
BASE_DIR = Path(__file__).resolve().parent


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return BASE_DIR


def _register_font() -> str:
    candidates = [BASE_DIR / "NotoSansSC-Regular.ttf", Path.cwd() / "NotoSansSC-Regular.ttf"]
    for p in candidates:
        if p.exists():
            try:
                LabelBase.register(name="AppFont", fn_regular=str(p))
                return "AppFont"
            except Exception:  # noqa: BLE001
                continue
    return "Roboto"


FONT_NAME = _register_font()

if platform not in ("android", "ios"):
    Window.size = (430, 820)

# --------------------------------------------------------------------------- #
# 配色
# --------------------------------------------------------------------------- #
APP_BG = get_color_from_hex("#EDF1F7")
CARD_BG = get_color_from_hex("#FFFFFF")
PRIMARY = get_color_from_hex("#3B82F6")
PRIMARY_DARK = get_color_from_hex("#2563EB")
TEXT_MAIN = get_color_from_hex("#1F2937")
TEXT_SUB = get_color_from_hex("#6B7280")
BORDER = get_color_from_hex("#DCE3ED")
SUCCESS = get_color_from_hex("#22C55E")
SUCCESS_BG = get_color_from_hex("#DCFCE7")
DANGER = get_color_from_hex("#EF4444")
DANGER_BG = get_color_from_hex("#FEE2E2")
DANGER_TEXT = get_color_from_hex("#B91C1C")
SUCCESS_TEXT = get_color_from_hex("#15803D")

# 阴影颜色（偏蓝的深灰，比纯黑更柔和）
SHADOW_RGB = (0.10, 0.15, 0.30)

DEFAULT_WORDS = [
    {"word": "abandon", "meaning": "抛弃，放弃", "pos": "v."},
    {"word": "ability", "meaning": "能力，才能", "pos": "n."},
    {"word": "absolutely", "meaning": "绝对地，完全地", "pos": "adv."},
    {"word": "accurate", "meaning": "准确的，精确的", "pos": "adj."},
    {"word": "achieve", "meaning": "实现，达到", "pos": "v."},
    {"word": "benefit", "meaning": "益处，好处", "pos": "n."},
    {"word": "confident", "meaning": "自信的", "pos": "adj."},
    {"word": "consider", "meaning": "考虑，认为", "pos": "v."},
    {"word": "describe", "meaning": "描述，形容", "pos": "v."},
    {"word": "eventually", "meaning": "最终，终于", "pos": "adv."},
    {"word": "familiar", "meaning": "熟悉的", "pos": "adj."},
    {"word": "generous", "meaning": "慷慨的，大方的", "pos": "adj."},
    {"word": "increase", "meaning": "增加，增长", "pos": "v."},
    {"word": "obvious", "meaning": "明显的", "pos": "adj."},
    {"word": "prepare", "meaning": "准备", "pos": "v."},
    {"word": "reduce", "meaning": "减少，降低", "pos": "v."},
]


# --------------------------------------------------------------------------- #
# 通用小工具
# --------------------------------------------------------------------------- #
def make_label(text="", **kwargs):
    kwargs.setdefault("font_name", FONT_NAME)
    return Label(text=text, **kwargs)


def fade_in(widget, duration=0.3, delay=0.0):
    """渐显：从 0 → 1，'out_quad' 缓动。"""
    widget.opacity = 0
    anim = Animation(opacity=1, d=duration, t="out_quad")

    def _start(dt):
        anim.start(widget)

    if delay > 0:
        Clock.schedule_once(_start, delay)
    else:
        _start(None)


def toast(msg, title="提示"):
    box = BoxLayout(padding=dp(14))
    box.add_widget(make_label(msg, font_size=sp(15), color=TEXT_MAIN,
                              halign="center", valign="middle"))
    popup = Popup(title="", content=box, size_hint=(0.68, 0.26),
                  separator_height=0, background_color=CARD_BG)
    popup.open()
    Clock.schedule_once(lambda dt: popup.dismiss(), 1.8)


# --------------------------------------------------------------------------- #
# 通用阴影圆角容器
# --------------------------------------------------------------------------- #
class RoundedBox(BoxLayout):
    """带双层柔和阴影 + 圆角背景的容器。"""

    bg_color = ColorProperty(CARD_BG)
    border_color = ColorProperty([0, 0, 0, 0])
    radius = NumericProperty(dp(18))
    border_width = NumericProperty(dp(1))
    shadow_offset = NumericProperty(dp(3))
    shadow_alpha = NumericProperty(0.10)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            # 外圈阴影（更薄更透 = 模糊感）
            self._s1c = Color(rgba=(0, 0, 0, 0))
            self._s1 = RoundedRectangle(pos=self.pos, size=self.size,
                                        radius=[self.radius])
            # 内圈阴影
            self._s2c = Color(rgba=(0, 0, 0, 0))
            self._s2 = RoundedRectangle(pos=self.pos, size=self.size,
                                        radius=[self.radius])
            # 主体背景
            self._c = Color(rgba=self.bg_color)
            self._r = RoundedRectangle(pos=self.pos, size=self.size,
                                       radius=[self.radius])
            # 边框
            self._bc = Color(rgba=self.border_color)
            self._bl = Line(rounded_rectangle=(0, 0, 1, 1, self.radius),
                            width=self.border_width)

        self.bind(pos=self._sync, size=self._sync,
                  radius=self._sync, border_width=self._sync,
                  shadow_offset=self._sync)
        self.bind(shadow_alpha=self._sync_color,
                  bg_color=self._sync_color, border_color=self._sync_color)
        self._sync()
        self._sync_color()

    def _sync(self, *args):
        r = self.radius
        # 外圈
        sp1 = dp(6)
        self._s1.pos = (self.x - sp1 / 2,
                        self.y - self.shadow_offset - sp1 / 2)
        self._s1.size = (self.width + sp1, self.height + sp1)
        self._s1.radius = [r + sp1 / 2]
        # 内圈
        sp2 = dp(2)
        self._s2.pos = (self.x - sp2 / 2,
                        self.y - self.shadow_offset - sp2 / 2)
        self._s2.size = (self.width + sp2, self.height + sp2)
        self._s2.radius = [r + sp2 / 2]
        # 主体
        self._r.pos = self.pos
        self._r.size = self.size
        self._r.radius = [r]
        self._bl.rounded_rectangle = (self.x, self.y, self.width,
                                      self.height, r)
        self._bl.width = self.border_width

    def _sync_color(self, *args):
        a = self.shadow_alpha
        self._s1c.rgba = (*SHADOW_RGB, a * 0.45)
        self._s2c.rgba = (*SHADOW_RGB, a)
        self._c.rgba = self.bg_color
        self._bc.rgba = self.border_color


class PillButton(ButtonBehavior, Label):
    """圆角按钮（文字居中），带按压阴影反馈。"""

    bg_color = ColorProperty(CARD_BG)
    border_color = ColorProperty([0, 0, 0, 0])
    radius = NumericProperty(dp(14))
    border_width = NumericProperty(dp(1))
    shadow_offset = NumericProperty(dp(2.5))
    shadow_alpha = NumericProperty(0.16)

    def __init__(self, **kwargs):
        kwargs.setdefault("font_name", FONT_NAME)
        kwargs.setdefault("halign", "center")
        kwargs.setdefault("valign", "middle")
        super().__init__(**kwargs)
        with self.canvas.before:
            self._s1c = Color(rgba=(0, 0, 0, 0))
            self._s1 = RoundedRectangle(pos=self.pos, size=self.size,
                                        radius=[self.radius])
            self._s2c = Color(rgba=(0, 0, 0, 0))
            self._s2 = RoundedRectangle(pos=self.pos, size=self.size,
                                        radius=[self.radius])
            self._c = Color(rgba=self.bg_color)
            self._r = RoundedRectangle(pos=self.pos, size=self.size,
                                       radius=[self.radius])
            self._bc = Color(rgba=self.border_color)
            self._bl = Line(rounded_rectangle=(0, 0, 1, 1, self.radius),
                            width=self.border_width)

        self.bind(pos=self._sync, size=self._sync,
                  radius=self._sync, border_width=self._sync,
                  shadow_offset=self._sync,
                  state=self._on_state)
        self.bind(shadow_alpha=self._sync_color,
                  bg_color=self._sync_color, border_color=self._sync_color)
        self.bind(size=self.setter("text_size"))
        self._sync()
        self._sync_color()

    def on_touch_down(self, touch):
        if self.disabled:
            return False
        return super().on_touch_down(touch)

    def _on_state(self, *args):
        # 按下 → 阴影下沉变淡；松开 → 恢复
        self._sync_color()
        if self.state == "down":
            Animation(shadow_offset=dp(0.8), shadow_alpha=0.05,
                      d=0.08, t="out_quad").start(self)
        else:
            Animation(shadow_offset=dp(2.5), shadow_alpha=0.16,
                      d=0.18, t="out_quad").start(self)

    def _sync(self, *args):
        r = self.radius
        sp1 = dp(6)
        self._s1.pos = (self.x - sp1 / 2,
                        self.y - self.shadow_offset - sp1 / 2)
        self._s1.size = (self.width + sp1, self.height + sp1)
        self._s1.radius = [r + sp1 / 2]
        sp2 = dp(2)
        self._s2.pos = (self.x - sp2 / 2,
                        self.y - self.shadow_offset - sp2 / 2)
        self._s2.size = (self.width + sp2, self.height + sp2)
        self._s2.radius = [r + sp2 / 2]
        self._r.pos = self.pos
        self._r.size = self.size
        self._r.radius = [r]
        self._bl.rounded_rectangle = (self.x, self.y, self.width,
                                      self.height, r)
        self._bl.width = self.border_width

    def _sync_color(self, *args):
        a = self.shadow_alpha
        self._s1c.rgba = (*SHADOW_RGB, a * 0.4)
        self._s2c.rgba = (*SHADOW_RGB, a)
        c = list(self.bg_color)
        if self.state == "down":
            c = [c[0] * 0.9, c[1] * 0.9, c[2] * 0.9, c[3]]
        self._c.rgba = c
        self._bc.rgba = self.border_color


class RoundedInput(RoundedBox):
    """圆角输入框（无阴影，避免与卡片阴影重叠显得脏）。"""

    def __init__(self, hint="", **kwargs):
        kwargs.setdefault("orientation", "horizontal")
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(48))
        kwargs.setdefault("bg_color", CARD_BG)
        kwargs.setdefault("border_color", BORDER)
        kwargs.setdefault("radius", dp(12))
        kwargs.setdefault("padding", [dp(6), 0])
        kwargs.setdefault("shadow_alpha", 0)  # 输入框不投影
        super().__init__(**kwargs)
        self.input = TextInput(
            hint_text=hint,
            font_name=FONT_NAME,
            font_size=sp(15),
            multiline=False,
            background_normal="",
            background_active="",
            background_color=[0, 0, 0, 0],
            foreground_color=TEXT_MAIN,
            hint_text_color=TEXT_SUB,
            cursor_color=PRIMARY,
            padding=[dp(8), dp(12)],
        )
        self.add_widget(self.input)

    @property
    def text(self):
        return self.input.text

    @text.setter
    def text(self, value):
        self.input.text = value


class OptionButton(ButtonBehavior, BoxLayout):
    """复习选项按钮：idle / wrong / right 三态，带阴影。"""

    text = StringProperty("")
    bg_color = ColorProperty(CARD_BG)
    line_color = ColorProperty(BORDER)
    text_color = ColorProperty(TEXT_MAIN)
    radius = NumericProperty(dp(14))
    status = StringProperty("idle")
    shadow_offset = NumericProperty(dp(2.5))
    shadow_alpha = NumericProperty(0.10)

    def __init__(self, **kwargs):
        kwargs.setdefault("orientation", "horizontal")
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(54))
        kwargs.setdefault("padding", [dp(18), 0])
        super().__init__(**kwargs)

        self._label = make_label(
            text=self.text, font_size=sp(16), color=self.text_color,
            halign="left", valign="middle",
        )
        self._label.bind(size=self._label.setter("text_size"))
        self.bind(text=self._label.setter("text"),
                  text_color=self._label.setter("color"))
        self.add_widget(self._label)

        with self.canvas.before:
            self._s1c = Color(rgba=(0, 0, 0, 0))
            self._s1 = RoundedRectangle(pos=self.pos, size=self.size,
                                        radius=[self.radius])
            self._s2c = Color(rgba=(0, 0, 0, 0))
            self._s2 = RoundedRectangle(pos=self.pos, size=self.size,
                                        radius=[self.radius])
            self._c = Color(rgba=self.bg_color)
            self._r = RoundedRectangle(pos=self.pos, size=self.size,
                                       radius=[self.radius])
            self._lc = Color(rgba=self.line_color)
            self._ll = Line(rounded_rectangle=(0, 0, 1, 1, self.radius),
                            width=dp(1.2))

        self.bind(pos=self._sync, size=self._sync, radius=self._sync,
                  shadow_offset=self._sync,
                  state=self._on_state)
        self.bind(shadow_alpha=self._sync_color,
                  bg_color=self._sync_color, line_color=self._sync_color)
        self._sync()
        self._sync_color()

    def on_touch_down(self, touch):
        if self.disabled:
            return False
        return super().on_touch_down(touch)

    def _on_state(self, *args):
        if self.status != "idle":
            return
        if self.state == "down":
            Animation(shadow_offset=dp(0.8), shadow_alpha=0.04,
                      d=0.08, t="out_quad").start(self)
        else:
            Animation(shadow_offset=dp(2.5), shadow_alpha=0.10,
                      d=0.16, t="out_quad").start(self)

    def _sync(self, *args):
        r = self.radius
        sp1 = dp(6)
        self._s1.pos = (self.x - sp1 / 2,
                        self.y - self.shadow_offset - sp1 / 2)
        self._s1.size = (self.width + sp1, self.height + sp1)
        self._s1.radius = [r + sp1 / 2]
        sp2 = dp(2)
        self._s2.pos = (self.x - sp2 / 2,
                        self.y - self.shadow_offset - sp2 / 2)
        self._s2.size = (self.width + sp2, self.height + sp2)
        self._s2.radius = [r + sp2 / 2]
        self._r.pos = self.pos
        self._r.size = self.size
        self._r.radius = [r]
        self._ll.rounded_rectangle = (self.x, self.y, self.width,
                                      self.height, r)

    def _sync_color(self, *args):
        a = self.shadow_alpha
        self._s1c.rgba = (*SHADOW_RGB, a * 0.4)
        self._s2c.rgba = (*SHADOW_RGB, a)
        self._c.rgba = self.bg_color
        self._lc.rgba = self.line_color

    def set_status(self, status):
        """只改变边框颜色，不改背景 / 文字 / disabled。"""
        self.status = status
        if status == "wrong":
            self.line_color = DANGER
        elif status == "right":
            self.line_color = SUCCESS


class WordRow(RoundedBox):
    """词库列表中的一行。"""

    def __init__(self, data, on_delete, **kwargs):
        kwargs.setdefault("orientation", "horizontal")
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(64))
        kwargs.setdefault("padding", [dp(14), 0])
        kwargs.setdefault("bg_color", CARD_BG)
        kwargs.setdefault("border_color", BORDER)
        kwargs.setdefault("radius", dp(14))
        kwargs.setdefault("shadow_alpha", 0.06)
        super().__init__(**kwargs)

        left = BoxLayout(orientation="vertical", spacing=dp(2))
        w_lbl = make_label(text=data.get("word", ""), font_size=sp(17),
                           color=TEXT_MAIN, halign="left", valign="middle")
        w_lbl.bind(size=w_lbl.setter("text_size"))
        sub_text = "{m}   {p}".format(
            m=data.get("meaning", ""), p=data.get("pos", "")
        ).strip()
        m_lbl = make_label(text=sub_text, font_size=sp(12),
                           color=TEXT_SUB, halign="left", valign="middle")
        m_lbl.bind(size=m_lbl.setter("text_size"))
        left.add_widget(w_lbl)
        left.add_widget(m_lbl)
        self.add_widget(left)

        del_btn = PillButton(text="删除", font_size=sp(12),
                             size_hint=(None, None),
                             size=(dp(56), dp(34)),
                             bg_color=DANGER_BG, color=DANGER_TEXT,
                             radius=dp(10),
                             shadow_alpha=0.08)
        del_btn.bind(on_release=lambda *_: on_delete(data))
        wrap = AnchorLayout(anchor_x="right", anchor_y="center",
                            size_hint_x=None, width=dp(60))
        wrap.add_widget(del_btn)
        self.add_widget(wrap)


# --------------------------------------------------------------------------- #
# 数据层（与之前一致）
# --------------------------------------------------------------------------- #
class WordStore:
    def __init__(self, path):
        self.path = Path(path)
        self.words = []
        self.load()

    def load(self):
        if not self.path.exists():
            self.words = []
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.words = self._normalize(data)
        except Exception:  # noqa: BLE001
            self.words = []

    def save(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            payload = {"version": 1, "words": self.words}
            self.path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:  # noqa: BLE001
            pass

    @staticmethod
    def _normalize(data):
        if isinstance(data, dict):
            items = data.get("words") or data.get("data") or []
        elif isinstance(data, list):
            items = data
        else:
            items = []
        result, seen = [], set()
        for it in items:
            if not isinstance(it, dict):
                continue
            w = str(it.get("word", "")).strip()
            if not w or w.lower() in seen:
                continue
            seen.add(w.lower())
            result.append({
                "word": w,
                "meaning": str(it.get("meaning", "")).strip(),
                "pos": str(it.get("pos", "")).strip(),
            })
        return result

    def add(self, word, meaning, pos):
        key = word.lower()
        for it in self.words:
            if it["word"].lower() == key:
                return False
        self.words.append({"word": word, "meaning": meaning, "pos": pos})
        self.save()
        return True

    def remove(self, word):
        self.words = [w for w in self.words if w["word"] != word]
        self.save()

    def export_to(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": 1, "words": self.words}
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                        encoding="utf-8")

    def import_from(self, path):
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        items = self._normalize(raw)
        index = {w["word"].lower(): w for w in self.words}
        added = 0
        for it in items:
            key = it["word"].lower()
            if key in index:
                index[key].update(it)
            else:
                self.words.append(it)
                index[key] = it
                added += 1
        self.save()
        return added


# --------------------------------------------------------------------------- #
# 复习页面
# --------------------------------------------------------------------------- #
class QuizScreen(Screen):
    OPTION_COUNT = 4

    def __init__(self, app, **kwargs):
        kwargs.setdefault("name", "quiz")
        super().__init__(**kwargs)
        self.app = app
        self.current_word = None
        self.correct_text = ""
        self.options = []
        self._lock = False
        self._build_ui()

    def _build_ui(self):
        root = BoxLayout(orientation="vertical",
                         padding=[dp(18), dp(10), dp(18), dp(6)],
                         spacing=dp(12))

        # 单词卡片
        card = RoundedBox(orientation="vertical", size_hint_y=None,
                          height=dp(168), bg_color=CARD_BG, radius=dp(22),
                          padding=[dp(14), dp(18)], shadow_alpha=0.10)
        self.word_label = make_label(text="", font_size=sp(38),
                                     color=TEXT_MAIN, halign="center",
                                     valign="middle", size_hint_y=0.72)
        self.word_label.bind(size=self.word_label.setter("text_size"))
        self.hint_label = make_label(
            text="选择正确的中文释义与词性", font_size=sp(13),
            color=TEXT_SUB, halign="center", valign="middle",
            size_hint_y=None, height=dp(26),
        )
        self.hint_label.bind(size=self.hint_label.setter("text_size"))
        card.add_widget(self.word_label)
        card.add_widget(self.hint_label)
        root.add_widget(card)

        # 选项区
        self.options_box = BoxLayout(orientation="vertical", spacing=dp(8),
                                     size_hint_y=None,
                                     height=dp(54 * 4 + 8 * 3))
        root.add_widget(self.options_box)

        self.tip_label = make_label(
            text="", font_size=sp(12), color=TEXT_SUB,
            halign="center", valign="middle",
            size_hint_y=None, height=dp(24),
        )
        self.tip_label.bind(size=self.tip_label.setter("text_size"))
        root.add_widget(self.tip_label)

        self.add_widget(root)

    @staticmethod
    def option_text(item):
        meaning = (item.get("meaning") or "").strip()
        pos = (item.get("pos") or "").strip()
        return f"{meaning}，{pos}" if pos else meaning

    def _build_option_texts(self, correct, words):
        n = self.OPTION_COUNT
        result = [correct]
        seen = {correct}

        pool = [self.option_text(w) for w in words]
        random.shuffle(pool)
        for t in pool:
            if len(result) >= n:
                break
            if t and t not in seen:
                seen.add(t)
                result.append(t)

        meanings = list({(w.get("meaning") or "").strip()
                         for w in words} - {""})
        poss = list({(w.get("pos") or "").strip() for w in words} - {""})
        guard = 0
        while len(result) < n and guard < 200 and meanings:
            guard += 1
            m = random.choice(meanings)
            p = random.choice(poss) if poss else ""
            t = f"{m}，{p}" if p else m
            if t not in seen:
                seen.add(t)
                result.append(t)

        random.shuffle(result)
        return result

    def new_question(self):
        self._lock = False
        self.options_box.clear_widgets()
        self.options = []
        words = self.app.store.words

        if not words:
            self.current_word = None
            self.correct_text = ""
            self.word_label.text = "词库为空"
            self.hint_label.text = "请到「词库」页面添加单词"
            self.options_box.height = 0
            return

        self.current_word = random.choice(words)
        self.word_label.text = self.current_word["word"]
        self.hint_label.text = "选择正确的中文释义与词性"
        self.tip_label.text = ""
        self.correct_text = self.option_text(self.current_word)

        texts = self._build_option_texts(self.correct_text, words)
        self.options_box.height = (len(texts) * dp(54)
                                   + max(0, len(texts) - 1) * dp(8))

        # ---- 渐显：卡片先，选项错峰跟上 ----
        fade_in(self.word_label, duration=0.32)
        fade_in(self.hint_label, duration=0.4, delay=0.05)

        for i, t in enumerate(texts):
            btn = OptionButton(text=t)
            btn.opacity = 0
            btn.bind(on_release=lambda inst, txt=t: self._on_pick(inst, txt))
            self.options_box.add_widget(btn)
            self.options.append(btn)
            fade_in(btn, duration=0.28, delay=0.08 + i * 0.055)

    def _on_pick(self, btn, text):
        if self._lock or btn.status != "idle" or self.current_word is None:
            return

        if text == self.correct_text:
            self._lock = True
            btn.set_status("right")
            self.app.stats["right"] += 1
            self.app.refresh_stats()
            self.hint_label.text = "回答正确，继续下一题"
            # 正确反馈：卡片和选项一起淡出，再刷新下一题
            self._fade_out_and_next()
        else:
            btn.set_status("wrong")
            self.app.stats["wrong"] += 1
            self.app.refresh_stats()
            self.hint_label.text = "不对哦，再想想"

    def _fade_out_and_next(self):
        anim = Animation(opacity=0, d=0.22, t="out_quad")
        for w in [self.word_label, self.hint_label] + self.options:
            anim.start(w)
        Clock.schedule_once(lambda dt: self.new_question(), 0.24)


# --------------------------------------------------------------------------- #
# 词库管理页面
# --------------------------------------------------------------------------- #
class ManageScreen(Screen):
    def __init__(self, app, **kwargs):
        kwargs.setdefault("name", "manage")
        super().__init__(**kwargs)
        self.app = app
        self._build_ui()
        self.refresh()
        fade_in(self, duration=0.35)

    def _build_ui(self):
        root = BoxLayout(orientation="vertical",
                         padding=[dp(16), dp(10), dp(16), dp(10)],
                         spacing=dp(10))

        form = RoundedBox(orientation="vertical", padding=dp(12),
                          spacing=dp(8), size_hint_y=None,
                          bg_color=CARD_BG, border_color=BORDER,
                          radius=dp(16), shadow_alpha=0.08)
        form.bind(minimum_height=form.setter("height"))
        form.add_widget(make_label("添加新单词", font_size=sp(14),
                                   color=TEXT_SUB, halign="left",
                                   valign="middle", size_hint_y=None,
                                   height=dp(22)))
        self.in_word = RoundedInput("单词，例如 apple")
        self.in_meaning = RoundedInput("中文翻译，例如 苹果")
        self.in_pos = RoundedInput("词性，例如 n. / v. / adj.")
        form.add_widget(self.in_word)
        form.add_widget(self.in_meaning)
        form.add_widget(self.in_pos)

        add_btn = PillButton(text="添加到词库", font_size=sp(15),
                             bg_color=PRIMARY, color=[1, 1, 1, 1],
                             radius=dp(12), size_hint_y=None,
                             height=dp(46))
        add_btn.bind(on_release=lambda *_: self.add_word())
        form.add_widget(add_btn)
        root.add_widget(form)

        io_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(10))
        imp_btn = PillButton(text="导入 JSON", font_size=sp(14),
                             bg_color=CARD_BG, color=PRIMARY,
                             border_color=PRIMARY, radius=dp(12))
        exp_btn = PillButton(text="导出 JSON", font_size=sp(14),
                             bg_color=PRIMARY, color=[1, 1, 1, 1],
                             radius=dp(12))
        imp_btn.bind(on_release=lambda *_: self.dialog_import())
        exp_btn.bind(on_release=lambda *_: self.dialog_export())
        io_row.add_widget(imp_btn)
        io_row.add_widget(exp_btn)
        root.add_widget(io_row)

        self.count_label = make_label("共 0 个单词", font_size=sp(12),
                                      color=TEXT_SUB, halign="left",
                                      valign="middle", size_hint_y=None,
                                      height=dp(22))
        root.add_widget(self.count_label)

        scroll = ScrollView(do_scroll_x=False, bar_width=dp(3))
        self.list_box = BoxLayout(orientation="vertical", spacing=dp(8),
                                  size_hint_y=None)
        self.list_box.bind(minimum_height=self.list_box.setter("height"))
        scroll.add_widget(self.list_box)
        root.add_widget(scroll)

        self.add_widget(root)

    def refresh(self):
        self.list_box.clear_widgets()
        words = self.app.store.words
        self.count_label.text = f"共 {len(words)} 个单词"
        if not words:
            self.list_box.add_widget(
                make_label("词库还是空的，先添加几个单词吧～",
                           font_size=sp(13), color=TEXT_SUB,
                           halign="center", valign="middle",
                           size_hint_y=None, height=dp(60))
            )
            return
        for i, w in enumerate(words):
            row = WordRow(w, self.delete_word)
            fade_in(row, duration=0.24, delay=min(i * 0.02, 0.3))
            self.list_box.add_widget(row)

    def add_word(self):
        word = self.in_word.text.strip()
        meaning = self.in_meaning.text.strip()
        pos = self.in_pos.text.strip()

        if not word or not meaning:
            toast("单词和中文翻译不能为空")
            return
        if not self.app.store.add(word, meaning, pos):
            toast(f"「{word}」已存在")
            return

        self.in_word.text = ""
        self.in_meaning.text = ""
        self.in_pos.text = ""
        self.refresh()
        self.app.quiz.new_question()
        toast(f"已添加 {word}")

    def delete_word(self, data):
        self.app.store.remove(data["word"])
        self.refresh()
        self.app.quiz.new_question()

    def _start_dir(self):
        if platform == "android":
            for p in ("/storage/emulated/0/Download",
                      "/storage/emulated/0", "/sdcard"):
                if os.path.isdir(p):
                    return p
            return self.app.user_data_dir
        return os.path.expanduser("~")

    def dialog_export(self):
        content = BoxLayout(orientation="vertical", spacing=dp(8),
                            padding=dp(10))
        content.add_widget(make_label("选择导出目录并填写文件名",
                                      font_size=sp(13), color=TEXT_SUB,
                                      halign="left", valign="middle",
                                      size_hint_y=None, height=dp(24)))
        name_input = TextInput(text="words.json", multiline=False,
                               font_name=FONT_NAME, font_size=sp(15),
                               size_hint_y=None, height=dp(42),
                               background_normal="",
                               background_color=get_color_from_hex("#F3F4F6"),
                               foreground_color=TEXT_MAIN)
        content.add_widget(name_input)

        chooser = FileChooserListView(path=self._start_dir(), dirselect=True)
        content.add_widget(chooser)

        popup = Popup(title="", content=content, size_hint=(0.94, 0.94),
                      separator_height=0, background_color=CARD_BG)

        btns = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(10))
        cancel = PillButton(text="取消", font_size=sp(14), bg_color=CARD_BG,
                            color=TEXT_SUB, border_color=BORDER)
        ok = PillButton(text="导出到此处", font_size=sp(14),
                        bg_color=PRIMARY, color=[1, 1, 1, 1])
        cancel.bind(on_release=lambda *_: popup.dismiss())
        ok.bind(on_release=lambda *_: self._do_export(popup, chooser.path,
                                                      name_input.text))
        btns.add_widget(cancel)
        btns.add_widget(ok)
        content.add_widget(btns)
        popup.open()

    def _do_export(self, popup, folder, name):
        name = (name or "").strip() or "words.json"
        if not name.lower().endswith(".json"):
            name += ".json"
        target = Path(folder) / name
        try:
            self.app.store.export_to(target)
            popup.dismiss()
            toast(f"已导出到 {target}")
        except Exception as exc:  # noqa: BLE001
            toast(f"导出失败：{exc}")

    def dialog_import(self):
        content = BoxLayout(orientation="vertical", spacing=dp(8),
                            padding=dp(10))
        content.add_widget(make_label("选择一个 .json 词库文件",
                                      font_size=sp(13), color=TEXT_SUB,
                                      halign="left", valign="middle",
                                      size_hint_y=None, height=dp(24)))
        chooser = FileChooserListView(path=self._start_dir(),
                                      filters=["*.json"])
        content.add_widget(chooser)

        popup = Popup(title="", content=content, size_hint=(0.94, 0.94),
                      separator_height=0, background_color=CARD_BG)

        btns = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(10))
        cancel = PillButton(text="取消", font_size=sp(14), bg_color=CARD_BG,
                            color=TEXT_SUB, border_color=BORDER)
        ok = PillButton(text="导入", font_size=sp(14), bg_color=PRIMARY,
                        color=[1, 1, 1, 1])
        cancel.bind(on_release=lambda *_: popup.dismiss())
        ok.bind(on_release=lambda *_: self._do_import(popup, chooser.selection))
        btns.add_widget(cancel)
        btns.add_widget(ok)
        content.add_widget(btns)
        popup.open()

    def _do_import(self, popup, selection):
        if not selection:
            toast("请先选择一个 .json 文件")
            return
        try:
            added = self.app.store.import_from(selection[0])
            popup.dismiss()
            self.refresh()
            self.app.quiz.new_question()
            toast(f"导入完成，新增 {added} 个单词")
        except Exception as exc:  # noqa: BLE001
            toast(f"导入失败：{exc}")


# --------------------------------------------------------------------------- #
# 底部 Tab
# --------------------------------------------------------------------------- #
class TabBar(BoxLayout):
    def __init__(self, app, **kwargs):
        kwargs.setdefault("orientation", "horizontal")
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(62))
        kwargs.setdefault("padding", [dp(14), dp(9)])
        kwargs.setdefault("spacing", dp(10))
        super().__init__(**kwargs)
        self.app = app

        self.btn_quiz = PillButton(text="复习", font_size=sp(15),
                                   radius=dp(14), bg_color=PRIMARY,
                                   color=[1, 1, 1, 1])
        self.btn_manage = PillButton(text="词库", font_size=sp(15),
                                     radius=dp(14), bg_color=CARD_BG,
                                     color=TEXT_SUB, border_color=BORDER)
        self.btn_quiz.bind(on_release=lambda *_: app.switch_tab(0))
        self.btn_manage.bind(on_release=lambda *_: app.switch_tab(1))
        self.add_widget(self.btn_quiz)
        self.add_widget(self.btn_manage)

    def set_active(self, index):
        if index == 0:
            self.btn_quiz.bg_color = PRIMARY
            self.btn_quiz.color = [1, 1, 1, 1]
            self.btn_quiz.border_color = [0, 0, 0, 0]
            self.btn_manage.bg_color = CARD_BG
            self.btn_manage.color = TEXT_SUB
            self.btn_manage.border_color = BORDER
        else:
            self.btn_quiz.bg_color = CARD_BG
            self.btn_quiz.color = TEXT_SUB
            self.btn_quiz.border_color = BORDER
            self.btn_manage.bg_color = PRIMARY
            self.btn_manage.color = [1, 1, 1, 1]
            self.btn_manage.border_color = [0, 0, 0, 0]


# --------------------------------------------------------------------------- #
# App
# --------------------------------------------------------------------------- #
class WordApp(App):
    title = "单词复习卡片"
    version = "1.0.0"

    def build(self):
        Window.clearcolor = APP_BG

        self.store = WordStore(self._data_file())
        if not self.store.words:
            self.store.words = [dict(w) for w in DEFAULT_WORDS]
            self.store.save()

        self.stats = {"right": 0, "wrong": 0}

        root = BoxLayout(orientation="vertical")

        # 顶部栏：标题 + 版本号 + 统计
        top = BoxLayout(size_hint_y=None, height=dp(56),
                        padding=[dp(18), 0], spacing=dp(8))

        title_group = BoxLayout(size_hint=(None, 1), width=dp(170),
                                spacing=dp(4))
        title = make_label("单词复习", font_size=sp(19), color=TEXT_MAIN,
                           halign="left", valign="middle",
                           size_hint_x=None, width=dp(100))
        title.bind(size=title.setter("text_size"))
        version_label = make_label(f"v{self.version}", font_size=sp(11),
                                   color=TEXT_SUB, halign="left",
                                   valign="middle",
                                   size_hint_x=None, width=dp(56))
        version_label.bind(size=version_label.setter("text_size"))
        title_group.add_widget(title)
        title_group.add_widget(version_label)
        top.add_widget(title_group)

        self.stats_label = make_label("正确 0 · 错误 0", font_size=sp(13),
                                      color=TEXT_SUB, halign="right",
                                      valign="middle", size_hint_x=None,
                                      width=dp(140))
        self.stats_label.bind(size=self.stats_label.setter("text_size"))
        top.add_widget(self.stats_label)
        root.add_widget(top)

        # 主体
        self.sm = ScreenManager()
        self.sm.transition = SlideTransition(direction="left", duration=0.3)
        self.quiz = QuizScreen(self)
        self.manage = ManageScreen(self)
        self.sm.add_widget(self.quiz)
        self.sm.add_widget(self.manage)
        root.add_widget(self.sm)

        self.tabbar = TabBar(self)
        root.add_widget(self.tabbar)
        self.tabbar.set_active(0)

        Clock.schedule_once(lambda dt: self.quiz.new_question(), 0.05)
        return root

    def on_stop(self):
        try:
            self.store.save()
        except Exception:  # noqa: BLE001
            pass

    def _data_file(self):
        if platform == "android":
            return Path(self.user_data_dir) / "words.json"
        return app_dir() / "words.json"

    def switch_tab(self, index):
        """复习 → 词库：向左滑；词库 → 复习：向右滑。"""
        target = "quiz" if index == 0 else "manage"
        if self.sm.current == target:
            self.tabbar.set_active(index)
            return
        # direction='left'  新屏从右侧进入、旧屏向左移出（整体左滑）
        # direction='right' 新屏从左侧进入、旧屏向右移出（整体右滑）
        direction = "right" if index == 0 else "left"
        self.sm.transition = SlideTransition(direction=direction,
                                             duration=0.32)
        self.sm.current = target
        self.tabbar.set_active(index)
        if index == 0 and self.quiz.current_word is None:
            self.quiz.new_question()

    def refresh_stats(self):
        self.stats_label.text = ("正确 {} · 错误 {}"
                                 .format(self.stats["right"],
                                         self.stats["wrong"]))


if __name__ == "__main__":
    WordApp().run()