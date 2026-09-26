import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv, set_key, unset_key

import click

from projeqtor import Projeqtor
from excel_reader import WBS
from loader import ActivityLoader

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def get_env_path():
    """Возвращает путь к .env файлу (рядом с exe или в текущей директории)."""
    if getattr(sys, 'frozen', False):
        # Если запущено из exe
        base_path = Path(sys.executable).parent
    else:
        # Если запущено из Python
        base_path = Path(__file__).parent
    return base_path / ".env"


def ensure_env_exists(env_path: Path):
    """Создаёт .env с дефолтными значениями, если его нет."""
    if not env_path.exists():
        default_env = """# ProjeQtOr API настройки
PJ_URL=http://localhost:8080
PJ_LOGIN=admin
PJ_PASSWORD=
PJ_API_KEY=

# ID справочников (узнайте через GET-запросы или в UI)
PJ_DEFAULT_PROJECT_ID=1
PJ_DEFAULT_ACTIVITY_TYPE_ID=1
PJ_DEFAULT_STATUS_ID=1
PJ_DEFAULT_PLANNING_MODE_ID=1
"""
        env_path.write_text(default_env, encoding="utf-8")
        logger.info(f"Создан файл конфигурации: {env_path}")
        logger.info("Отредактируйте .env перед использованием (команда: config edit)")


@click.group()
def cli():
    """ProjeQtOr Activity Loader - загрузка деятельностей из Excel в ProjeQtOr."""
    pass


@cli.command()
@click.argument("excel_file", type=click.Path(exists=True))
def load(excel_file):
    """Загрузить деятельности из Excel файла в ProjeQtOr."""
    env_path = get_env_path()
    ensure_env_exists(env_path)
    load_dotenv(env_path)

    # Проверяем обязательные параметры
    required_vars = ["PJ_URL", "PJ_LOGIN", "PJ_PASSWORD", "PJ_API_KEY"]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        logger.error(f"Не заполнены обязательные параметры в .env: {', '.join(missing)}")
        logger.error("Выполните: config edit")
        sys.exit(1)

    try:
        # 1. Клиент ProjeQtOr
        client = Projeqtor()

        # 2. Парсим Excel
        wbs = WBS(excel_file)
        order, rows_by_wbs = wbs.build_load_order()
        logger.info(f"Найдено задач: {len(order)}")

        # 3. Загружаем
        loader = ActivityLoader(
            projeqtor_client=client,
            project_id=int(os.getenv("PJ_DEFAULT_PROJECT_ID", "1")),
            activity_type_id=int(os.getenv("PJ_DEFAULT_ACTIVITY_TYPE_ID", "1")),
            status_id=int(os.getenv("PJ_DEFAULT_STATUS_ID", "1")),
            planning_mode_id=int(os.getenv("PJ_DEFAULT_PLANNING_MODE_ID", "1")),
        )

        mapping = loader.load(order, rows_by_wbs)

        logger.info(f"\n✅ Загружено {len(mapping)} задач.")
        logger.info("Маппинг WBS -> ProjeQtOr id:")
        for wbs_code, pq_id in mapping.items():
            logger.info(f"  {wbs_code} -> {pq_id}")

    except Exception as e:
        logger.error(f"Ошибка: {e}")
        sys.exit(1)


@cli.group()
def config():
    """Управление конфигурацией (.env)."""
    pass


@config.command("show")
def config_show():
    """Показать текущую конфигурацию."""
    env_path = get_env_path()
    ensure_env_exists(env_path)
    load_dotenv(env_path)

    click.echo("Текущая конфигурация:")
    click.echo(f"Файл: {env_path}\n")

    for key in ["PJ_URL", "PJ_LOGIN", "PJ_PASSWORD", "PJ_API_KEY",
                "PJ_DEFAULT_PROJECT_ID", "PJ_DEFAULT_ACTIVITY_TYPE_ID",
                "PJ_DEFAULT_STATUS_ID", "PJ_DEFAULT_PLANNING_MODE_ID"]:
        value = os.getenv(key, "")
        # Скрываем пароль и API ключ
        if key in ["PJ_PASSWORD", "PJ_API_KEY"] and value:
            value = "*" * (len(value) - 4) + value[-4:]
        click.echo(f"  {key} = {value}")
    click.echo()


@config.command("edit")
def config_edit():
    """Открыть .env в текстовом редакторе."""
    env_path = get_env_path()
    ensure_env_exists(env_path)

    # Пытаемся открыть в системном редакторе
    if sys.platform == "win32":
        os.startfile(env_path)
    elif sys.platform == "darwin":
        os.system(f"open {env_path}")
    else:
        os.system(f"xdg-open {env_path}")

    click.echo(f"Открыт файл: {env_path}")


@config.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key, value):
    """Установить значение параметра. Пример: config set PJ_URL http://example.com"""
    env_path = get_env_path()
    ensure_env_exists(env_path)

    set_key(str(env_path), key, value)
    click.echo(f"Установлено: {key} = {value}")


@config.command("get")
@click.argument("key")
def config_get(key):
    """Получить значение параметра. Пример: config get PJ_URL"""
    env_path = get_env_path()
    ensure_env_exists(env_path)
    load_dotenv(env_path)

    value = os.getenv(key, "")
    if value:
        click.echo(value)
    else:
        click.echo(f"Параметр {key} не найден или пуст")
        sys.exit(1)


@config.command("path")
def config_path():
    """Показать путь к файлу .env."""
    env_path = get_env_path()
    click.echo(env_path)


@cli.command()
def test():
    """Проверить подключение к ProjeQtOr."""
    env_path = get_env_path()
    ensure_env_exists(env_path)
    load_dotenv(env_path)

    try:
        client = Projeqtor()
        # Пробуем получить список проектов
        result = client.get_all("Project")
        projects = result.get("items", [])
        click.echo(f"Подключение успешно!")
        click.echo(f"Найдено проектов: {len(projects)}")
        if projects:
            click.echo("\nПервые 5 проектов:")
            for proj in projects[:5]:
                click.echo(f"  ID={proj['id']}: {proj['name']}")
    except Exception as e:
        click.echo(f"Ошибка подключения: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli()