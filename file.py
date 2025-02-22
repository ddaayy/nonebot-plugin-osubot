from io import BytesIO, TextIOWrapper
from typing import Union, Optional

import re
from pathlib import Path

from nonebot import get_driver
from nonebot.log import logger

from .config import Config
from .api import safe_async_get
from .network import auto_retry
from .network.first_response import get_first_response
from .schema import Badge

plugin_config = Config.parse_obj(get_driver().config.dict())


osufile = Path(__file__).parent / "osufile"
map_path = Path() / "data" / "osu" / "map"
user_cache_path = Path() / "data" / "osu" / "user"
badge_cache_path = Path() / "data" / "osu" / "badge"
api_ls = ["https://api.chimu.moe/v1/download/",
          "https://api.osu.direct/d/",
          "https://txy1.sayobot.cn/beatmaps/download/novideo/"]

if not map_path.exists():
    map_path.mkdir(parents=True, exist_ok=True)
if not user_cache_path.exists():
    user_cache_path.mkdir(parents=True, exist_ok=True)
if not badge_cache_path.exists():
    badge_cache_path.mkdir(parents=True, exist_ok=True)


async def download_map(setid: int) -> Optional[Path]:
    urls = [i + str(setid) for i in api_ls]
    logger.info(f"开始下载地图: <{setid}>")
    req = await get_first_response(urls)
    filename = f"{setid}.osz"
    filepath = map_path.parent / filename
    with open(filepath, "wb") as f:
        f.write(req.read())
    logger.info(f"地图: <{setid}> 下载完毕")
    return filepath


async def download_tmp_osu(map_id):
    url = f"https://osu.ppy.sh/osu/{map_id}"
    logger.info(f"开始下载谱面: <{map_id}>")
    req = await safe_async_get(url)
    filename = f"{map_id}.osu"
    filepath = map_path / filename
    chunk = req.read()
    with open(filepath, "wb") as f:
        f.write(chunk)
    return filepath

@auto_retry
async def download_osu(set_id, map_id):
    url = [f"https://osu.ppy.sh/osu/{map_id}", f"https://api.osu.direct/osu/{map_id}"]
    logger.info(f"开始下载谱面: <{map_id}>")
    req = await get_first_response(url)
    if req:
        filename = f"{map_id}.osu"
        filepath = map_path / str(set_id) / filename
        with open(filepath, "wb") as f:
            f.write(req)
        return filepath
    else:
        raise Exception('下载出错，请稍后再试')


async def get_projectimg(url: str):
    if "avatar-guest.png" in url:
        url = "https://osu.ppy.sh/images/layout/avatar-guest.png"
    req = await safe_async_get(url)
    if req.status_code == 403:
        return osufile / "work" / "mapbg.png"
    data = req.read()
    im = BytesIO(data)
    return im


def re_map(file: Union[bytes, Path]) -> str:
    if isinstance(file, bytes):
        text = TextIOWrapper(BytesIO(file), "utf-8").read()
    else:
        with open(file, "r", encoding="utf-8") as f:
            text = f.read()
    res = re.search(r"\d,\d,\"(.+)\"", text)
    bg = "mapbg.png" if not res else res.group(1).strip()
    return bg


async def make_badge_cache_file(badge: Badge):
    path = badge_cache_path / f"{hash(badge.description)}.png"
    badge_icon = await get_projectimg(badge.image_url)
    with open(path, "wb") as f:
        f.write(badge_icon.getvalue())


# 保存个人信息界面背景
async def save_info_pic(user: str, byt: bytes):
    path = user_cache_path / user
    if not path.exists():
        path.mkdir()
    with open(path / "info.png", "wb") as f:
        f.write(BytesIO(byt).getvalue())
