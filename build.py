# build.py
"""Скрипт для сборки проекта в .exe"""

import os
import sys
import shutil
from pathlib import Path

def clean_build():
    """Очищает предыдущие сборки."""
    dirs_to_clean = ['build', 'dist', '__pycache__']
    for dir_name in dirs_to_clean:
        path = Path(dir_name)
        if path.exists():
            shutil.rmtree(path)
            print(f"✓ Удалено: {dir_name}")

def check_assets():
    """Проверяет наличие всех необходимых файлов."""
    required = [
        'assets/leshy/idle',
        'assets/leshy/thinking',
        'assets/leshy/talking',
        'core/knowledge_base.json',
        'core/fallback_answers.json',
        'core/loading_phrases.json',
        'main.py',
    ]
    
    all_ok = True
    for path in required:
        if not Path(path).exists():
            print(f"❌ Отсутствует: {path}")
            all_ok = False
    
    # Проверяем скины
    maid_path = Path('core/maid')
    if maid_path.exists():
        print(f"✓ Найдена папка скина maid")
    else:
        print(f"ℹ️ Папка скина maid не найдена (будет использоваться стандартная)")
    
    if all_ok:
        print("✓ Все необходимые файлы найдены")
    return all_ok

def build():
    """Запускает сборку."""
    print("=" * 60)
    print("🌿 Сборка Хранителя Канцелярского Леса")
    print("=" * 60)
    
    if not check_assets():
        return
    
    clean_build()
    
    # Базовая команда
    cmd = (
        'pyinstaller --onefile --windowed '
        '--name "Assistant" '
        '--add-data "assets;assets" '
        '--add-data "core/knowledge_base.json;core" '
        '--add-data "core/fallback_answers.json;core" '
        '--add-data "core/loading_phrases.json;core" '
    )
    
    # Добавляем папки скинов, если есть
    for skin_dir in Path('core').iterdir():
        if skin_dir.is_dir():
            dest = f'core/{skin_dir.name}'
            cmd += f'--add-data "{skin_dir};{dest}" '
            print(f"✓ Добавлен скин: {skin_dir.name}")
    
    cmd += (
        '--hidden-import PyQt5 '
        '--hidden-import PyQt5.QtCore '
        '--hidden-import PyQt5.QtGui '
        '--hidden-import PyQt5.QtWidgets '
        '--hidden-import json '
        '--hidden-import random '
        '--hidden-import datetime '
        '--clean '
    )
    
    # Иконка
    if Path('assets/icon.ico').exists():
        cmd += '--icon "assets/icon.ico" '
    
    cmd += 'main.py'
    
    print(f"\n🔧 Запуск сборки...")
    result = os.system(cmd)
    
    if result == 0:
        exe_path = Path('dist/Assistant.exe')
        size_mb = exe_path.stat().st_size / (1024 * 1024) if exe_path.exists() else 0
        print(f"\n✅ Сборка успешно завершена!")
        print(f"   📁 {exe_path.absolute()}")
        print(f"   📦 Размер: {size_mb:.1f} МБ")
        print(f"\n💡 При первом запуске рядом с .exe создастся settings.json")
    else:
        print(f"\n❌ Ошибка сборки (код: {result})")

if __name__ == "__main__":
    build()