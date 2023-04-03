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
e = None
import PySimpleGUI as sg
lstbox = sg.Listbox(sound_ids,size=(50, 50))
win = sg.Window("TDViewer", [[lstbox, [sg.Button("Play"), sg.Button("Stop")]]], resizable=True)
while True:
    event, values = win.read()
    if event == sg.WINDOW_CLOSED:
        if settings_path.exists() == False:
            ok_or_cancel = sg.popup_ok_cancel("指定したパスを設定ファイルに保存しますか？")
            if ok_or_cancel == "OK":
                with settings_path.open("wt", encoding="utf-8") as f:
                    json.dump({"GAME_DATA_PATH": str(base_dir_path)}, f)
        break
    if event == "Play":
        v:str = values[0][0]
        try:
            audio = tdview.load_audio(v.lower() + ".abap")
            for i,data in audio.samples.items():
                tdview.play(data)
        except FileNotFoundError as err:
            sg.popup(f"ファイル({err.args[0]})が見つかりませんでした", title="ファイルが見つかりませんでした。")
        except Exception as err:
            e = err
            print(err)
            break
    elif event == "Stop":
        tdview.stop()
win.close()


