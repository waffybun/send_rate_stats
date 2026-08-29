# not part of the real program, just reference data
import requests, requests_cache
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import pandas as pd
import plotly.express as px
from pathlib import Path

requests_cache.install_cache('global_cache', allowable_methods=('GET', 'HEAD', 'POST'), expire_after=3600) # cache api responses for an hour, results in stale data but not a big deal


# documentation i used to figure out what i'm looking at:
# https://boomlings.dev/endpoints/levels/getGJLevels21
# https://boomlings.dev/resources/server/level

num_pages = 50
full_level_list = []
robtop_tz = ZoneInfo("Europe/Stockholm")

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

    #level_dict = { "level_ids": full_level_list}
    #json_body = json.dumps(level_dict, indent=2)
    #return(json_body)
    return(full_level_list)

# now, feed id list into senddb and get timestamps
# if only the batch level lookup on the api actually worked in batches...

def look_up_send_times(level_ids):
    headers = {
        'accept': 'application/json',
    }
    send_times = []
    counter = 1
    for level_id in level_ids:
        print(f"Looking up level {counter} of {len(level_ids)}")
        url = f"https://api.senddb.dev/api/v1/level/{level_id}"
        response = requests.get(url=url, headers=headers)
        json_data = response.json() if response and response.status_code == 200 else None
        if json_data:
            sends = json_data['sends']
            if sends: 
                most_recent_send_time = sends[len(sends)-1]['timestamp']
                last_send_timestamp = float(most_recent_send_time)/1000 # convert from ms to s
                send_time = datetime.fromtimestamp(last_send_timestamp, tz=timezone.utc)
                send_times.append(send_time)
        counter += 1
    return send_times

list_of_ids = get_levels_from_sent_tab(num_pages)
send_times = look_up_send_times(list_of_ids)
send_hours = [time.astimezone(robtop_tz).hour + time.astimezone(robtop_tz).minute / 60.0 for time in send_times]

send_times_filepath = Path(__file__).resolve().parents[1] / "files" / "send_times_hours.txt"
with open(send_times_filepath, "w") as file:
    for time in send_hours:
        file.write(f"{time}\n")

# same ai slop code as before, sowwy

actual_max = 24
max_bin_limit = int(((actual_max // 2) + 1) * 2) # Auto-ends on an even interval

bins_delta = list(range(0, max_bin_limit + 2, 2)) # 2-hour wide bins forever
bin_centers_delta = [h + 1 for h in bins_delta[:-1]]
labels_delta = [f"{h}h–{h+2}h" for h in bins_delta[:-1]]

# Standard 24-hour bins for Time-of-Day graphs
bins_2hr = list(range(0, 26, 2))
bin_centers_2hr = [h + 1 for h in bins_2hr[:-1]]
labels_2hr = [f"{h:02d}:00–{h+2:02d}:00" for h in bins_2hr[:-1]]

 # --- CHART 2: Fixed Send Times ---
df_send = pd.DataFrame({"Hours": send_hours})
fig2 = px.histogram(
    df_send, 
    x="Hours",
    range_x=[0, 26],
    nbins=13,
    title="Frequency of Sends by Time of Day (RobTop's Timezone)"
)
fig2.update_layout(
    xaxis=dict(tickmode='array', tickvals=bin_centers_2hr, ticktext=labels_2hr, tickangle=35),
    yaxis_title=dict(text="Levels"),
    bargap=0.15,
    title_font=dict(size=14, family="Arial"),  
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=60, r=60, t=60, b=90)
)
fig2.update_traces(
    xbins=dict(start=0, end=26, size=2),
    marker_color='thistle', 
    marker_line_color='white', 
    marker_line_width=0.5
)
fig2.show()