from nonebot import on_command
from nonebot.adapters.onebot.v11 import (
    MessageEvent as v11MessageEvent,
    MessageSegment as v11MessageSegment,
)
from nonebot.typing import T_State
from .utils import split_msg
from ..draw import get_score_data
from ..utils import NGM


score = on_command("score", priority=11, block=True)


@score.handle(parameterless=[split_msg()])
async def _score(state: T_State, event: v11MessageEvent):
    await score.send("正在查询成绩图，少女祈祷中...")
    if "error" in state:
        await score.finish(v11MessageSegment.reply(event.message_id) + state["error"])
    if not state["para"].isdigit():
        await score.finish("请输入正确的谱面ID")
    data = await get_score_data(
        state["user"],
        int(event.get_user_id()),
        NGM[state["mode"]],
        mapid=state["para"],
        mods=state["mods"],
        is_name=state["is_name"],
    )
    if isinstance(data, str):
        await score.finish(v11MessageSegment.reply(event.message_id) + data)
    await score.finish(
        v11MessageSegment.reply(event.message_id) + v11MessageSegment.image(data)
    )

