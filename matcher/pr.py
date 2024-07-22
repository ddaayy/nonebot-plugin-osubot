from nonebot import on_command
from nonebot.adapters.onebot.v11 import (
    MessageEvent as v11MessageEvent,
    MessageSegment as v11MessageSegment,
)
from nonebot.params import T_State

from ..api import get_user_info
from .utils import split_msg
from ..draw import draw_score
from ..schema import Score, NewScore
from ..api import osu_api
from ..draw.bp import draw_pfm
from ..utils import NGM
from ..database import UserData
from ..draw.score import cal_legacy_acc, cal_legacy_rank

recent = on_command("re",priority=11, block=True)
pr = on_command("pr", priority=11, block=True)


@recent.handle(parameterless=[split_msg()])
async def _recent(state: T_State, event: v11MessageEvent):
    await recent.send("正在查询最近成绩，少女祈祷中...")
    if "error" in state:
        await recent.finish(v11MessageSegment.reply(event.message_id) + state["error"])
    mode = NGM[state["mode"]]
    player = await UserData.get_or_none(user_id=int(event.get_user_id()))
    if "-" in state["para"]:
        ls = state["para"].split("-")
        low, high = ls[0], ls[1]
        data = await osu_api(
            "recent",
            state["user"],
            mode,
            is_name=state["is_name"],
            offset=int(low) - 1,
            limit=high,
            legacy_only=int(not player.lazer_mode)
        )
        if not data:
            await recent.finish(
                v11MessageSegment.reply(event.message_id) + f"未查询到在 {mode} 的游玩记录"
            )
        if isinstance(data, str):
            await recent.finish(v11MessageSegment.reply(event.message_id) + data)
        if not state["is_name"]:
            info = await get_user_info(
                f"https://osu.ppy.sh/api/v2/users/{state['user']}?key=id"
            )
            if isinstance(info, str):
                return info
            else:
                state["user"] = info["username"]
        score_ls = [Score(**score_json) for score_json in data]
        if not player.lazer_mode:
            score_ls = [i for i in score_ls if {"acronym": "CL"} in i.mods]
        for score_info in score_ls:
            if not player.lazer_mode:
                score_info.mods.remove({"acronym": "CL"}) if {"acronym": "CL"} in score_info.mods else None
            if score_info.ruleset_id == 3 and not player.lazer_mode:
                score_info.accuracy = cal_legacy_acc(score_info.statistics)
            if not player.lazer_mode:
                is_hidden = any(i in score_info.mods for i in ({"acronym": "HD"}, {"acronym": "FL"}, {"acronym": "FI"}))
                score_info.rank = cal_legacy_rank(score_info, is_hidden)
        pic = await draw_pfm("relist", state["user"], score_ls, score_ls, mode)
        await recent.finish(
            v11MessageSegment.reply(event.message_id) + v11MessageSegment.image(pic)
        )
    if state["day"] == 0:
        state["day"] = 1
    data = await draw_score(
        "recent",
        state["user"],
        int(event.get_user_id()),
        mode,
        [],
        state["day"] - 1,
        is_name=state["is_name"],
    )
    if isinstance(data, str):
        await recent.finish(v11MessageSegment.reply(event.message_id) + data)
    await recent.finish(
        v11MessageSegment.reply(event.message_id) + v11MessageSegment.image(data)
    )


@pr.handle(parameterless=[split_msg()])
async def _pr(state: T_State, event: v11MessageEvent):
    await pr.send("正在查询最近成绩，少女祈祷中...")
    if "error" in state:
        await pr.finish(v11MessageSegment.reply(event.message_id) + state["error"])
    mode = state["mode"]
    player = await UserData.get_or_none(user_id=int(event.get_user_id()))
    if "-" in state["para"]:
        ls = state["para"].split("-")
        low, high = ls[0], ls[1]
        data = await osu_api(
            "pr",
            state["user"],
            NGM[mode],
            is_name=state["is_name"],
            offset=int(low) - 1,
            limit=high,
            legacy_only=int(not player.lazer_mode)
        )
        if not data:
            await pr.finish(
                v11MessageSegment.reply(event.message_id) + f"未查询到在 {NGM[mode]} 的游玩记录"
            )
        if isinstance(data, str):
            await pr.finish(v11MessageSegment.reply(event.message_id) + data)
        if not state["is_name"]:
            info = await get_user_info(
                f"https://osu.ppy.sh/api/v2/users/{state['user']}?key=id"
            )
            if isinstance(info, str):
                return info
            else:
                state["user"] = info["username"]
        score_ls = [NewScore(**score_json) for score_json in data]
        if not player.lazer_mode:
            score_ls = [i for i in score_ls if {"acronym": "CL"} in i.mods]
        for score_info in score_ls:
            if not player.lazer_mode:
                score_info.mods.remove({"acronym": "CL"}) if {"acronym": "CL"} in score_info.mods else None
            if score_info.ruleset_id == 3 and not player.lazer_mode:
                score_info.accuracy = cal_legacy_acc(score_info.statistics)
            if not player.lazer_mode:
                is_hidden = any(i in score_info.mods for i in ({"acronym": "HD"}, {"acronym": "FL"}, {"acronym": "FI"}))
                score_info.rank = cal_legacy_rank(score_info, is_hidden)
        pic = await draw_pfm("prlist", state["user"], score_ls, score_ls, NGM[mode])
        await pr.finish(
            v11MessageSegment.reply(event.message_id) + v11MessageSegment.image(pic)
        )
    if state["day"] == 0:
        state["day"] = 1
    data = await draw_score(
        "pr",
        state["user"],
        int(event.get_user_id()),
        NGM[mode],
        [],
        state["day"] - 1,
        is_name=state["is_name"],
    )
    if isinstance(data, str):
        await pr.finish(v11MessageSegment.reply(event.message_id) + data)
    await pr.finish(
        v11MessageSegment.reply(event.message_id) + v11MessageSegment.image(data)
    )