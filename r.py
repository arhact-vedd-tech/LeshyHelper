import os
from pathlib import Path

def collect_code_to_single_file(root_dir='.', output_file='r.txt', exclude_dirs={'.venv', 'saved'}, extensions={'.txt', '.py', '.json'}):
    """
    Собирает код из всех файлов с указанными расширениями в один файл.
    
    Args:
        root_dir: корневая директория для поиска
        output_file: имя выходного файла
        exclude_dirs: директории для исключения
        extensions: расширения файлов для обработки
    """
    
    root_path = Path(root_dir).resolve()
    
    # Собираем все файлы
    files_to_process = []
    for dirpath, dirnames, filenames in os.walk(root_path):
        # Исключаем ненужные директории
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs]
        
        for filename in filenames:
            file_path = Path(dirpath) / filename
            if file_path.suffix in extensions:
                files_to_process.append(file_path)
    
    # Сортируем файлы для удобства
    files_to_process.sort()
    
    # Записываем всё в один файл
    with open(output_file, 'w', encoding='utf-8') as outfile:
        outfile.write("=" * 80 + "\n")
        outfile.write("СБОРКА КОДА ПРОЕКТА\n")
        outfile.write(f"Корневая директория: {root_path}\n")
        outfile.write(f"Количество файлов: {len(files_to_process)}\n")
        outfile.write("=" * 80 + "\n\n")
        
        for i, file_path in enumerate(files_to_process, 1):
            try:
                with open(file_path, 'r', encoding='utf-8') as infile:
                    content = infile.read()
                
                relative_path = file_path.relative_to(root_path)
                
                # Записываем разделитель и информацию о файле
                outfile.write("\n" + "=" * 80 + "\n")
                outfile.write(f"ФАЙЛ {i} ИЗ {len(files_to_process)}\n")
                outfile.write(f"Директория: {file_path.parent}\n")
                outfile.write(f"Относительный путь: {relative_path}\n")
                outfile.write(f"Имя файла: {file_path.name}\n")
                outfile.write(f"Размер: {len(content)} символов\n")
                outfile.write("=" * 80 + "\n\n")
                
                # Записываем содержимое файла
                outfile.write(content)
                outfile.write("\n")
                
            except Exception as e:
                outfile.write(f"\n!!! ОШИБКА при чтении файла {file_path}: {e}\n")
    
    print(f"Готово! Обработано {len(files_to_process)} файлов.")
    print(f"Результат сохранен в: {output_file}")
    return output_file

if __name__ == "__main__":
    # Можно указать свою директорию или оставить текущую
    # collect_code_to_single_file(root_dir='.', output_file='r.txt')
    
    # Или с указанием конкретного пути:
    collect_code_to_single_file(
        root_dir='.',  # замените на путь к вашему проекту
        output_file='r.txt',
        exclude_dirs={'.venv', 'saved', '__pycache__', '.git', '.idea', 'node_modules'},
        extensions={'.txt', '.py', '.json'}
    )