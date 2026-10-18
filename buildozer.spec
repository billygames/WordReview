[app]

# ---- 应用标识（桌面显示名用中文，内部 title 用英文避免编码问题）----
title = WordReview
package.name = wordreview
package.domain = org.wordreview
android.app_name = 单词复习

# ---- 源代码 ----
source.dir = .
# 必须包含 ttf（中文字体），json（词库导入导出）
source.include_exts = py,png,jpg,jpeg,kv,atlas,ttf,json
source.exclude_dirs = tests, bin, .github, __pycache__
source.exclude_patterns = *.pyc,*.pyo,words.json

# ---- 版本 ----
version = 1.0.0
android.numeric_version = 1

# ---- 依赖（Kivy 应用只需要这两项）----
requirements = python3, hostpython3, kivy==3.0.0.dev0

# ---- 屏幕 ----
# 你的 UI 按竖屏 430×820 设计，保持 portrait
orientation = portrait
fullscreen = 0

# ---- Android 版本与架构 ----
android.api = 33
android.minapi = 24
android.ndk = 25b
# 同时构建 64 位和 32 位，覆盖绝大多数设备
android.archs = arm64-v8a, armeabi-v7a

# ---- 权限 ----
# FileChooser 需要访问外部存储；MANAGE_EXTERNAL_STORAGE 用于 Android 11+
# 访问 Download 目录（侧载/自用场景足够）
android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,MANAGE_EXTERNAL_STORAGE

# ---- 产物 ----
android.release_artifact = apk
android.debug_artifact = apk

# ---- 其他构建行为 ----
android.accept_sdk_license = True
android.skip_update = False
# 让 Python 的 print 出现在 logcat（调试时有用）
android.logcat_filters = *:S python:D

# ---- 可选：图标（如有 icon.png 可取消注释）----
# icon.filename = %(source.dir)s/icon.png

# ---- 可选：启动画面（如有可取消注释）----
# presplash.filename = %(source.dir)s/presplash.png


[buildozer]

# 关键：关闭 root 警告，CI 容器中自动继续，避免 EOFError
warn_on_root = 0

# 日志级别：0 = 仅错误，1 = 信息，2 = 调试（含命令输出）
log_level = 2

# 构建目录和产物目录（默认值，一般无需修改）
build_dir = ./.buildozer
bin_dir = ./bin
