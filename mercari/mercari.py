import os
import random
import re
import urllib.parse
from enum import Enum
from math import ceil
from collections import defaultdict
from time import sleep

import requests
from .DpopUtils import generate_DPOP

rootURL = "https://api.mercari.jp/"
rootProductURL = "https://jp.mercari.com/item/"
searchURL = "{}search_index/search".format(rootURL)
getItemURL = "{}items/get".format(rootURL)



class Item:
    def __init__(self, *args, **kwargs):
        self.id = kwargs['productID']
        self.productURL = "{}{}".format(rootProductURL, kwargs['productID'])
        self.imageURL = kwargs['imageURL']
        self.productName = kwargs['name']
        self.price = kwargs['price']
        self.condition = kwargs['condition']
        self.status = kwargs['status']
        self.soldOut = kwargs['status'] == "sold_out"
        self.updated = kwargs['updated']
        self.created = kwargs['created']
        

    @staticmethod
    def fromApiResp(apiResp):
        return Item(
            productID=apiResp['id'],
            name=apiResp["name"],
            price=apiResp["price"],
            status=apiResp['status'],
            imageURL=apiResp['thumbnails'][0],
            condition=apiResp['item_condition']["id"],
            itemCategory=apiResp['item_category']['name'],
            updated=apiResp['updated'],
            created=apiResp['created']
        )


def parse(resp):
    # returns [] if resp has no items on it
    # returns [Item's] otherwise
    if "catalog_details" in resp["data"]:
        return defaultdict(str, resp["data"]["catalog_details"])

    if "num_found" not in resp["meta"]:
        return defaultdict(str)

    if resp["meta"]["num_found"] == 0:
        return [], False

    respItems = resp["data"]
    return [Item.fromApiResp(item) for item in respItems], resp["meta"]["has_next"]


def fetch(baseURL, data, number_of_try=0):
    # let's build up the url ourselves
    # I know requests can do it, but I need to do it myself cause we need
    # special encoding!
    url = "{}?{}".format(
        baseURL,
        urllib.parse.urlencode(data)
    )

    DPOP = generate_DPOP(
        # let's see if this gets blacklisted, but it also lets them track
        uuid="Mercari Python Bot",
        method="GET",
        url=baseURL

    )

    headers = {
        'DPOP': DPOP,
        'X-Platform': 'web',  # mercari requires this header
        'Accept': '*/*',
        'Accept-Encoding': 'deflate, gzip'
    }
    r = requests.get(url, headers=headers)
    if not r.ok:
        if number_of_try > 5:
            r.raise_for_status()
        print(f"Error! Wait for {2**number_of_try}s")
        sleep(2**number_of_try)
        return fetch(baseURL, data, number_of_try+1)    
    return parse(r.json())


# returns an generator for Item objects
# keeps searching until no results so may take a while to get results back
def search(keywords, sort="created_time", order="desc", status="on_sale", limit=120):
    data = {
        "keyword": keywords,
        "limit": 120,
        "page": 0,
        "sort": sort,
        "order": order,
        "status": status,
    }
    has_next_page = True

    while has_next_page:
        items, has_next_page = fetch(searchURL, data)
        yield from items
        data['page'] += 1

def get_phone_details(item_id):
    data = {
        "id": item_id,
    }
    return fetch(getItemURL, data)
