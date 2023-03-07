from typing import Union, Optional

from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import GroupMessage, FriendMessage
from graia.ariadne.event.mirai import NewFriendRequestEvent
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import At, Image, Plain
from graia.ariadne.model import Group, Friend, Member
from graia.ariadne.util.interrupt import FunctionWaiter
from graia.broadcast.builtin.decorators import Depend
from graia.broadcast.exceptions import ExecutionStop, PropagationCancelled

from graia.saya import Channel
from graia.saya.builtins.broadcast.schema import ListenerSchema
from priority import LISTEN_PRIORIY
import json

channel = Channel.current()
channel.name("Common")
channel.description("Common Events")
channel.author("Shuimen")

with open("config.json") as f:
    config = json.load(f)
ADMIN = config["qqbot"]["admin"]


@channel.use(ListenerSchema(
    listening_events=[NewFriendRequestEvent],
    priority=LISTEN_PRIORIY["COMMON_ADD_FRIEND"]
))
async def add_new_friend(app: Ariadne, event: NewFriendRequestEvent):
    await app.send_friend_message(
        ADMIN,
        MessageChain(
            Plain('===<SYSTEM>===\n'),
            Plain(f'收到添加好友事件\nQQ：{event.supplicant}\n昵称：{event.nickname}\n'),
            Plain(event.message) if event.message else Plain('无附加信息'),
            Plain('\n\n是否同意申请？同意/Y，拒绝/N'),
        ),
    )

    async def waiter(waiter_friend: Friend, waiter_message: MessageChain) -> Optional[tuple[bool, int]]:
        # 之所以把这个 waiter 放在 new_friend 里面，是因为我们需要用到 app
        # 假如不需要 app 或者 打算通过传参等其他方式获取 app，那也可以放在外面
        if waiter_friend.id == ADMIN:
            saying = waiter_message.display
            if saying == '同意' or saying == 'Y':
                return True, waiter_friend.id
            elif saying == '拒绝' or saying == 'N':
                return False, waiter_friend.id
            else:
                await app.send_friend_message(waiter_friend, MessageChain(
                    Plain('===<SYSTEM>===\n'),
                    Plain('请发送同意/Y或拒绝/N')
                ))
                raise PropagationCancelled

    def check_member(member: int):
        async def check_member_deco(app: Ariadne, friend: Friend):
            if friend.id != member:
                raise ExecutionStop
        return Depend(check_member_deco)

    result = await FunctionWaiter(
        waiter,
        [FriendMessage],
        decorators=[check_member(ADMIN)],
        priority=LISTEN_PRIORIY["COMMON_CHECK_FRIEND"],
        block_propagation=True
    ).wait()
    if result[0]:
        await event.accept()  # 同意好友请求
        await app.send_friend_message(
            ADMIN,
            MessageChain(
                Plain('===<SYSTEM>===\n'),
                Plain(f'Bot 管理员 {result[1]} 已同意 {event.nickname}({event.supplicant}) 的好友请求')
            ),
        )
    else:
        await event.reject('Bot 管理员拒绝了你的好友请求')  # 拒绝好友请求
        await app.send_friend_message(
            ADMIN,
            MessageChain(
                Plain('===<SYSTEM>===\n'),
                Plain(f'Bot 管理员 {result[1]} 已拒绝 {event.nickname}({event.supplicant}) 的好友请求')
            ),
        )