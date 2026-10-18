[app]

# 英文 title 避免编码问题，中文名用 android.app_name
title = WordReview
android.app_name = WordReview
package.name = wordreview
package.domain = org.wordreview

source.dir = .
# 关键：ttf 必须包含，否则中文字体丢失
source.include_exts = py,png,jpg,kv,atlas,ttf,json
source.exclude_dirs = tests,.github,__pycache__,.buildozer
source.exclude_patterns = *.pyc,*.pyo,words.json

version = 1.0.0

# 依赖极简：只需要 kivy，不用 python3-android 之外的任何东西
requirements = python3,kivy

# 让 Python 的 print 显示在 logcat（调试用）
android.logcat_filters = *:S python:D

# ---- 屏幕与状态栏（这个项目的 UI 是竖屏设计的）----
orientation = portrait
fullscreen = 0

# ---- Android 版本 ----
android.api = 33
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a

# ---- 关键：FileChooser 需要访问外部存储 ----
# Android 11+ 想访问 Download 目录必须 MANAGE_EXTERNAL_STORAGE
android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,MANAGE_EXTERNAL_STORAGE

android.allow_backup = True
android.accept_sdk_license = True

# ---- 图标 ----
# icon.filename = %(source.dir)s/icon.png

# ---- 打包优化（构建时间大幅缩短）----
android.release_artifact = apk
android.debug_artifact = apk
p4a.branch = master
android.skip_update = False
