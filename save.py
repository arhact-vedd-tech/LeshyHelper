import os
import shutil
from pathlib import Path

def copy_files_to_saved(source_dir='.', exclude_dirs=None, extensions=None):
    """
    Обходит родительский каталог и все дочерние каталоги (кроме исключенных),
    копирует файлы с указанными расширениями напрямую в папку saved.
    
    Args:
        source_dir: исходная директория (по умолчанию текущая)
        exclude_dirs: список исключаемых директорий
        extensions: список расширений файлов для копирования
    """
    
    if exclude_dirs is None:
        exclude_dirs = ['.venv', 'saved']  # Исключаем .venv и папку saved
    
    if extensions is None:
        extensions = ['.py', '.txt', '.json']
    
    # Создаем папку saved, если она не существует
    saved_dir = Path(source_dir) / 'saved'
    saved_dir.mkdir(exist_ok=True)
    
    copied_count = 0
    
    # Обходим все файлы рекурсивно
    for root, dirs, files in os.walk(source_dir):
        # Исключаем директории, которые не нужно обходить
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        # Получаем относительный путь от source_dir
        root_path = Path(root)
        
        # Пропускаем саму папку saved
        if root_path == saved_dir or root_path.is_relative_to(saved_dir):
            continue
        
        for file in files:
            # Проверяем расширение файла
            if any(file.lower().endswith(ext) for ext in extensions):
                source_file = root_path / file
                target_file = saved_dir / file
                
                # Если файл с таким именем уже существует, добавляем префикс из пути
                if target_file.exists():
                    # Получаем имя родительской папки для уникальности
                    parent_name = root_path.name
                    target_file = saved_dir / f"{parent_name}_{file}"
                
                # Копируем файл
                shutil.copy2(source_file, target_file)
                print(f"Скопирован: {source_file} -> {target_file}")
                copied_count += 1
    
    print(f"\nВсего скопировано файлов: {copied_count}")
    print(f"Файлы сохранены в: {saved_dir.absolute()}")

if __name__ == "__main__":
    # Можете изменить параметры по необходимости
    copy_files_to_saved(
        source_dir='.',  # Текущая директория (родительский каталог)
        exclude_dirs=['.venv', '__pycache__', '.git', 'saved'],  # Исключаемые каталоги
        extensions=['.py', '.txt', '.json']  # Расширения для копирования
    )