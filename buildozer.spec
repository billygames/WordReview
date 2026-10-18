[app]

# (str) 应用标题
title = WordReview

# (str) 包名 (反向域名格式)
package.name = wordreview
package.domain = org.wordreview

# (str) 源文件目录
source.dir = .

# (list) 需要打包进 APK 的文件扩展名
source.include_exts = py,png,jpg,kv,atlas,ttf

# (list) 需要排除的文件/目录（可选）
source.exclude_dirs = tests, bin, .git, .github

# (str) 应用版本
version = 1.0.0

# (list) Python 包依赖
# 严格指定 Python 3.12.10、Kivy 2.3.1
requirements = python3==3.12.10,hostpython3==3.12.10,kivy==2.3.1

# (list) Android 权限
# 导入/导出 JSON 需要读写外部存储权限
android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE

# (int) Target Android API
android.api = 33

# (int) Minimum API (Android 5.0)
android.minapi = 21

# (int) Android NDK 版本
android.ndk = 25b

# (list) 目标 CPU 架构
android.archs = arm64-v8a, armeabi-v7a

# (str) 应用图标（如果有则取消注释并放置 icon.png）
# icon.filename = %(source.dir)s/icon.png

# (str) 启动画面（可选）
# presplash.filename = %(source.dir)s/presplash.png

# (str) 应用版本号（整数，用于 Google Play）
android.numeric_version = 1

# (bool) 允许在非测试设备上安装 (debug 模式保持默认即可)
# android.allow_backup = True

# (str) 是否启用 Android 硬件加速（Kivy 默认开启）
android.hardware.accelerometer = False

android.accept_sdk_license = True
