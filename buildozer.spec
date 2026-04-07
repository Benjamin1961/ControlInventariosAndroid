[app]

title = Panadería Inventarios
package.name = panaderiainventarios
package.domain = org.benjamin

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,db
source.include_patterns = modulos/*.py,assets/*

version = 1.0

# Dependencias corregidas (sin sqlite3, kivymd con versión)
#requirements = python3,kivy==2.3.1,kivymd==1.2.0,pillow==10.1.0,android,pyjnius==1.6.1
#requirements = python3,kivy==2.3.1,kivymd==1.2.0,pillow==10.1.0,android
requirements = python3,kivy==2.3.1,kivymd==1.2.0,pillow==10.1.0,android,filetype

orientation = portrait

android.permissions = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,MANAGE_EXTERNAL_STORAGE

android.api = 33
android.minapi = 21
android.sdk = 33
android.ndk = 25b
android.ndk_api = 21

android.archs = arm64-v8a

android.gradle_dependencies = androidx.appcompat:appcompat:1.4.0
android.enable_androidx = True

android.allow_backup = True

presplash.color = #3E2723

p4a.bootstrap = sdl2

log_level = 2

[buildozer]
build_dir = ./.buildozer
bin_dir = ./bin
android.accept_sdk_license = True
warn_on_root = 1
