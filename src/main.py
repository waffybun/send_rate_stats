import requests
import requests_cache
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path

requests_cache.install_cache('global_cache', expire_after=3600) # cache api responses for an hour so we don't need to keep getting them over and over

headers = {
    'accept': 'application/json',
}

rate_times = []
send_times = []
time_deltas = []
notes = []
notable_time_deltas = []

filter_demons = False # if false only log nondemons, if true only log demons
filter_platformers = False # if false only log classics, if true only log platformers
custom_level_search = False # if false run statistics from scraped ids, if true run statistics for only the provided ids

levels_to_count = 100

notable_time_difference = 12 if not filter_demons and not filter_platformers else 48 
# levels with a send-rate time difference past the threshold get printed separately at the end

def get_level_data(level_id, debug=False):
    link = f"https://api.senddb.dev/api/v1/level/{level_id}"
    response = requests.get(link, headers=headers)
    json_data = response.json() if response and response.status_code == 200 else None
    if json_data:
        level_name = json_data['name']
        creator = json_data['creator']['name']
        if debug: print(f"Checking stats for {level_name} by {creator} (ID {level_id})")
        sends = json_data['sends']
        if sends: 
            most_recent_send_time = sends[len(sends)-1]['timestamp']
            if debug:
                send_counter = 1
                for send in sends:
                    list_send_timestamp = float(send['timestamp'])/1000 # convert from ms to s
                    list_send_time = datetime.fromtimestamp(list_send_timestamp, tz=timezone.utc)
                    if debug: print(f"Time of send {send_counter}: {list_send_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    send_counter += 1
            last_send_timestamp = float(most_recent_send_time)/1000 # convert from ms to s
            send_time = datetime.fromtimestamp(last_send_timestamp, tz=timezone.utc)
            send_times.append(send_time)
            print(f"Time of {level_name} by {creator} (ID {level_id})'s most recent send: {send_time.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print(f"{level_name} by {creator} (ID {level_id}) was rated without any sends, or the level was rated before SendDB started tracking sends.")
            notes.append(f"{level_name} by {creator} (ID {level_id}) was rated without any sends, or the level was rated before SendDB started tracking sends.")
        if json_data['rate']:
            rate_timestamp = float(json_data['rate']['timestamp'])/1000 # convert from ms to s
            rate_time = datetime.fromtimestamp(rate_timestamp, tz=timezone.utc)
            time_difference = rate_time-send_time
            print(f"Time level was rated: {rate_time.strftime('%Y-%m-%d %H:%M:%S')}")
            rate_times.append(rate_time)
            print(f"Time between last send and level rate: {custom_format(time_difference)}")
            time_deltas.append(time_difference)
            if time_difference.total_seconds() / 3600 > notable_time_difference: # levels rated a very significant amount of time after the last send, depends on mode
                # convert the timedelta to a datetime
                total_seconds = time_difference.total_seconds()
                hours = int(total_seconds // 3600)
                minutes = int((total_seconds % 3600) // 60)
                seconds = int(total_seconds % 60)
                notable_time_deltas.append(f"{level_name} by {creator} (ID {level_id}) was rated {hours:02}:{minutes:02}:{seconds:02} after its last send.")
        else:
            print(f"{level_name} by {creator} (ID {level_id}) is not rated.")
    else:
        print(f"Level with ID {level_id} does not exist, or the API is unavailable.")
    print("")

def get_batch_level_data(id_list, debug=False):
    for id in id_list:
        get_level_data(id, debug)

def custom_format(td): # properly format timedeltas
    total_seconds = td.total_seconds()
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    return '{:02d}:{:02d}:{:02d}'.format(hours, minutes, seconds)

print("\nProgram starting. Please note all provided times are in UTC unless otherwise specified.\n")

if custom_level_search:
    input = input("Enter ID of level to search, or enter a list of IDs separated by spaces to batch search: ")
    id_list = input.split()
    print()
else:
    if filter_demons: print("Only searching for demons.")
    else: print ("Only searching for nondemons.")

    if filter_platformers: print("Only searching for platformers.")
    else: print("Only searching for classics (platformers excluded).")
    print()

    rated_level_list_filepath = Path(__file__).resolve().parents[1] / "files" / "Rated Levels List - Levels.csv"
    rates = pd.read_csv(rated_level_list_filepath, dtype=str)

    # take the list and start from the end
    # pick the last two levels, subtract 10 from the row number, repeat until 100 ids have been selected
    # for each id, check to see if demon or platformer and filter based on selections

    id_list = []
    current_position = 1 # last level in the array

    while len(id_list) < levels_to_count and current_position < len(rates):
        if current_position % 10 == 3:
            current_position += 8 # so the pattern should be 1, 2, 11, 12, 21, 22, etc...

        if current_position >= len(rates):
            print("Reached end of list with not enough matches.")
            break

        current_row = rates.iloc[-1*current_position]

        if filter_demons and current_row["Reward"] != "10⭐": 
            current_position += 1 # if sorting for only demons, skip nondemons
            continue
        if not filter_demons and current_row["Reward"] == "10⭐": 
            current_position += 1 # if sorting only for nondemons, skip demons
            continue 
        if filter_platformers and current_row["Gamemode"] == "⭐ Classic": 
            current_position += 1 # if sorting for only plats, skip classics
            continue 
        if not filter_platformers and current_row["Gamemode"] == "🌙 Platformer": 
            current_position += 1 # if sorting for only classics, skip plats
            continue 

        id_list.append(int(current_row["Level ID"]))
        #print(f"{int(current_row["Level ID"])} added to list")

        current_position += 1

get_batch_level_data(id_list)

robtop_tz = ZoneInfo("Europe/Stockholm")

"""
print("Times of the given levels' most recent send (converted to RobTop's timezone):")

for time in send_times:
    converted_time = time.astimezone(robtop_tz)
    print(converted_time.strftime('%H:%M:%S'))
print("")

print("Times that the given levels were rated at (converted to RobTop's timezone):")
for time in rate_times:
    converted_time = time.astimezone(robtop_tz)
    print(converted_time.strftime('%H:%M:%S'))
print("")

print("Time between each level's most recent send and when it got rated:")
for time in time_deltas:
    print(custom_format(time))
print("")
"""

print("Levels that have a higher than usual time difference between last send and rate:")
for level in notable_time_deltas:
    print(level)
print("")

if len(notes) > 0:
    print("Other noteworthy levels:")
    for level in notes:
        print(level)
    print("")


# TEMPORARY AI SLOP BELOW (just using this to see if i'm actually onto something, if i am i'll rewrite the code myself)

# 1. Process Data
rate_hours = [time.astimezone(robtop_tz).hour + time.astimezone(robtop_tz).minute / 60.0 for time in rate_times]
send_hours = [time.astimezone(robtop_tz).hour + time.astimezone(robtop_tz).minute / 60.0 for time in send_times]
delta_hours = [td.total_seconds() / 3600.0 for td in time_deltas]

# 24-hour bins
bins_2hr = list(range(0, 26, 2))
bin_centers_2hr = [h + 1 for h in bins_2hr[:-1]]
labels_2hr = [f"{h:02d}:00–{h+2:02d}:00" for h in bins_2hr[:-1]]

# --- Updated Delay Bins Logic ---
max_delta = max(delta_hours) if delta_hours else 24

# 1. Dynamically choose bin size based on how large the maximum delay is
if max_delta <= 24:
    bin_step = 2       
elif max_delta <= 250:
    bin_step = 4      
elif max_delta <= 500:
    bin_step = 8
elif max_delta <= 1000:
    bin_step = 16
else:
    bin_step = 48      

# 2. Build the bins using the adaptive step size
max_bin_limit = int(((max_delta // bin_step) + 1) * bin_step)
bins_delta = list(range(0, max_bin_limit + bin_step, bin_step))

# 3. Center the labels precisely between the custom bin edges
bin_centers_delta = [h + (bin_step / 2) for h in bins_delta[:-1]]
labels_delta = [f"{h}h–{h+bin_step}h" for h in bins_delta[:-1]]

# 2. Use layout='constrained' for automatic spacing between subplots
fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 16), layout='constrained')

# Chart 1: Rate Times
ax1.hist(rate_hours, bins=bins_2hr, color='skyblue', edgecolor='black', rwidth=0.85)
ax1.set_title("Frequency of Level Ratings by Time of Day (RobTop's Timezone)", fontsize=12, fontweight='bold', pad=10)
ax1.set_xlabel('Time of Day (2-Hour Intervals)', fontsize=10, labelpad=8)
ax1.set_ylabel('Levels Rated', fontsize=10)
ax1.set_xticks(bin_centers_2hr)
ax1.set_xticklabels(labels_2hr, rotation=35, ha='right')
ax1.grid(axis='y', linestyle='--', alpha=0.7)

# Chart 2: Send Times
ax2.hist(send_hours, bins=bins_2hr, color='thistle', edgecolor='black', rwidth=0.85)
ax2.set_title("Frequency of 'Successful' Sends by Time of Day (RobTop's Timezone)", fontsize=12, fontweight='bold', pad=10)
ax2.set_xlabel('Time of Day (2-Hour Intervals)', fontsize=10, labelpad=8)
ax2.set_ylabel('Levels Sent', fontsize=10)
ax2.set_xticks(bin_centers_2hr)
ax2.set_xticklabels(labels_2hr, rotation=35, ha='right')
ax2.grid(axis='y', linestyle='--', alpha=0.7)

# Chart 3: Time Elapsed Until Rated
ax3.hist(delta_hours, bins=bins_delta, color='lightgreen', edgecolor='black', rwidth=0.85)
ax3.set_title('Time Elapsed Between Most Recent Send and Level Rate', fontsize=12, fontweight='bold', pad=10)
ax3.set_xlabel('Delay Window (Hours)', fontsize=10, labelpad=8)
ax3.set_ylabel('Levels', fontsize=10)
ax3.set_xticks(bin_centers_delta)
ax3.set_xticklabels(labels_delta, rotation=45, ha='right')
ax3.grid(axis='y', linestyle='--', alpha=0.7)

plt.show()