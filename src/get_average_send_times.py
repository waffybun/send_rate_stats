# not part of the real program, just reference data
import requests, requests_cache
import json

requests_cache.install_cache('global_cache', allowable_methods=('GET', 'HEAD', 'POST'), expire_after=3600) # cache api responses for an hour, results in stale data but not a big deal


# documentation i used to figure out what i'm looking at:
# https://boomlings.dev/endpoints/levels/getGJLevels21
# https://boomlings.dev/resources/server/level

num_pages = 10
full_level_list = []


def get_levels_from_sent_tab(num_pages):
    url = "https://www.boomlings.com/database/getGJLevels21.php"
    headers = {
    "User-Agent": ""
    }
    # get every level in sent tab from the past num_pages pages (skip the first page because it might not be in senddb yet)
    for page in range (1, num_pages+1):
        data = {
        "gameVersion": 22,
        "binaryVersion": 47,
        "type": 27, # sent tab
        "secret": "Wmfd2893gb7",
        "page": page
        }
        req = requests.post(url=url, data=data, headers=headers)
        # the response is formatted really really weirdly, so this is my attempt at parsing it
        # it is NOT fun
        levels = req.text.split("|")
        #print("\n")
        for level in levels[:9]: # sometimes levels become unlisted after being sent so there are only 9, limiting this number can (mostly) prevent out of bounds issues
            level_info = level.split(":")
            level_response_dict = {}
            for i in range(0, len(level_info) - 1, 2):
                level_response_dict.update({level_info[i]: level_info[i+1]})
            level_id = level_response_dict.get("1")
            level_name = level_response_dict.get("2")
            full_level_list.append(int(level_id))

    level_dict = { "level_ids": full_level_list}
    json_body = json.dumps(level_dict, indent=2)
    return(json_body)

# now, feed id list into senddb and get timestamps
# i learned a better way to do this, senddb has the ability to send batch requests for level info

def look_up_send_times(level_ids):
    headers = {
        'accept': 'application/json',
    }
    url = f"https://api.senddb.dev/api/v1/level/batch"
    response = requests.post(url=url, data=level_ids, headers=headers)
    json_data = response.json() if response and response.status_code == 200 else None


list_of_ids = get_levels_from_sent_tab(num_pages)
#look_up_send_times(list_of_ids)
print(list_of_ids)
