import asyncio
import random
import re
from asyncio import TimerHandle
from difflib import SequenceMatcher
from io import BytesIO
from pathlib import Path
from typing import Union, Dict
from typing import Dict as dict
from PIL import Image

from expiringdict import ExpiringDict
from nonebot import on_command, on_message
from nonebot.internal.rule import Rule
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11 import (
    GroupMessageEvent as v11GroupMessageEvent,
    MessageSegment as v11MessageSegment,
)
from nonebot_plugin_session import SessionId, SessionIdType
from nonebot.params import T_State
from .utils import split_msg
from ..info import get_bg
from ..utils import NGM
from ..api import osu_api
from ..schema import NewScore
from ..database.models import UserData
from ..api import safe_async_get

games: Dict[str, NewScore] = {}
pic_games: Dict[str, NewScore] = {}
timers: Dict[str, TimerHandle] = {}
pic_timers: Dict[str, TimerHandle] = {}
hint_dic = {"pic": False, "artist": False, "creator": False}
pic_hint_dic = {"artist": False, "creator": False, "audio": False}
group_hint = {}
pic_group_hint = {}
guess_audio = on_command("猜歌", priority=11, block=True)
guess_song_cache = ExpiringDict(1000, 60 * 60 * 24)
data_path = Path() / "data" / "osu"
pcm_path = data_path / "out.pcm"


async def get_random_beatmap_set(binded_id, group_id, ttl=10):
    if ttl == 0:
        return
    selected_user = random.choice(binded_id)
    if not selected_user:
        return
    user = await UserData.filter(user_id=selected_user).first()
    bp_info = await osu_api("bp", user.osu_id, NGM[str(user.osu_mode)])
    if not bp_info or isinstance(bp_info, str):
        return await get_random_beatmap_set(binded_id, group_id, ttl - 1)
    selected_score = random.choice([NewScore(**i) for i in bp_info])
    if selected_score.beatmapset.id not in guess_song_cache[group_id]:
        guess_song_cache[group_id].add(selected_score.beatmapset.id)
    else:
        return await get_random_beatmap_set(binded_id, group_id, ttl - 1)
    return selected_score, user.osu_name


@guess_audio.handle(parameterless=[split_msg()])
async def _(state: T_State, event: v11GroupMessageEvent, matcher: Matcher, session_id: str = SessionId(SessionIdType.GROUP)):
    if "error" in state:
        mode = str(random.randint(0, 3))
        await guess_audio.send("由于未绑定OSU账号，本次随机挑选模式进行猜歌\n" + state["error"])
    else:
        mode = state["mode"]
    group_id = session_id
    binded_id = await UserData.filter(osu_mode=mode).values_list("user_id", flat=True)
    if not binded_id:
        await guess_audio.finish("还没有人绑定该模式的osu账号呢，绑定了再来试试吧")
    if not guess_song_cache.get(group_id):
        guess_song_cache[group_id] = set()
    if state["para"]:
        bp_info = await osu_api("bp", state["para"], NGM[state["mode"]], is_name=True)
        if not bp_info or isinstance(bp_info, str):
            await guess_audio.send("该用户无bp记录")
        selected_score = random.choice([NewScore(**i) for i in bp_info])
        selected_user = state["para"]
    else:
        selected_score, selected_user = await get_random_beatmap_set(binded_id, group_id)
    if not selected_score:
        await guess_audio.finish("好像没有可以猜的歌了，今天的猜歌就到此结束吧！")
    if games.get(group_id, None):
        await guess_audio.finish("现在还有进行中的猜歌呢，请等待当前猜歌结束")
    games[group_id] = selected_score
    set_timeout(matcher, group_id)
    await guess_audio.send(f"开始osu猜歌游戏，猜猜下面音频的曲名吧，该曲抽选自{selected_user} {NGM[mode]} 模式的bp")
    print(selected_score.beatmapset.title)
    await guess_audio.finish(
        v11MessageSegment.record(
            f"https://cdn.sayobot.cn:25225/preview/{selected_score.beatmapset.id}.mp3"
        )
    )



async def stop_game(matcher: Matcher, cid: int):
    timers.pop(cid, None)
    if games.get(cid, None):
        game = games.pop(cid)
        if group_hint.get(cid, None):
            group_hint[cid] = None
        msg = f"猜歌超时，游戏结束，正确答案是{game.beatmapset.title_unicode}"
        if game.beatmapset.title_unicode != game.beatmapset.title:
            msg += f" [{game.beatmapset.title}]"
        await matcher.send(msg)


async def pic_stop_game(matcher: Matcher, cid: int):
    pic_timers.pop(cid, None)
    if pic_games.get(cid, None):
        game = pic_games.pop(cid)
        if pic_group_hint.get(cid, None):
            pic_group_hint[cid] = None
        msg = f"猜歌超时，游戏结束，正确答案是{game.beatmapset.title_unicode}"
        if game.beatmapset.title_unicode != game.beatmapset.title:
            msg += f" [{game.beatmapset.title}]"
        await matcher.send(msg)


def set_timeout(matcher: Matcher, cid: str, timeout: float = 300):
    timer = timers.get(cid, None)
    if timer:
        timer.cancel()
    loop = asyncio.get_running_loop()
    timer = loop.call_later(timeout, lambda: asyncio.ensure_future(stop_game(matcher, cid)))
    timers[cid] = timer


def pic_set_timeout(matcher: Matcher, cid: str, timeout: float = 300):
    timer = pic_timers.get(cid, None)
    if timer:
        timer.cancel()
    loop = asyncio.get_running_loop()
    timer = loop.call_later(timeout, lambda: asyncio.ensure_future(pic_stop_game(matcher, cid)))
    pic_timers[cid] = timer


def game_running(session_id: str = SessionId(SessionIdType.GROUP)) -> bool:
    return bool(games.get(session_id, None))


def pic_game_running(session_id: str = SessionId(SessionIdType.GROUP)) -> bool:
    return bool(pic_games.get(session_id, None))


word_matcher = on_message(Rule(game_running),priority=12)


pic_word_matcher = on_message(Rule(pic_game_running),priority=12)


@word_matcher.handle()
async def _(event: v11GroupMessageEvent, session_id: str = SessionId(SessionIdType.GROUP)):
    song_name = games[session_id].beatmapset.title
    song_name_unicode = games[session_id].beatmapset.title_unicode
    r1 = SequenceMatcher(None, song_name.lower(), event.get_plaintext().lower()).ratio()
    r2 = SequenceMatcher(None, song_name_unicode.lower(), event.get_plaintext().lower()).ratio()
    r3 = SequenceMatcher(
        None,
        re.sub(r"[(\[].*[)\]]", "", song_name.lower()),
        event.get_plaintext().lower(),
    ).ratio()
    if r1 >= 0.5 or r2 >= 0.5 or r3 >= 0.5:
        games.pop(session_id)
        if group_hint.get(session_id, None):
            group_hint[session_id] = None
        msg = f"恭喜{event.sender.nickname}猜出正确答案为{song_name_unicode}"
        await word_matcher.finish(v11MessageSegment.reply(event.message_id) + msg)




@pic_word_matcher.handle()
async def _(event: v11GroupMessageEvent, session_id: str = SessionId(SessionIdType.GROUP)):
    song_name = pic_games[session_id].beatmapset.title
    song_name_unicode = pic_games[session_id].beatmapset.title_unicode
    r1 = SequenceMatcher(None, song_name.lower(), event.get_plaintext().lower()).ratio()
    r2 = SequenceMatcher(None, song_name_unicode.lower(), event.get_plaintext().lower()).ratio()
    r3 = SequenceMatcher(
        None,
        re.sub(r"[(\[].*[)\]]", "", song_name.lower()),
        event.get_plaintext().lower(),
    ).ratio()
    if r1 >= 0.5 or r2 >= 0.5 or r3 >= 0.5:
        pic_games.pop(session_id)
        if pic_group_hint.get(session_id, None):
            pic_group_hint[session_id] = None
        msg = f"恭喜{event.sender.nickname}猜出正确答案为{song_name_unicode}"
        await pic_word_matcher.finish(v11MessageSegment.reply(event.message_id) + msg)




hint = on_command("音频提示", priority=11, block=True, rule=Rule(game_running))


@hint.handle()
async def _(session_id: str = SessionId(SessionIdType.GROUP)):
    score = games[session_id]
    if not group_hint.get(session_id, None):
        group_hint[session_id] = hint_dic.copy()
    if all(group_hint[session_id].values()):
        await hint.finish("已无更多提示，加油哦")
    true_keys = []
    for key, value in group_hint[session_id].items():
        if not value:
            true_keys.append(key)
    action = random.choice(true_keys)
    if action == "pic":
        group_hint[session_id]["pic"] = True
        await hint.finish(v11MessageSegment.image(score.beatmapset.covers.cover))
    if action == "artist":
        group_hint[session_id]["artist"] = True
        msg = f"曲师为：{score.beatmapset.artist_unicode}"
        if score.beatmapset.artist_unicode != score.beatmapset.artist:
            msg += f" [{score.beatmapset.artist}]"
        await hint.finish(msg)
    if action == "creator":
        group_hint[session_id]["creator"] = True
        await hint.finish(f"谱师为：{score.beatmapset.creator}")


pic_hint = on_command("图片提示", priority=11, block=True, rule=Rule(pic_game_running))


@pic_hint.handle()
async def _(session_id: str = SessionId(SessionIdType.GROUP)):
    score = pic_games[session_id]
    if not pic_group_hint.get(session_id, None):
        pic_group_hint[session_id] = pic_hint_dic.copy()
    if all(pic_group_hint[session_id].values()):
        await pic_hint.finish("已无更多提示，加油哦")
    true_keys = []
    for key, value in pic_group_hint[session_id].items():
        if not value:
            true_keys.append(key)
    action = random.choice(true_keys)
    if action == "audio":
        pic_group_hint[session_id]["audio"] = True
        await pic_hint.finish(
            v11MessageSegment.record(
                f"https://cdn.sayobot.cn:25225/preview/{score.beatmapset.id}.mp3"
            )
        )
    if action == "artist":
        pic_group_hint[session_id]["artist"] = True
        msg = f"曲师为：{score.beatmapset.artist_unicode}"
        if score.beatmapset.artist_unicode != score.beatmapset.artist:
            msg += f" [{score.beatmapset.artist}]"
        await pic_hint.finish(msg)
    if action == "creator":
        pic_group_hint[session_id]["creator"] = True
        await pic_hint.finish(f"谱师为：{score.beatmapset.creator}")



guess_pic = on_command("图片猜歌", priority=11, block=True)


@guess_pic.handle(parameterless=[split_msg()])
async def _(state: T_State, event: v11GroupMessageEvent, matcher: Matcher, session_id: str = SessionId(SessionIdType.GROUP)):
    if "error" in state:
        mode = str(random.randint(0, 3))
        await guess_pic.send("由于未绑定OSU账号，本次随机选择模式进行猜歌\n" + state["error"])
    else:
        mode = state["mode"]
    binded_id = await UserData.filter(osu_mode=mode).values_list("user_id", flat=True)
    if not binded_id:
        await guess_pic.finish("还没有人绑定该模式的osu账号呢，绑定了再来试试吧")
    if not guess_song_cache.get(session_id):
        guess_song_cache[session_id] = set()
    if state["para"]:
        bp_info = await osu_api("bp", state["para"], NGM[state["mode"]], is_name=True)
        if not bp_info or isinstance(bp_info, str):
            await guess_pic.send("该用户无bp记录")
        selected_score = random.choice([NewScore(**i) for i in bp_info])
        selected_user = state["para"]
    else:
        selected_score, selected_user = await get_random_beatmap_set(binded_id, session_id)
    if not selected_score:
        await guess_pic.finish("好像没有可以猜的歌了，今天的猜歌就到此结束吧！")
    if pic_games.get(session_id, None):
        await guess_pic.finish("现在还有进行中的猜歌呢，请等待当前猜歌结束")
    pic_games[session_id] = selected_score
    pic_set_timeout(matcher, session_id)
    await guess_pic.send(f"开始图片猜歌游戏，猜猜下面图片的曲名吧，该曲抽选自{selected_user} {NGM[mode]} 模式的bp")
    byt = await get_bg(selected_score.beatmap.id)
    img = Image.open(byt)
    width, height = img.size
    crop_width = int(width * 0.3)
    crop_height = int(height * 0.3)
    left = random.randint(0, width - crop_width)
    top = random.randint(0, height - crop_height)
    right = left + crop_width
    bottom = top + crop_height
    cropped_image = img.crop((left, top, right, bottom))
    byt = BytesIO()
    cropped_image.save(byt, "png")
    print(selected_score.beatmapset.title_unicode)
    await guess_pic.finish(v11MessageSegment.image(byt))



async def download_audio(set_id, group_id):
    audio_path = data_path / f"{set_id}.mp3"
    url = f"https://cdn.sayobot.cn:25225/preview/{set_id}.mp3"
    data = await safe_async_get(url)
    with open(audio_path, "wb") as file:
        file.write(data.content)
    process = await asyncio.create_subprocess_shell(
        f"ffmpeg -y -i {audio_path} -f s16le -acodec pcm_s16le -ar 12000 -ac 2 -loglevel quiet {pcm_path}"
    )
    await process.wait()
    task = await asyncio.create_subprocess_shell(
        f"silk_v3_encoder.exe {pcm_path} {data_path / Path(f'{group_id}.silk')} -tencent -quiet"
    )
    await task.wait()
