from projeqtor import Projeqtor
import json
import time

tickets = [
    42748, 42802, 41141, 41101, 42688, 42687, 42510, 41952, 41951,
    41939, 41937, 41935, 41934, 41924, 41922, 41880, 41867, 41859,
    41882, 43416, 43417, 43418, 43419, 40822, 42410, 42168, 41501,
    42601, 42705, 41078, 42257, 40991, 40994, 41065, 42266, 40979,
    40981, 40987, 41003, 41006, 41009, 42181, 42247
]

# tickets = [42748]

for ticket in tickets:
    data = Projeqtor(ticket)
    data_ = data.get_tickets()
    with open (f'tickets/jsons/{str(ticket)}.json', 'w', encoding='utf-8') as file:
        json.dump(data_, file, ensure_ascii=False, indent = 4)
    time.sleep(2)