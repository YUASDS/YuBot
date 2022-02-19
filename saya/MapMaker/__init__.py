import os
import re


from pathlib import Path
from graia.saya import Saya, Channel
from graia.ariadne.model import Group, Member
from graia.ariadne.message.element import  Image
from graia.ariadne.event.message import GroupMessage
from graia.ariadne.message.chain import MessageChain
from graia.saya.builtins.broadcast.schema import ListenerSchema
from graia.ariadne.message.parser.twilight import (Twilight, FullMatch,
                                                   RegexMatch, WildcardMatch)

from util.sendMessage import safeSendGroupMessage
from util.control import Permission, Interval, Rest
from .LineMaker import (line_maker, save_config, load_config, get_pet)

func = os.path.dirname(__file__).split("\\")[-1]
bg = os.path.join(os.path.dirname(__file__), 'bg.jpg')
CONFIG_FILE = Path(__file__).parent.joinpath("config.json")
MAP = {}

# if not os.path.exists(config_path):
#     with open(config_path, 'w', encoding='utf8') as f:
#         f.write("{}")
# config = load_config(config_path)

saya = Saya.current()
channel = Channel.current()


@channel.use(
    ListenerSchema(
        priority=16,  # 优先度
        listening_events=[GroupMessage],
        inline_dispatchers=[
            Twilight({
                "head": RegexMatch("制作地图|制造地图|创建地图|刷新地图"),
                "space":RegexMatch("[\s]+",optional=True),
                "num":RegexMatch("[0-9]+",optional=True),
                "anythings": WildcardMatch(flags=re.DOTALL)
            })
        ],
        decorators=[
            Permission.require(),
            Permission.restricter(func),
            Rest.rest_control(),
            Interval.require()
        ],
    ))
async def main(group: Group, anythings: RegexMatch,num:RegexMatch):
    if num.matched:
        num = num.result.asDisplay()
        if num.isdigit:
            num=int(num)
        else:
            num=6
    else:
        num=6
    if anythings.matched:
        message_chain = anythings.result
        if message_chain.has(Image):
            if len(message_chain.get(Image)) > 1:
                return await safeSendGroupMessage(
                    group, MessageChain.create("创建背景时只能携带一张图片哦！"))
            else:
                image_url = message_chain.getFirst(Image).url
                try:
                    back=await get_pet(image_url=image_url)
                except:
                    return await safeSendGroupMessage(
                    group, MessageChain.create("图片获取失败，换张图片吧~"))
                imgs = line_maker(back,part=num)
                img = await imgs.map_pice(option=1)
    else:
        imgs = line_maker(bg,part=num)
        img = await imgs.map_pice()
    cell_size = imgs.cell_size
    gid = str(group.id)
    MAP[gid] = {}
    MAP[gid]["pet"] = {}
    lis = [[0 for i in range(imgs.rg1)] for i in range(imgs.rg2)]
    MAP[gid]["array"] = lis
    MAP[gid]["bg"] = imgs.Img
    data = await load_config(CONFIG_FILE)
    data[gid] = cell_size
    await save_config(data, CONFIG_FILE)
    await safeSendGroupMessage(group, MessageChain.create("地图制作完成"))
    await safeSendGroupMessage(group,
                               MessageChain.create(Image(data_bytes=img)))
    pass


@channel.use(
    ListenerSchema(
        listening_events=[GroupMessage],
        inline_dispatchers=[
            Twilight({
                "head": FullMatch("加入地图"),
                "x": RegexMatch("[a-z]|[A-Z]",optional=True),
                "y": RegexMatch("[0-9]",optional=True)
            })
        ],
        decorators=[
            Permission.require(),
            Permission.restricter(func),
            Rest.rest_control(),
            Interval.require()
        ],
    ))
async def join(group: Group, x: RegexMatch, y: RegexMatch, member: Member):
    if not x.matched and y.matched:
        return await safeSendGroupMessage(
                    group, MessageChain.create("加入地图的时候需要带上位置哦~"))
    x = x.result.asDisplay()
    y = y.result.asDisplay()
    gid = str(group.id)
    mid = str(member.id)
    x = ord(x.upper()) - 65
    y = int(y)
    config = await load_config(CONFIG_FILE)
    if gid in MAP:
        file = MAP[gid]["bg"].copy()
        cell_size = config[gid]

        if True in [mid in i for i in MAP[gid]["array"]]:
            return await safeSendGroupMessage(group,
                                              MessageChain.create("请使用移动"))
        MAP[gid]["array"][x][y] = mid

        maker = line_maker(file=file, cell_size=cell_size)
        if mid not in MAP[gid]["pet"]:
            pet = await get_pet(mid)
            MAP[gid]["pet"][mid] = pet

        img = maker.post_array(pet_dict=MAP[gid]["pet"],
                               bg_array=MAP[gid]["array"])

        await safeSendGroupMessage(group, MessageChain.create("加入地图成功"))
        await safeSendGroupMessage(group,
                                   MessageChain.create(Image(data_bytes=img)))
        pass
    else:
        await safeSendGroupMessage(group, MessageChain.create("请先创建地图"))


@channel.use(
    ListenerSchema(
        listening_events=[GroupMessage],
        inline_dispatchers=[
            Twilight({
                "head": FullMatch("移动"),
                "x": RegexMatch("[a-z]|[A-Z]",optional=True),
                "y": RegexMatch("[0-9]",optional=True)
            })
        ],
        decorators=[
            Permission.require(),
            Permission.restricter(func),
            Rest.rest_control(),
            Interval.require()
        ],
    ))
async def change(group: Group, x: RegexMatch, y: RegexMatch, member: Member):
    if not x.matched and y.matched:
        return await safeSendGroupMessage(
                    group, MessageChain.create("移动地图的时候需要带上位置哦~"))
    x = x.result.asDisplay()
    y = y.result.asDisplay()
    gid = str(group.id)
    mid = str(member.id)
    x = ord(x.upper()) - 65
    y = int(y)
    config = await load_config(CONFIG_FILE)
    if gid in MAP:
        file = MAP[gid]["bg"].copy()
        cell_size = config[gid]
        
        if not True in [mid in i for i in MAP[gid]["array"]]:
            return await safeSendGroupMessage(group,
                                             MessageChain.create("请先加入地图"))
        w = 0 
        for i in MAP[gid]["array"]:
            h = 0
            for j in i:
                if j == mid:
                    MAP[gid]["array"][w][h] = 0
                    MAP[gid]["array"][x][y] = mid
                    # print(w, h)
                    # print(MAP[gid]["array"])
                h = h + 1
            w = w + 1
        maker = line_maker(file=file, cell_size=cell_size)
        if mid not in MAP[gid]["pet"]:
            pet = await get_pet(mid)
            MAP[gid]["pet"][mid] = pet

        img = maker.post_array(pet_dict=MAP[gid]["pet"],
                               bg_array=MAP[gid]["array"])

        await safeSendGroupMessage(group, MessageChain.create("移动地图成功"))
        await safeSendGroupMessage(group,
                                   MessageChain.create(Image(data_bytes=img)))
        pass
    else:
        await safeSendGroupMessage(group, MessageChain.create("请先创建地图"))


@channel.use(
    ListenerSchema(
        listening_events=[GroupMessage],
        inline_dispatchers=[
            Twilight({
                "head": RegexMatch("添加角色|增加角色|添加NPC"),
                "space1": RegexMatch("[\s]+",optional=True),
                "npc": RegexMatch("[\S]+",optional=True),
                "space2": RegexMatch("[\s]+",optional=True),
                "x": RegexMatch("[a-z]|[A-Z]",optional=True),
                "y": RegexMatch("[0-9]",optional=True),
                "enter": FullMatch("\n",optional=True),
                "anythings1": WildcardMatch(optional=True)
            })
        ],
        decorators=[
            Permission.require(),
            Permission.restricter(func),
            Rest.rest_control(),
            Interval.require()
        ],
    ))
async def joinImage(group: Group, npc: RegexMatch, x: RegexMatch,
                    y: RegexMatch,  anythings1: WildcardMatch,member:Member):

    gid = str(group.id)
    x = x.result.asDisplay()
    y = y.result.asDisplay()
    npc=npc.result.asDisplay()
    x = ord(x.upper()) - 65
    y = int(y)
    message_chain = anythings1.result
    config = await load_config(CONFIG_FILE)
    if gid in MAP:
        file = MAP[gid]["bg"].copy()
        cell_size = config[gid]
        MAP[gid]["array"][x][y] = npc

        maker = line_maker(file=file, cell_size=cell_size)
        if message_chain.has(Image):
            if len(message_chain.get(Image)) > 1:
                return await safeSendGroupMessage(
                    group, MessageChain.create("添加角色只能携带一张图片哦！"))
            else:
                image_url = message_chain.getFirst(Image).url
                pet = await get_pet(image_url=image_url)
        else:
            pet= await get_pet(member_id=str(member.id))
        if npc not in MAP[gid]["pet"]:
            MAP[gid]["pet"][npc] = pet
        else:
            return await safeSendGroupMessage(
                    group, MessageChain.create(f"当前{npc}，已经加入了地图了,请使用移动~"))
        img = maker.post_array(pet_dict=MAP[gid]["pet"],
                               bg_array=MAP[gid]["array"])

        await safeSendGroupMessage(group, MessageChain.create("添加NPC成功"))
        await safeSendGroupMessage(group,
                                   MessageChain.create(Image(data_bytes=img)))
        pass
    else:
        await safeSendGroupMessage(group, MessageChain.create("请先创建地图"))

@channel.use(
    ListenerSchema(
        listening_events=[GroupMessage],
        inline_dispatchers=[
            Twilight({
                "head": RegexMatch("移动NPC|移动角色"),
                "space1": RegexMatch("[\s]+",optional=True),
                "npc": RegexMatch("[\S]+",optional=True),
                "space2": RegexMatch("[\s]+",optional=True),
                "x": RegexMatch("[a-z]|[A-Z]",optional=True),
                "y": RegexMatch("[0-9]",optional=True)
            })
        ],
        decorators=[
            Permission.require(),
            Permission.restricter(func),
            Rest.rest_control(),
            Interval.require()
        ],
    ))
async def change_npc(group: Group, x: RegexMatch, y: RegexMatch, member: Member,npc:RegexMatch):
    if not x.matched and y.matched:
        return await safeSendGroupMessage(
                    group, MessageChain.create("移动角色的时候需要带上位置哦~"))
    if not npc.matched:
        return await safeSendGroupMessage(
                    group, MessageChain.create("移动角色的时候需要带上角色名字哦~"))
    
    x = x.result.asDisplay()
    y = y.result.asDisplay()
    npc=npc.result.asDisplay()
    
    gid = str(group.id)
    x = ord(x.upper()) - 65
    y = int(y)
    config = await load_config(CONFIG_FILE)
    if gid in MAP:
        file = MAP[gid]["bg"].copy()
        cell_size = config[gid]
        w = 0
        if not True in [npc in i for i in MAP[gid]["array"]]:
            return await safeSendGroupMessage(group,
                                              MessageChain.create("请先加入地图"))
        if npc not in MAP[gid]["pet"]:
            return await safeSendGroupMessage(group,
                                              MessageChain.create("请先将NPC加入地图再移动哦~"))
        for i in MAP[gid]["array"]:
            h = 0
            for j in i:
                if j == npc:
                    MAP[gid]["array"][w][h] = 0
                    MAP[gid]["array"][x][y] = npc
                    # print(w, h)
                    # print(MAP[gid]["array"])
                h = h + 1
            w = w + 1
        maker = line_maker(file=file, cell_size=cell_size)
        img = maker.post_array(pet_dict=MAP[gid]["pet"],
                               bg_array=MAP[gid]["array"])
        await safeSendGroupMessage(group, MessageChain.create("移动地图成功"))
        await safeSendGroupMessage(group,
                                   MessageChain.create(Image(data_bytes=img)))
        pass
    else:
        await safeSendGroupMessage(group, MessageChain.create("请先创建地图"))
