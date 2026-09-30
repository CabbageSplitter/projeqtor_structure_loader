import os
import sys
import json
import logging
import shlex
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv, set_key
import cmd

import click

from projeqtor import Projeqtor
from excel_reader import WBS
from loader import ActivityLoader

# ---------- Логирование ----------
def get_log_path():
    if getattr(sys, 'frozen', False):
        base_path = Path(sys.executable).parent
    else:
        base_path = Path(__file__).parent
    return base_path / "loader.log"

log_path = get_log_path()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_path, encoding="utf-8"),
    ]
)
logger = logging.getLogger(__name__)


# ---------- Работа с .env ----------
def get_env_path():
    if getattr(sys, 'frozen', False):
        base_path = Path(sys.executable).parent
    else:
        base_path = Path(__file__).parent
    return base_path / ".env"


def ensure_env_exists(env_path: Path):
    if not env_path.exists():
        default_env = """# ProjeQtOr API настройки
PJ_URL=http://localhost:8080
PJ_LOGIN=admin
PJ_PASSWORD=
PJ_API_KEY=

# ID справочников
PJ_DEFAULT_PROJECT_ID=1
PJ_DEFAULT_ACTIVITY_TYPE_ID=1
PJ_DEFAULT_STATUS_ID=1
PJ_DEFAULT_PLANNING_MODE_ID=1
"""
        env_path.write_text(default_env, encoding="utf-8")
        logger.info(f"Создан файл конфигурации: {env_path}")


def reload_env():
    """Перечитать .env в os.environ."""
    env_path = get_env_path()
    ensure_env_exists(env_path)
    load_dotenv(env_path, override=True)


# ---------- Интерактивный shell ----------
class ProjeqtorShell(cmd.Cmd):
    intro = (
        "=" * 60 + "\n"
        "  ProjeQtOr Activity Loader — интерактивный режим\n"
        "  Введите 'help' или '?' для списка команд.\n"
        "  Введите 'exit' или 'quit' для выхода.\n"
        + "=" * 60 + "\n"
    )
    prompt = "projeqtor> "

    def __init__(self):
        super().__init__()
        reload_env()

    # --- Команды ---
    def do_load(self, arg):
        """load <excel_file> — загрузить деятельности из Excel."""
        if not arg:
            print("Укажите путь к Excel файлу: load tasks.xlsx")
            return
        excel_file = arg.strip()
        if not os.path.exists(excel_file):
            print(f"Файл не найден: {excel_file}")
            return
        try:
            reload_env()
            self._run_load(excel_file)
        except Exception as e:
            print(f"Ошибка: {e}")

    def do_test(self, arg):
        """test — проверить подключение к ProjeQtOr."""
        try:
            reload_env()
            client = Projeqtor()
            result = client.get_all("Project")
            projects = result.get("items", [])
            print(f"Подключение успешно! Найдено проектов: {len(projects)}")
            for proj in projects[:5]:
                print(f"  ID={proj['id']}: {proj['name']}")
        except Exception as e:
            print(f"Ошибка подключения: {e}")

    def do_config(self, arg):
        """config <show|set|get|edit|path> [args...] — управление конфигурацией."""
        parts = shlex.split(arg) if arg else []
        if not parts:
            print("Использование: config <show|set|get|edit|path>")
            return

        subcmd = parts[0]
        env_path = get_env_path()
        ensure_env_exists(env_path)

        if subcmd == "show":
            reload_env()
            print(f"Конфигурация ({env_path}):\n")
            keys = [
                "PJ_URL", "PJ_LOGIN", "PJ_PASSWORD", "PJ_API_KEY",
                "PJ_DEFAULT_PROJECT_ID", "PJ_DEFAULT_ACTIVITY_TYPE_ID",
                "PJ_DEFAULT_STATUS_ID", "PJ_DEFAULT_PLANNING_MODE_ID",
            ]
            for key in keys:
                value = os.getenv(key, "")
                if key in ["PJ_PASSWORD", "PJ_API_KEY"] and value:
                    value = "*" * (len(value) - 4) + value[-4:] if len(value) > 4 else "****"
                print(f"  {key} = {value}")
            print()

        elif subcmd == "set" and len(parts) >= 3:
            key, value = parts[1], parts[2]
            set_key(str(env_path), key, value)
            reload_env()
            print(f"Установлено: {key} = {value}")

        elif subcmd == "set":
            print("Использование: config set KEY VALUE")

        elif subcmd == "get" and len(parts) >= 2:
            reload_env()
            value = os.getenv(parts[1], "")
            print(value if value else f"Параметр {parts[1]} не найден")

        elif subcmd == "edit":
            if sys.platform == "win32":
                os.startfile(env_path)
            elif sys.platform == "darwin":
                os.system(f"open {env_path}")
            else:
                os.system(f"xdg-open {env_path}")
            print(f"Открыт файл: {env_path}")

        elif subcmd == "path":
            print(env_path)

        else:
            print("Неизвестная подкоманда. Доступно: show, set, get, edit, path")

    def do_env(self, arg):
        """env — показать путь к .env файлу (алиас для config path)."""
        print(get_env_path())

    def do_exit(self, arg):
        """exit — выйти из программы."""
        print("До свидания!")
        return True  # True = выйти из цикла cmdloop

    def do_quit(self, arg):
        """quit — выйти из программы."""
        return self.do_exit(arg)

    def do_EOF(self, arg):
        """Ctrl+D — выход."""
        print()
        return self.do_exit(arg)

    # --- Вспомогательные методы ---
    def _run_load(self, excel_file: str):
        client = Projeqtor()
        wbs = WBS(excel_file)
        order, rows_by_wbs = wbs.build_load_order()
        print(f"Найдено задач: {len(order)}")
        print(f"Порядок: {order}\n")

        loader = ActivityLoader(
            projeqtor_client=client,
            project_id=int(os.getenv("PJ_DEFAULT_PROJECT_ID", "1")),
            activity_type_id=int(os.getenv("PJ_DEFAULT_ACTIVITY_TYPE_ID", "1")),
            status_id=int(os.getenv("PJ_DEFAULT_STATUS_ID", "1"))
        )
        mapping = loader.load(order, rows_by_wbs)
        print(f"Загружено {len(mapping)} задач.")
        for wbs_code, pq_id in mapping.items():
            print(f"  {wbs_code} -> {pq_id}")




    # --- Автодополнение по Tab ---
    def complete_config(self, text, line, begidx, endidx):
        subcmds = ["show", "set", "get", "edit", "path"]
        return [s for s in subcmds if s.startswith(text)]

    def complete_help(self, text, line, begidx, endidx):
        cmds = self.get_names()
        cmds = [c[3:] for c in cmds if c.startswith("do_")]
        return [c for c in cmds if c.startswith(text)]

    # --- Обработка пустого ввода и ошибок ---
    def emptyline(self):
        """Не повторять последнюю команду при пустом вводе."""
        pass

    def default(self, line):
        print(f"Неизвестная команда: '{line}'. Введите 'help' для списка команд.")


# ---------- Обычный CLI через click (для запуска с аргументами) ----------
@click.group()
def cli():
    """ProjeQtOr Activity Loader."""
    pass

@cli.command()
@click.argument("excel_file", type=click.Path(exists=True))
def load(excel_file):
    """Загрузить деятельности из Excel."""
    reload_env()
    shell = ProjeqtorShell()
    shell._run_load(excel_file)

@cli.command()
def test():
    """Проверить подключение к ProjeQtOr."""
    reload_env()
    try:
        client = Projeqtor()
        result = client.get_all("Project")
        projects = result.get("items", [])
        print(f"Подключение успешно! Найдено проектов: {len(projects)}")
    except Exception as e:
        print(f"Ошибка: {e}")
        sys.exit(1)

@cli.command("shell")
def shell_cmd():
    """Запустить интерактивный режим."""
    ProjeqtorShell().cmdloop()


# ---------- Точка входа ----------
if __name__ == "__main__":
    # Если аргументов нет — запускаем интерактивный shell
    if len(sys.argv) == 1:
        try:
            ProjeqtorShell().cmdloop()
        except KeyboardInterrupt:
            print("\n\nПрервано пользователем. До свидания!")
        sys.exit(0)

    # Если есть аргументы — работаем через click (обратная совместимость)
    try:
        cli(standalone_mode=False)
    except click.exceptions.UsageError as e:
        print(f"{e.message}")
    except SystemExit:
        pass
    except Exception as e:
        print(f"Ошибка: {e}")
    finally:
        # Ждём нажатия клавиши, если запускали с аргументами
        if len(sys.argv) > 1:
            input("Нажмите Enter для выхода...")