import logging
import os
from dotenv import load_dotenv

from projeqtor import Projeqtor
from excel_reader import WBS
from loader import ActivityLoader

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


if __name__ == "__main__":
    client = Projeqtor()

    # 2. Парсим Excel и строим порядок загрузки
    wbs = WBS(os.getenv("FILE_PATH"))
    order, rows_by_wbs = wbs.build_load_order()
    logging.info(f"Найдено задач: {len(order)}")
    logging.info(f"Порядок загрузки: {order}")

    # 3. Загружаем
    loader = ActivityLoader(
        projeqtor_client=client,
        project_id=int(os.getenv("PJ_DEFAULT_PROJECT_ID")),
        activity_type_id=int(os.getenv("PJ_DEFAULT_ACTIVITY_TYPE_ID")),
        status_id=int(os.getenv("PJ_DEFAULT_STATUS_ID")),
        planning_mode_id=int(os.getenv("PJ_DEFAULT_PLANNING_MODE_ID")),
    )

    mapping = loader.load(order, rows_by_wbs)

    logging.info(f"Загружено {len(mapping)} задач.")
    logging.info("Маппинг WBS -> ProjeQtOr id:")
    for wbs_code, pq_id in mapping.items():
        logging.info(f"  {wbs_code} -> {pq_id}")