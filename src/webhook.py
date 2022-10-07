'''
References:
    https://realpython.com/api-integration-in-python/
    https://discord.com/developers/docs/resources/webhook
'''

import requests
from typing import Union

from mycredentials import WEBHOOK_ID, WEBHOOK_TOKEN

class Webhook():

    URL_TEMPLATE = "https://discord.com/api/webhooks/{id}/{token}{params}"

    def __init__(self, id: Union[int, str], token: str):
        self.id = id
        self.token = token

    def generate_url(self, wait: bool=False, thread_id: Union[int, str]=""):
        """
        Generates an URL for API calls.

        Parameters:
            wait: (optional) Waits for server confirmation of message send before response
            thread_id: (optional) Send a message to the specified thread within a webhook's channel

        Returns:
            An API URL as `str` type
        """

        # Setup query parameters
        query_params = []
        if wait == True:
            query_params.append("wait=true")
        if thread_id != "":
            query_params.append("thread_id={}".format(thread_id))
        if len(query_params) > 0:
            params = "?" + "&".join(query_params)
        else:
            params = ""

        # Generate api url
        url = self.URL_TEMPLATE.format(
            id=self.id,
            token=self.token,
            params=params
        )

        return url
    
    def get_info(self) -> dict:
        """
        Retrieves the basic info of the webhook.

        Returns:
            A `dict` object containing the info
        """
        response: requests.Response = requests.get(self.generate_url())

        if response.status_code != 200:
            print("response code: {}".format(response.status_code))

        return response.json()

def demo():
    msg = "A simple demo of using webhook in forum channels.\nFor more details, visit https://discord.com/developers/docs/resources/webhook"
    print(msg)

    # Create webhook object
    webhook = Webhook(WEBHOOK_ID, WEBHOOK_TOKEN)

    # GET Webhook
    webhook_info = webhook.get_info()
    print(webhook_info)

    # Send message by creating a new thread
    # You need to specify a "thread_name" to create a thread 
    params = {
        "content": "test",
        "thread_name": "Test",
        "avatar_url": "https://i.imgur.com/dGOpgPp.png", # Override Webhook avatar 
        "username": "I Changed My Name!", # Override Webhook name
    }
    print(webhook.generate_url(wait=True))
    response: requests.Response = requests.post(webhook.generate_url(wait=True), json=params)
    print(response.status_code, response.json())

    # Send message at a existing thread
    # You need to specify the thread id in the url, not in the JSON params
    print(response.json()["id"]) # Using the thread we just created
    params = {
        "content": "Hello World!",
    }
    thread_id = response.json()["id"]
    response: requests.Response = requests.post(webhook.generate_url(wait=True, thread_id=thread_id), json=params)
    print(response.status_code, response.json())

if __name__ == "__main__":
    demo()