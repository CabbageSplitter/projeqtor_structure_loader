from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ActivityLoader:
    """Загружает дерево деятельностей из Excel в ProjeQtOr."""

    def __init__(
        self,
        projeqtor_client,
        project_id: int,
        activity_type_id: int,
        status_id: int,
        planning_mode_id: int,
    ):
        self.client = projeqtor_client
        self.project_id = project_id
        self.activity_type_id = activity_type_id
        self.status_id = status_id
        self.planning_mode_id = planning_mode_id

        # Маппинг: WBS-код из Excel -> id в ProjeQtOr
        self.wbs_to_pq_id: dict[str, int] = {}

    def _build_activity_payload(self, wbs: str, row) -> dict:
        """Формирует JSON для создания Activity."""
        # Название = WBS + имя из Excel (по требованию)
        name = f"{wbs} {row['name']}".strip()

        payload = {
            "name": name,
            "idActivityType": self.activity_type_id,
            "idProject": self.project_id,
            "idStatus": self.status_id,
            "creationDate": datetime.now().strftime("%Y-%m-%d"),
            "idActivityPlanningMode": self.planning_mode_id,
            "ActivityPlanningElement": {"progress": 0},
        }

        # Если есть родитель — подставляем его ProjeQtOr id
        parent_wbs = row["depends_on"]
        if parent_wbs:
            if parent_wbs not in self.wbs_to_pq_id:
                raise RuntimeError(
                    f"Родитель '{parent_wbs}' для '{wbs}' ещё не загружен. "
                    f"Проверьте корректность depends_on в Excel."
                )
            payload["idActivity"] = self.wbs_to_pq_id[parent_wbs]

        return payload

    def load(self, order: list[str], rows_by_wbs: dict) -> dict[str, int]:
        """Загружает все задачи в порядке order. Возвращает маппинг WBS -> PQ id."""
        total = len(order)
        for idx, wbs in enumerate(order, start=1):
            row = rows_by_wbs[wbs]
            payload = self._build_activity_payload(wbs, row)

            result = self.client.post_activity(payload)
            items = result.get("items", [])

            if not items or items[0].get("apiResult") != "OK":
                raise RuntimeError(
                    f"[{idx}/{total}] Ошибка создания '{wbs}': {result}"
                )

            pq_id = items[0]["id"]
            self.wbs_to_pq_id[wbs] = pq_id
            logger.info(
                f"[{idx}/{total}] WBS={wbs} -> ProjeQtOr id={pq_id} | name='{payload['name']}'"
            )

        return self.wbs_to_pq_id