#%%
import UnityPy
import os.path
from pathlib import Path
import sounddevice as sd
import soundfile as sf
import io
import PySimpleGUI as sg
import json

base_dir_path = None
settings_path = (Path.cwd() / "settings.json")
if settings_path.exists():
    with settings_path.open("rb") as f:
        try:
            settings_dic = json.load(f)
        except json.JSONDecodeError as err:
            print(f"設定ファイルのJSONが正常に読み込めませんでした。\nファイル({settings_path})を削除してください")
            raise err
    try:
        base_dir_path_str = settings_dic["GAME_DATA_PATH"]
    except KeyError as err:
        print("設定ファイルを読み込みましたが、GAME_DATA_PATHが存在しませんでした")
    else:
        filepath =  Path(base_dir_path_str)
        if filepath.exists() and filepath.is_dir():
            base_dir_path = filepath
else:
    filepath = sg.popup_get_folder("ゲームデータのあるフォルダ(prim)を指定してください")
    if filepath is not None:
        base_dir_path = Path(filepath)
        if base_dir_path.exists():
            if base_dir_path.is_dir() == False:
                print(f"{base_dir_path}がフォルダではありません")
                exit()
        else:
            print(f"{base_dir_path}が存在しません")
            exit()
    else:
        print("ゲームデータの指定は必須です。")
        exit()

# %%
sound_files_path = Path.cwd() /  "sound_files.txt"
with open(sound_files_path, "rt") as f:
    sound_ids = f.read().splitlines()

# %%
class TDViewer:
    def __init__(self, base_dir:str|Path=None) -> None:
        if base_dir is str:
            self.base_dir = Path(base_dir)
        else:
            self.base_dir = base_dir
    
    def load_image(self, filename:str):
        filepath = self.base_dir / filename
        if filepath.exists() == False:
            raise FileNotFoundError(f"{filepath}")
        env = UnityPy.load(str(filepath))
        obj = env.objects[0]
        if obj.type.name  in ['Sprite', 'Texture2D']:
            v = obj.read()
            return v.image
        else:
            raise Exception(f"エラー SpriteまたはTexture2Dではありません ({obj.type.name})")
        
    def load_audio(self, filename:str):
        filepath = self.base_dir / filename
        if filepath.exists() == False:
            raise FileNotFoundError(f"{filepath}")
        env = UnityPy.load(str(filepath))
    
        for obj in env.objects:
            if obj.type.name == 'AudioClip':
                v = obj.read()
                return v
        raise Exception(f"エラー AudioClipではありません")
    
    def play(self, data):
        if isinstance(data, bytes):
            bio = io.BytesIO(data)
            d, srate = sf.read(bio)
            sd.play(d,samplerate=srate)

    def stop(self):
        sd.stop(True)

# %%
tdview = TDViewer(base_dir_path)

# %% 
# GUI
#!%gui tk

import PySimpleGUI as sg
import re
import threading
import itertools
from queue import Queue
import queue
import threading
import time

stop_ev = threading.Event()
def _play_thread(q:Queue):
    while not stop_ev.is_set():
        try:
            audio = q.get(timeout=0.1)
        except queue.Empty:
            continue
        try:
            st = sd.get_stream()
            if st.active :
                # 終了イベントを確認
                while True:
                    if stop_ev.is_set():
                        break
                    if not st.active:
                        break
                    time.sleep(0.1)
        except RuntimeError:
            pass
        for i, data in audio.samples.items():
                    tdview.play(data)        
    sd.stop(True)

audio_q = Queue()    
play_thread = threading.Thread(target=_play_thread, kwargs={"q":audio_q})
play_thread.start()
lstbox = sg.Listbox(sound_ids,size=(30, 20), key="-List-",expand_x=True, expand_y=True,select_mode=sg.LISTBOX_SELECT_MODE_EXTENDED)
win = sg.Window("TDViewer", [[sg.Input(size=(30,1), enable_events=True, key="-INPUT-")],
                               [lstbox], [sg.Button("Play"), sg.Button("Stop")] ,[sg.Button("Reset")]], resizable=True)
while True:
    event, values = win.read()
    print(f"event:{event}")
    if event == sg.WINDOW_CLOSED:
        stop_ev.set()
        if settings_path.exists() == False:
            ok_or_cancel = sg.popup_ok_cancel("指定したパスを設定ファイルに保存しますか？")
            if ok_or_cancel == "OK":
                with settings_path.open("wt", encoding="utf-8") as f:
                    json.dump({"GAME_DATA_PATH": str(base_dir_path)}, f)
        break
    if event == "Play":
        if play_thread.is_alive() == False:
            stop_ev.clear()
            audio_q = Queue()
            play_thread = threading.Thread(target=_play_thread, kwargs={"q":audio_q})
            play_thread.start()
        selections = values["-List-"]
        print(f"selections:{selections}")
        filenames = [ s.lower() + ".abap" for s in selections]
        missing_filenames = []
        for filename in filenames:
            if (base_dir_path / filename).exists() == False:
                print(f"File Not Found: {filename}")
                missing_filenames.append(filename)
        play_filenames = [n for n in filenames if n not in missing_filenames]
        for sel in play_filenames:
            try:
                print(sel)
                audio = tdview.load_audio(sel)
                audio_q.put(audio)
            except FileNotFoundError as err:
                sg.popup(f"ファイル({err.args[0]})が見つかりませんでした", title="ファイルが見つかりませんでした。")
            except Exception as err:
                print(err)
                break
    elif event == "Stop":
        sd.stop()
        stop_ev.set()
        
    elif event == "-INPUT-":
        print("-INPUT-")
        if values["-INPUT-"] != '':
            s:str = values["-INPUT-"]
            r = re.compile(s,re.IGNORECASE)
            ids = [ i for i in sound_ids if r.search(i)]
            win["-List-"].update(ids)
    elif event == "Reset":
            win["-INPUT-"].update(value="")
            win["-List-"].update(sound_ids)
win.close()
