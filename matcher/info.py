from nonebot import on_command
from nonebot.adapters.onebot.v11 import (
    MessageEvent as v11MessageEvent,
    MessageSegment as v11MessageSegment,
)
from nonebot.typing import T_State
from .utils import split_msg
from ..draw import draw_info
from ..utils import NGM

info = on_command("info", aliases={"Info", "INFO", "osuinfo"}, block=True, priority=11)


@info.handle(parameterless=[split_msg()])
async def _info(state: T_State, event: v11MessageEvent):
    await info.send("正在读取osu个人信息，少女祈祷中...")
    if "error" in state:
        await info.finish(v11MessageSegment.reply(event.message_id) + state["error"])
    data = await draw_info(
        state["user"], NGM[state["mode"]], state["day"], state["is_name"]
    )
    if isinstance(data, str):
        await info.finish(v11MessageSegment.reply(event.message_id) + data)
    await info.finish(
        v11MessageSegment.reply(event.message_id) + v11MessageSegment.image(data)
    )

