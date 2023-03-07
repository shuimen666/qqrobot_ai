from typing import Union
from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import GroupMessage, FriendMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import At, Image, Plain
from graia.ariadne.message.parser.base import DetectPrefix, ContainKeyword
from graia.ariadne.model import Group, Friend

from graia.saya import Channel
from graia.saya.builtins.broadcast.schema import ListenerSchema
import chatgpt
import datetime
import base64
import re
from priority import LISTEN_PRIORIY

channel = Channel.current()
channel.name("ChatGPT")
channel.description("ChatGPT API")
channel.author("Shuimen")


@channel.use(ListenerSchema(
    listening_events=[GroupMessage, FriendMessage],
    priority=LISTEN_PRIORIY["CHATGPT"]
))
async def generate_normal_answer(app: Ariadne, sender: Union[Group, Friend], message: MessageChain, event:Union[GroupMessage, FriendMessage]):
    if At(app.account) in message or isinstance(sender, Friend):
        prompt_str = str(message.include(Plain)).strip()
        if prompt_str.startswith("#") or prompt_str.startswith("$"):
            return

        response = await chatgpt.chatGPTBot.request_answer(event.sender.id, prompt_str)
        message_chain = MessageChain("" if isinstance(sender, Friend) else At(event.sender))
        message_chain += MessageChain(Plain(response))
        await app.send_message(
            sender,
            message_chain,
        )


@channel.use(ListenerSchema(
    listening_events=[GroupMessage, FriendMessage],
    priority=LISTEN_PRIORIY["CHATGPT"],
    decorators=[ContainKeyword("$创建会话")]
))
async def create_conversation(app: Ariadne, sender: Union[Group, Friend], message: MessageChain, event:Union[GroupMessage, FriendMessage]):
    if At(app.account) in message or isinstance(sender, Friend):
        prompt_str = str(message.include(Plain)).strip()
        now = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        merged_str = now + str(sender.id)
        unique_str = base64.b64encode(merged_str.encode('utf-8')).decode('utf-8')

        chatgpt.chatGPTBot.change_channel(event.sender.id, unique_str)

        response = "创建成功！会话ID为"+unique_str+"。已经为您切换到本会话。"
        message_chain = MessageChain("" if isinstance(sender, Friend) else At(event.sender))
        message_chain += MessageChain(Plain(response))
        await app.send_message(
            sender,
            message_chain,
        )


@channel.use(ListenerSchema(
    listening_events=[GroupMessage, FriendMessage],
    priority=LISTEN_PRIORIY["CHATGPT"]
))
async def regenerate_answer(app: Ariadne, sender: Union[Group, Friend], message: MessageChain, event:Union[GroupMessage, FriendMessage]):
    if At(app.account) in message or isinstance(sender, Friend):
        prompt_str = str(message.include(Plain)).strip()

        if prompt_str.startswith("$regenerate") or prompt_str.startswith("$重新生成"):
            response = await chatgpt.chatGPTBot.regenerate_answer(event.sender.id)
            message_chain = MessageChain("" if isinstance(sender, Friend) else At(event.sender))
            message_chain += MessageChain(Plain(response))
            await app.send_message(
                sender,
                message_chain,
            )


@channel.use(ListenerSchema(
    listening_events=[GroupMessage, FriendMessage],
    priority=LISTEN_PRIORIY["CHATGPT"]
))
async def clear_logs(app: Ariadne, sender: Union[Group, Friend], message: MessageChain, event:Union[GroupMessage, FriendMessage]):
    if At(app.account) in message or isinstance(sender, Friend):
        prompt_str = str(message.include(Plain)).strip()

        if prompt_str.startswith("$clear") or prompt_str.startswith("$清空"):
            chatgpt.chatGPTBot.reset_log(event.sender.id)
            response = "当前会话已经清空。"
            message_chain = MessageChain("" if isinstance(sender, Friend) else At(event.sender))
            message_chain += MessageChain(Plain(response))
            await app.send_message(
                sender,
                message_chain,
            )


@channel.use(ListenerSchema(
    listening_events=[GroupMessage, FriendMessage],
    priority=LISTEN_PRIORIY["CHATGPT"],
    decorators=[ContainKeyword("$切换会话")]
))
async def change_conversation(app: Ariadne, sender: Union[Group, Friend], message: MessageChain, event:Union[GroupMessage, FriendMessage]):
    if At(app.account) in message or isinstance(sender, Friend):
        prompt_str = str(message.include(Plain)).strip()
        match = re.search(r'\$切换会话(.+)', prompt_str)
        if match:
            unique_str = match.group(1)
            chatgpt.chatGPTBot.change_channel(sender.id, unique_str)

            response = "切换成功！已经为您切换到会话" + unique_str + "。"
            message_chain = MessageChain("" if isinstance(sender, Friend) else At(event.sender))
            message_chain += MessageChain(Plain(response))
            await app.send_message(
                sender,
                message_chain,
            )


@channel.use(ListenerSchema(
    listening_events=[GroupMessage, FriendMessage],
    priority=LISTEN_PRIORIY["CHATGPT"]
))
async def set_system_prompt(app: Ariadne, sender: Union[Group, Friend], message: MessageChain, event:Union[GroupMessage, FriendMessage]):
    if At(app.account) in message or isinstance(sender, Friend):
        prompt_str = str(message.include(Plain)).strip()
        if prompt_str.startswith("$set") or prompt_str.startswith("$设置系统"):
            match1 = re.search(r'\$set(.+)', prompt_str)
            match2 = re.search(r'\$设置系统(.+)', prompt_str)
            match = match1 if match1 else match2
            system_prompt = match.group(1)
            chatgpt.chatGPTBot.set_system_prompt(event.sender.id, system_prompt)
            response = "已设置系统设定为：" + system_prompt
            message_chain = MessageChain("" if isinstance(sender, Friend) else At(event.sender))
            message_chain += MessageChain(Plain(response))
            await app.send_message(
                sender,
                message_chain,
            )