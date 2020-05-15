import json
from time import sleep
import spotipy
import spotipy.client
from pynput.keyboard import Key, Controller
from pynput import keyboard
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy.util as util
from pystray import MenuItem as item
from pprint import pprint
import pystray
import os
import sys
from PIL import Image, ImageDraw
import PIL
from multiprocessing import Process, Event
import multiprocessing
from threading import Lock, Thread
from functools import partial
import configparser
from pathlib import Path
import copy


# Toggle web/local by absence of client_Secret in config/cfg
# empty = use aws
# filled = use local
#TODO: Optimize/fix hotkey (move to punputs .hotkey system)
#TODO: Set up server for secret ID
#TODO: Add skip/pause,play hotkeys
#TODO: Tray entrys for enabling/disabling hotkeys
#TODO: Hotkey combos will be done VIA config.cfg by user

try_to_quit = False
thread1: Process = None

config = configparser.ConfigParser()
config.read('config.cfg')


icon_image = Image.open('img/ToUnlike.PNG')
menu = (item('name1', lambda: pprint('name1')), item('Exit', lambda: close_program()))
icon = pystray.Icon('Sliker', icon_image, 'Sliker? I dont even know her', menu)

LIKE_TOGGLE_COMBO = []

# LIKE_TOGGLE_COMBO = [
#     [keyboard.Key.shift, keyboard.KeyCode(char='a')],
#     [keyboard.Key.shift, keyboard.KeyCode(char='A')],
# ]

hotkey_active_state = '0'
current_keys_pressed = set()

# username = ''
# redirect_uri = ''
# client_id = ''
# client_secret = ''
username = config['User']['username']
redirect_uri = config['API Keys']['redirect_uri']
client_id = config['API Keys']['client_id']
client_secret = config['API Keys']['client_secret']


def main():
    global config
    load_config('config.cfg', config)
    global thread1
    global try_to_quit
    global icon

    e_is_liked = multiprocessing.Event()
    e_is_unliked = multiprocessing.Event()

    def icon_thread(icn):
        icon_loop(icn, e_is_liked, e_is_unliked)

    thread1 = Process(target=thr1, args=(e_is_liked, e_is_unliked, LIKE_TOGGLE_COMBO))
    thread1.start()
    icon.run(setup=icon_thread)
    thread1.join()
    while try_to_quit:
        sys.exit(200)
    sys.exit(200)


def thr1(e1, e2, hkLikeCombo):
    global try_to_quit
    e_is_liking = multiprocessing.Event()

    def on_press(key):
        pprint(hkLikeCombo)
        if hotkeys_pressed(key, hkLikeCombo, e_is_liking):
            toggle_like_status(e1, e2, e_is_liking)

    def on_release(key):
        hotkeys_released(key, hkLikeCombo)

    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()


def hotkeys_pressed(key, hotkeylist, event):
    global hotkey_active_state
    if any([key in COMBO for COMBO in hotkeylist]) and not event.is_set():
        current_keys_pressed.add(key)
        if any(all(k in current_keys_pressed for k in COMBO) for COMBO in
               hotkeylist) and hotkey_active_state == '0':
            hotkey_active_state = '1'
            return True


def hotkeys_released(key, hotkeylist):
    global hotkey_active_state
    if any([key in COMBO for COMBO in hotkeylist]):
        try:
            current_keys_pressed.remove(key)
        except:
            pprint('couldnt remove. probably already gone IDK')
        finally:
            hotkey_active_state = '0'


def load_config(config_file: str, cfg: configparser):
    global username
    global client_id
    global client_secret
    global redirect_uri
    global LIKE_TOGGLE_COMBO

    if Path(config_file).is_file():
        pprint('Config Exists')
        cfg.read(config_file)
    else:
        cfg['COMMENTS'] = {}
        cfg.set('COMMENTS', """###########################################################################
# For a non alphanumerical key use:
# https://pynput.readthedocs.io/en/latest/keyboard.html#pynput.keyboard.Key
# ")
# For a alpha/numerical key, do
# keyboard.KeyCode(char='YOUR KEY')
# If using shift as a modifyer, do 2 entries. one with a lower case, the other with uppercase. Example:
# [")
#         [\"keyboard.Key.shift\", \"keyboard.KeyCode(char='a')\"],
#         [\"keyboard.Key.shift\", \"keyboard.KeyCode(char='A')\"]
# ]
###########################################################################""",'')
        cfg['Hotkeys'] = {}
        cfg['Hotkeys']['like_toggle'] = """[
        ["keyboard.Key.shift", "keyboard.KeyCode(char='a')"],
        ["keyboard.Key.shift", "keyboard.KeyCode(char='A')"]
        ]"""

        cfg['API Keys'] = {}
        cfg['API Keys']['client_id'] = ''
        cfg['API Keys']['client_secret'] = ''
        cfg['API Keys']['redirect_uri'] = 'http://localhost:8000'

        cfg['User'] = {}
        cfg['User']['Username'] = ''
        with open(config_file, 'w') as configfile:
            cfg.write(configfile)
        get_api_client_creds()

    username = config['User']['username']
    redirect_uri = config['API Keys']['redirect_uri']
    client_id = config['API Keys']['client_id']
    client_secret = config['API Keys']['client_secret']
    LIKE_TOGGLE_COMBO = copy.deepcopy(json.loads(config['Hotkeys']['like_toggle']))
    listlistStr_to_listlistFunc(LIKE_TOGGLE_COMBO)


def get_api_client_creds():
    print('Need client API ID and secret')
    print('')
    # start of non web setup
    print('because of the nature of this app, each user')
    print('needs to set up their own API keys on:')
    print('https://developer.spotify.com/dashboard/applications')

    print('Walkthrough images are in img/walkthrough')
    usrnm = input('Spotify Login ID: ')
    cid = input('Client ID: ')
    cst = input('Client Secret: ')
    ruri = input('Redirect Uri (leave blank to use: ' + config['API Keys']['redirect_uri'] + '): ')
    if len(ruri) > 3:
        config['API Keys']['redirect_uri'] = ruri
    config['User']['username'] = usrnm
    config['API Keys']['client_id'] = cid
    config['API Keys']['client_secret'] = cst
    with open('config.cfg', 'w') as configfile:
        config.write(configfile)
    return


def listlistStr_to_listlistFunc(vlist):
    for i in range(len(vlist)):
        for x in range(len(vlist[i])):
            vlist[i][x] = eval(vlist[i][x])
    return


def close_program():
    # os._exit(0)
    global try_to_quit
    # global thread1
    try_to_quit = True
    icon.stop()
    thread1.terminate()


def icon_loop(icon2, e1, e2):
    icon2.visible = True
    heart_img = Image.open('img/ToUnlike.PNG')
    empty_heart_img = Image.open('img/ToLike.PNG')
    global try_to_quit

    # There is a win 0 error after the icon has been changed 3333(or 3331) times.
    # the following counter is to icon changing before than (at/before 3300)
    times_icon_updates = 0
    breaking_point = 3330
    while True:
        if e1.is_set() and times_icon_updates <= breaking_point:
            try:
                pprint('1')
                e1.clear()
                if icon2.icon != heart_img:
                    icon2.icon = heart_img
                    times_icon_updates +=1
            except:
                pprint('error setting toUnlike IMG')

        elif e2.is_set() and times_icon_updates <= breaking_point:
            try:
                pprint('2')
                e2.clear()
                if icon2.icon != empty_heart_img:
                    icon2.icon = empty_heart_img
                    times_icon_updates +=1
            except:
                pprint('error setting toLike IMG')

        if try_to_quit:
            sys.exit(100)


def toggle_like_status(elike, eunlike, eisliking):
    eisliking.set()
    spotify_lib_read = spotify_entire_scope()
    track_id = [get_current_track_id()]
    track_is_liked = bool(spotify_lib_read.current_user_saved_tracks_contains(tracks=track_id)[0])
    spotify_lib_modify = spotify_entire_scope()
    if track_is_liked:
        pprint('removed')
        eunlike.set()
        spotify_lib_modify.current_user_saved_tracks_delete(track_id)
    else:
        pprint('added')
        elike.set()
        spotify_lib_modify.current_user_saved_tracks_add(track_id)
    eisliking.clear()
    return


def get_current_track_id():
    current_track_data = get_current_track_data()

    if current_track_data is not None:
        # 'currently_playing_type' can be; track, episode, ad or unknown.
        return current_track_data['item']['id']
    else:
        jankify_for_current_track('Computer')
        return get_current_track_id()


def get_current_track_data():
    return spotify_entire_scope().currently_playing()


def get_device(device_type):
    spotify = spotify_entire_scope()
    devices = spotify.devices()

    for key in devices['devices']:
        if key['type'] == device_type:
            return {'id': key['id'], 'volume': key['volume_percent']}
    # If chosen device isn't online, returns first device on API JSON list received from Spotify
    return {'id': devices['devices'][0]['id'], 'volume': devices['devices'][0]['volume_percent']}


def spotify_entire_scope():
    spotify = spotipy.Spotify(auth=util.prompt_for_user_token(username=username, scope="user-library-modify "
                                                                                       "user-library-read "
                                                                                       "user-modify-playback-state "
                                                                                       "user-read-playback-state",
                                                              redirect_uri=redirect_uri, client_id=client_id, client_secret=client_secret))
    return spotify


# if no music is played after awhile get_current_track_data() will not receive data from spotify.
# This jankify function will set volume to 0, play/pause AFAP so that get_current_track_data() will be able to get data
def jankify_for_current_track(device_type):
    spotify = spotify_entire_scope()
    device = get_device(device_type)
    spotify.volume(volume_percent=0, device_id=device['id'])
    spotify.start_playback(device_id=device['id'])
    spotify.pause_playback(device_id=device['id'])
    spotify.volume(volume_percent=device['volume'], device_id=device['id'])
    return


if __name__ == "__main__":
    main()
