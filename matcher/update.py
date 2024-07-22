from io import BytesIO
from typing import Union

from nonebot import on_command, get_driver
from nonebot.adapters.onebot.v11.helpers import ImageURLs
from nonebot.adapters.onebot.v11 import (
    MessageEvent as v11MessageEvent,
    MessageSegment as v11MessageSegment,
    Bot as v11Bot,
    GroupMessageEvent as v11GroupMessageEvent,
)
from nonebot.typing import T_State
from ..file import user_cache_path, save_info_pic, safe_async_get


from .utils import split_msg

update_pic = on_command("更新背景", aliases={"更改背景"}, priority=11, block=True)
update_info = on_command("osuupdate", aliases={"更新"}, priority=11, block=True)
clear_background = on_command("清空背景", aliases={"清除背景", "重置背景"}, priority=11, block=True)


@update_pic.handle(parameterless=[split_msg()])
async def _(
    bot: v11Bot,
    state: T_State,
    event: v11GroupMessageEvent,
    pic_ls: list = ImageURLs("请在指令后附上图片"),
):
    if "error" in state:
        await update_pic.finish(
            v11MessageSegment.reply(event.message_id) + state["error"]
        )
    user = state["user"]
    pic_url = pic_ls[0]
    await save_info_pic(user, pic_url)
    msg = f"自群{event.group_id}: {event.user_id}的更新背景申请" + v11MessageSegment.image(
        pic_url
    )
    for superuser in get_driver().config.superusers:
        await bot.send_private_msg(user_id=int(superuser), message=msg)
    await update_pic.finish(v11MessageSegment.reply(event.message_id) + "更新背景成功")


@update_info.handle(parameterless=[split_msg()])
async def _(state: T_State, event: v11MessageEvent):
    if "error" in state:
        await update_info.finish(
            v11MessageSegment.reply(event.message_id) + state["error"]
        )
    user = state["user"]
    user_path = user_cache_path / str(user)
    for file_path in user_path.glob("icon*.*"):
        # 检查文件是否为图片格式
        if file_path.suffix.lower() in [".jpg", ".png", ".jpeg", ".gif", ".bmp", ".peg"]:
            file_path.unlink()
    await update_info.finish(v11MessageSegment.reply(event.message_id) + "个人信息更新成功")


@clear_background.handle(parameterless=[split_msg()])
async def _(state: T_State, event: v11MessageEvent):
    if "error" in state:
        await clear_background.finish(
            v11MessageSegment.reply(event.message_id) + state["error"]
        )
    user = state["user"]
    path = user_cache_path / str(user) / "info.png"
    if path.exists():
        path.unlink()
        await clear_background.finish(
            v11MessageSegment.reply(event.message_id) + "背景图片清除成功"
        )
    else:
        await clear_background.finish(
            v11MessageSegment.reply(event.message_id) + "您还没有设置背景或已成功清除背景"
        )
