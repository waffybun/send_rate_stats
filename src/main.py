import requests
import requests_cache
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path
import plotly.express as px

import streamlit as st

requests_cache.install_cache('global_cache', expire_after=3600) # cache api responses for an hour so we don't need to keep getting them over and over

headers = {
    'accept': 'application/json',
}

rate_times = []
send_times = []
time_deltas = []
notes = []
notable_time_deltas = []

extra_info = st.empty()

if 'run_awarded' not in st.session_state:
    st.session_state['run_awarded'] = False

if 'run_custom' not in st.session_state:
    st.session_state['run_custom'] = False

if 'filter_demons' not in st.session_state:
    st.session_state['filter_demons'] = False

if 'filter_platformers' not in st.session_state:
    st.session_state['filter_platformers'] = False

if 'debug' not in st.session_state:
    st.session_state['debug'] = False

if 'mode' not in st.session_state:
    st.session_state['mode'] = None

if 'debug_expander' not in st.session_state:
    st.session_state['debug_expander'] = None

""" 
# Send/Rate Statistics Visualizer
Please note all provided times are in UTC unless otherwise specified.
"""

col1, col2 = st.columns(2)
with col2:
    if st.button('Get statistics from custom IDs'):
        st.session_state['mode'] = 'custom'
with col1:
    if st.button("Run statistics on Awarded Tab levels"):
        st.session_state['mode'] = 'awarded'

notable_time_difference = 12 # defaults to 12 hours
# levels with a send-rate time difference past the threshold get printed separately at the end

if st.session_state['mode'] == 'awarded':
    filter_demons = st.checkbox('Demons only?', key='filter_demons')
    filter_platformers = st.checkbox('Platformers only?', key='filter_platformers')
    debug = st.checkbox('Extra debug info?', key='debug')
    levels_to_count = st.number_input("Number of levels to search from", min_value=1, max_value=100, step=1, value=100, key='levels_to_count')
    notable_time_difference = 12 if not filter_demons and not filter_platformers else 48 
    run_awarded = st.button("Run", key="run_awarded")
elif st.session_state['mode'] == 'custom':
    st.text_input("Enter ID(s), space-separated:", key="IDs")
    run_custom = st.button("Run", key="run_custom")

def get_level_data(level_id, debug, log=None):
    link = f"https://api.senddb.dev/api/v1/level/{level_id}"
    response = requests.get(link, headers=headers)
    json_data = response.json() if response and response.status_code == 200 else None
    if json_data:
        level_name = json_data['name']
        creator = json_data['creator']['name']
        if log:
            log.write(f"Checking stats for {level_name} by {creator} (ID {level_id})")
        sends = json_data['sends']
        if sends: 
            most_recent_send_time = sends[len(sends)-1]['timestamp']
            if debug:
                send_counter = 1
                for send in sends:
                    list_send_timestamp = float(send['timestamp'])/1000 # convert from ms to s
                    list_send_time = datetime.fromtimestamp(list_send_timestamp, tz=timezone.utc)
                    if debug and log: log.write(f"Time of send {send_counter}: {list_send_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    send_counter += 1
            last_send_timestamp = float(most_recent_send_time)/1000 # convert from ms to s
            send_time = datetime.fromtimestamp(last_send_timestamp, tz=timezone.utc)
            send_times.append(send_time)
            if log and not debug:
                log.write(f"Time of {level_name} by {creator} (ID {level_id})'s most recent send: {send_time.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            if log:
                log.write(f"{level_name} by {creator} (ID {level_id}) was rated without any sends, or the level was rated before SendDB started tracking sends.")
            notes.append(f"{level_name} by {creator} (ID {level_id}) was rated without any sends, or the level was rated before SendDB started tracking sends.")
        if json_data['rate']:
            rate_timestamp = float(json_data['rate']['timestamp'])/1000 # convert from ms to s
            rate_time = datetime.fromtimestamp(rate_timestamp, tz=timezone.utc)
            time_difference = rate_time-send_time
            if log:
                log.write(f"Time level was rated: {rate_time.strftime('%Y-%m-%d %H:%M:%S')}")
            rate_times.append(rate_time)
            if log:
                log.write(f"Time between last send and level rate: {custom_format(time_difference)}")
            time_deltas.append(time_difference)
            if time_difference.total_seconds() / 3600 > notable_time_difference: # levels rated a very significant amount of time after the last send, depends on mode
                # convert the timedelta to a datetime
                total_seconds = time_difference.total_seconds()
                hours = int(total_seconds // 3600)
                minutes = int((total_seconds % 3600) // 60)
                seconds = int(total_seconds % 60)
                notable_time_deltas.append(f"{level_name} by {creator} (ID {level_id}) was rated {hours:02}:{minutes:02}:{seconds:02} after its last send.")
        else:
            if log:
                log.write(f"{level_name} by {creator} (ID {level_id}) is not rated.")
    else:
        if log:
            log.write(f"Level with ID {level_id} does not exist, is not in the SendDB database (likely too old), or the API is unavailable.")
            notes.append(f"Level with ID {level_id} does not exist, is not in the SendDB database (likely too old), or the API is unavailable.")
    log.write("\n")

def get_batch_level_data(id_list, log=None):
    progress = st.empty()
    bar = st.progress(0)
    count = 1
    max = len(id_list)
    for id in id_list:
        progress.text(f'Processing level {count}/{max}')
        bar.progress(int(count/max*100))
        get_level_data(id, st.session_state['debug'], log)
        count += 1
    progress.empty()
    bar.empty()

def custom_format(td): # properly format timedeltas
    total_seconds = td.total_seconds()
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    return '{:02d}:{:02d}:{:02d}'.format(hours, minutes, seconds)

if st.session_state['run_custom']:
    st.session_state['debug_expander'] = st.expander("Level-by-level details", expanded=False)
    log = st.session_state['debug_expander']
    id_list = st.session_state['IDs'].split()

if st.session_state['run_awarded']:
    st.session_state['debug_expander'] = st.expander("Level-by-level details", expanded=False)
    log = st.session_state['debug_expander']
    if st.session_state['filter_demons']:
        if log:
            log.write("Only searching for demons.")
    else: 
        if log:
            log.write("Only searching for nondemons.")

    if st.session_state['filter_platformers']: 
        if log:
            log.write("Only searching for platformers.")
    else: 
        if log:
            log.write("Only searching for classics (platformers excluded).")
    log.write("\n")

    rated_level_list_filepath = Path(__file__).resolve().parents[1] / "files" / "Rated Levels List - Levels.csv"
    rates = pd.read_csv(rated_level_list_filepath, dtype=str)

    # take the list and start from the end
    # pick the last two levels, subtract 10 from the row number, repeat until 100 ids have been selected
    # for each id, check to see if demon or platformer and filter based on selections

    id_list = []
    current_position = 1 # last level in the array

    while len(id_list) < st.session_state['levels_to_count'] and current_position < len(rates):
        if current_position % 10 == 3:
            current_position += 8 # so the pattern should be 1, 2, 11, 12, 21, 22, etc...

        if current_position >= len(rates):
            print("Reached end of list with not enough matches.")
            break

        current_row = rates.iloc[-1*current_position]

        if st.session_state['filter_demons'] and not "10" in current_row["Reward"]: 
            current_position += 1 # if sorting for only demons, skip nondemons
            continue
        if not st.session_state['filter_demons'] and "10" in current_row["Reward"]: 
            current_position += 1 # if sorting only for nondemons, skip demons
            continue 
        if st.session_state['filter_platformers'] and current_row["Gamemode"] == "⭐ Classic": 
            current_position += 1 # if sorting for only plats, skip classics
            continue 
        if not st.session_state['filter_platformers'] and current_row["Gamemode"] == "🌙 Platformer": 
            current_position += 1 # if sorting for only classics, skip plats
            continue 

        id_list.append(int(current_row["Level ID"]))
        #print(f"{int(current_row["Level ID"])} added to list")

        current_position += 1

if st.session_state['run_custom'] or st.session_state['run_awarded']:

    log = st.session_state['debug_expander']
    get_batch_level_data(id_list, log=log)

    robtop_tz = ZoneInfo("Europe/Stockholm")

    notes_exp = st.expander("Notes", expanded=True)
    if len(notable_time_deltas) > 0:
        notes_exp.write("Levels that have a higher than usual time difference between last send and rate:")
        for level in notable_time_deltas:
            notes_exp.write(level)
        notes_exp.write("\n")

    if len(notes) > 0:
        notes_exp.write("Noteworthy levels:")
        for level in notes:
            notes_exp.write(level)
        notes_exp.write("\n")


    # TEMPORARY AI SLOP BELOW (just using this to see if i'm actually onto something, if i am i'll rewrite the code myself)

      # 1. Process Data
    rate_hours = [time.astimezone(robtop_tz).hour + time.astimezone(robtop_tz).minute / 60.0 for time in rate_times]
    send_hours = [time.astimezone(robtop_tz).hour + time.astimezone(robtop_tz).minute / 60.0 for time in send_times]
    
    # --- FIXED DELAY LOGIC (Capping Outliers for Readability) ---
    raw_delta_hours = [td.total_seconds() / 3600.0 for td in time_deltas]
    
    # Cap any delay greater than 24 hours to exactly 25 hours so it lands in a final bucket
    delta_hours = [h if h <= 24.0 else 25.0 for h in raw_delta_hours]

    # Create explicit layout labels up to 24 hours, plus a catch-all block
    bins_delta = list(range(0, 26, 2)) # [0, 2, 4, ... 24]
    bin_centers_delta = [h + 1 for h in bins_delta[:-1]]
    bin_centers_delta.append(25.0)     # Place center for the final bucket
    
    labels_delta = [f"{h}h–{h+2}h" for h in bins_delta[:-1]]
    labels_delta.append("24h+")        # Appended label for outliers

    # Standard 24-hour bins for Time-of-Day graphs
    bins_2hr = list(range(0, 26, 2))
    bin_centers_2hr = [h + 1 for h in bins_2hr[:-1]]
    labels_2hr = [f"{h:02d}:00–{h+2:02d}:00" for h in bins_2hr[:-1]]


    # --- CHART 1: Fixed 2-Hour Bars & Margins ---
    df_rate = pd.DataFrame({"Hours": rate_hours})
    fig1 = px.histogram(
        df_rate, 
        x="Hours", 
        range_x=[0, 26],
        nbins=13, # Forces exactly 13 bars across 26 units
        title="Frequency of Level Ratings by Time of Day (RobTop's Timezone)"
    )
    fig1.update_layout(
        xaxis=dict(tickmode='array', tickvals=bin_centers_2hr, ticktext=labels_2hr, tickangle=35),
        bargap=0.15,
        title_font=dict(size=14, family="Arial"),
        template="plotly_dark",  
        paper_bgcolor="rgba(0,0,0,0)",  
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=60, r=60, t=60, b=90) # <-- Fixed edge cropping
    )
    # Strictly enforce individual bar boundaries via xbins
    fig1.update_traces(
        xbins=dict(start=0, end=26, size=2), 
        marker_color='skyblue', 
        marker_line_color='white', 
        marker_line_width=0.5
    )
    st.plotly_chart(fig1, width="stretch")


    # --- CHART 2: Fixed Send Times ---
    df_send = pd.DataFrame({"Hours": send_hours})
    fig2 = px.histogram(
        df_send, 
        x="Hours", 
        range_x=[0, 26],
        nbins=13,
        title="Frequency of 'Successful' Sends by Time of Day (RobTop's Timezone)"
    )
    fig2.update_layout(
        xaxis=dict(tickmode='array', tickvals=bin_centers_2hr, ticktext=labels_2hr, tickangle=35),
        bargap=0.15,
        title_font=dict(size=14, family="Arial"),
        template="plotly_dark",  
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
    st.plotly_chart(fig2, width="stretch")


    # --- CHART 3: Fixed Outlier Scaling ---
    df_delta = pd.DataFrame({"Delay": delta_hours})
    fig3 = px.histogram(
        df_delta, 
        x="Delay", 
        range_x=[0, 26],
        nbins=13,
        title="Time Elapsed Between Most Recent Send and Level Rate"
    )
    fig3.update_layout(
        xaxis=dict(tickmode='array', tickvals=bin_centers_delta, ticktext=labels_delta, tickangle=45),
        bargap=0.15,
        title_font=dict(size=14, family="Arial"),
        template="plotly_dark",  
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=60, r=60, t=60, b=90)
    )
    fig3.update_traces(
        xbins=dict(start=0, end=26, size=2),
        marker_color='lightgreen', 
        marker_line_color='white', 
        marker_line_width=0.5
    )
    st.plotly_chart(fig3, width="stretch")