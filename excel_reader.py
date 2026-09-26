import pandas as pd

class WBS:
    def __init__(self, path: str):
        self.path = path

    def parse_excel(self) -> pd.DataFrame:
        """Парсит Excel и нормализует колонки id / depends_on в строки."""
        df = pd.read_excel(self.path)

        # Приводим WBS-коды к строкам и убираем пробелы
        df["id"] = df["id"].astype(str).str.strip()
        df["depends_on"] = (
            df["depends_on"]
            .fillna("")
            .astype(str)
            .str.strip()
            .replace({"nan": "", "None": ""})
        )
        return df

    def build_load_order(self):
        """
        Строит порядок загрузки: родители идут раньше детей.
        Возвращает:
            order        — список WBS-кодов в порядке создания
            rows_by_wbs  — словарь {wbs_code: pandas.Series}
        """
        df = self.parse_excel()
        rows_by_wbs = {row["id"]: row for _, row in df.iterrows()}

        # Строим дерево: parent_wbs -> [children_wbs]
        children = {}
        roots = []
        for wbs, row in rows_by_wbs.items():
            parent = row["depends_on"]
            if not parent:
                roots.append(wbs)
            else:
                children.setdefault(parent, []).append(wbs)

        # Ключ сортировки: "1.10.2" -> [1, 10, 2] (числовой, а не лексикографический)
        def wbs_sort_key(wbs: str):
            parts = wbs.rstrip(".").split(".")
            return [int(p) for p in parts if p]

        # Обход в глубину (pre-order): родитель -> все его дети
        order = []
        def dfs(wbs):
            order.append(wbs)
            for child in sorted(children.get(wbs, []), key=wbs_sort_key):
                dfs(child)

        for root in sorted(roots, key=wbs_sort_key):
            dfs(root)

        return order, rows_by_wbs