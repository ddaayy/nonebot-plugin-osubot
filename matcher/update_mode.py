from nonebot import on_command
from nonebot.params import CommandArg, Message
from nonebot.adapters.onebot.v11 import (
    MessageEvent as v11MessageEvent,
    MessageSegment as v11MessageSegment,
)

from ..database import UserData
from ..utils import NGM


update_mode = on_command("更新模式", priority=11, aliases={"更改模式"}, block=True)
update_lazer = on_command("切换lazer", priority=11, block=True)

@update_mode.handle()
async def _(
    event: v11MessageEvent, args: Message = CommandArg()
):
    user = await UserData.get_or_none(user_id=event.get_user_id())
    if not user:
        await update_mode.finish(
            v11MessageSegment.reply(event.message_id) + "该账号尚未绑定，请输入 /bind osu 用户名 绑定账号"
        )
    elif not args:
        await update_mode.finish(
            v11MessageSegment.reply(event.message_id) + "请输入需要更新内容的模式"
        )
    if not args.extract_plain_text().isdigit():
        await update_mode.finish(
            v11MessageSegment.reply(event.message_id) + "请输入正确的模式 0-3"
        )
        return
    mode = int(args.extract_plain_text())
    if 0 <= mode < 4:
        await UserData.filter(user_id=event.get_user_id()).update(osu_mode=mode)
        msg = f"已将默认模式更改为 {NGM[str(mode)]}"
    else:
        msg = "请输入正确的模式 0-3"
    await update_mode.finish(v11MessageSegment.reply(event.message_id) + msg)

@update_lazer.handle()
async def _(event: v11MessageEvent):
    user = await UserData.get_or_none(user_id=event.get_user_id())
    if not user:
        await update_lazer.finish("该账号尚未绑定，请输入 /bind osu 用户名 绑定账号")
    await UserData.filter(user_id=event.get_user_id()).update(lazer_mode=not user.lazer_mode)
    if user.lazer_mode:
        msg = "已关闭lazer模式"
    else:
        msg = "已开启lazer模式"
    await update_lazer.finish(msg)