import json
import httpx

class Projeqtor:

    def __init__(self, ticket_id):
        self.base_url = '.'
        self.ticket_id = ticket_id
        self.username = '.'  
        self.password = '.' 

    def get_tickets(self):
        url = f"{self.base_url}?uri=Ticket/search/id={self.ticket_id}"
        
        # params = {
        #     'uri': f'Ticket/search/id={self.ticket_id}',
        # }
        
        with httpx.Client(auth=(self.username, self.password)) as client:

            response = client.get(
                url,
                # params=params
            )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            items = data.get('items', [])
            return items
        else:
            # return {"error": response.text, "status": response.status_code}
            return(response.status_code)
