from typing import Union

from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import GroupMessage, FriendMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import At, Image, Plain
from graia.ariadne.message.parser.base import DetectPrefix
from graia.ariadne.model import Group, Friend

from graia.saya import Channel
from graia.saya.builtins.broadcast.schema import ListenerSchema
import scenario
import chatgpt
import re
from priority import LISTEN_PRIORIY

channel = Channel.current()
channel.name("Scenario")
channel.description("Scenario painting")
channel.author("Shuimen")


@channel.use(ListenerSchema(
    listening_events=[GroupMessage, FriendMessage],
    priority=LISTEN_PRIORIY["SCENARIO"]
))
async def generate_image(app: Ariadne, sender: Union[Group, Friend], message: MessageChain, event:Union[GroupMessage, FriendMessage]):
    if At(app.account) in message:
        prompt_str = str(message.include(Plain)).strip()
        if re.match("#查看.*", prompt_str):
            return
        if not prompt_str.startswith("#"):
            return

        prompt_str = prompt_str[1:]
        params = settle_params(prompt_str)
        back_message = MessageChain("" if isinstance(sender, Friend) else At(event.sender))
        back_message += MessageChain(f"收到！正在生成图片，")
        if params.get("id", None) is not None:
            back_message += MessageChain(f"模型ID为", str(params["id"]), "。")
        if params.get("describe", None) is not None:
            message_gpt = MessageChain("" if isinstance(sender, Friend) else At(event.sender))
            message_gpt += MessageChain(Plain("正在根据您的描述生成prompts...请稍等。"))
            await app.send_message(
                sender,
                message_gpt,
            )
            chatgpt.chatGPTBot.reset_log('ai_painting_prompt_generator')
            extra_prompts = await chatgpt.chatGPTBot.request_answer('ai_painting_prompt_generator', params["describe"])
            params["prompt"].extend(extra_prompts.split(","))
            back_message += MessageChain(f"描述为", str(params["describe"]), "。")
        if params.get("prompt", None) is not None:
            back_message += MessageChain(f"prompt为", ", ".join(params["prompt"]), "。")
        if params.get("negative_prompt", None) is not None:
            back_message += MessageChain(f"negative_prompt为", ", ".join(params["negative_prompt"]), "。")
        if params.get("steps", None) is not None:
            back_message += MessageChain(f"steps为", str(params["steps"]), "。")
        if params.get("nums", None) is not None:
            back_message += MessageChain(f"nums为", str(params["nums"]), "。")
        if params.get("guidance", None) is not None:
            back_message += MessageChain(f"guidance为", str(params["guidance"]), "。")
        await app.send_message(
            sender,
            back_message,
        )

        images = await scenario.get_images(params)
        message_chain = MessageChain("" if isinstance(sender, Friend) else At(event.sender))
        for image in images:
            message_chain += MessageChain(Image(path=image))
        await app.send_message(
            sender,
            message_chain,
        )

def settle_params(input_str):
    params = dict()
    string_list = input_str.split(",")
    now = "prompt"
    params["prompt"] = []
    for item in string_list:
        item = item.strip()
        if item.startswith("steps"):
            params["steps"] = int(re.split("[:=]", item)[1])
        elif item.startswith("nums"):
            params["nums"] = int(re.split("[:=]", item)[1])
        elif item.startswith("guidance"):
            params["guidance"] = float(re.split("[:=]", item)[1])
        elif item.startswith("id"):
            params["id"] = re.split("[:=]", item)[1]
        elif item.startswith("prompt"):
            now = "prompt"
            params["prompt"].append(re.split("[:=]", item)[1].strip())
        elif item.startswith("negative_prompt"):
            now = "negative_prompt"
            params["negative_prompt"] = []
            params["negative_prompt"].append(re.split("[:=]", item)[1].strip())
        elif item.startswith("describe"):
            params["describe"] = re.split("[:=]", item)[1]
        else:
            params[now].append(item)
    print(params)
    return params


@channel.use(ListenerSchema(
    listening_events=[GroupMessage, FriendMessage],
    priority=LISTEN_PRIORIY["SCENARIO"]
))
async def show_model(app: Ariadne, sender: Union[Group, Friend], message: MessageChain, event:Union[GroupMessage, FriendMessage]):
    if At(app.account) in message:
        prompt_str = str(message.include(Plain)).strip()

        if re.match("#查看.*模型.*", prompt_str):
            models = await scenario.get_model()
            message_chain = MessageChain("" if isinstance(sender, Friend) else At(event.sender), f"\n")
            i = 1
            for model in models:
                message_chain += MessageChain(f"{i}.{model['name']}, id={model['id']}\n")
                i += 1
            await app.send_message(
                sender,
                message_chain,
            )
        elif prompt_str.startswith("查看"):
            model_name = prompt_str.removeprefix("查看").strip()
            now_models = scenario.now_models
            for model in now_models:
                if model.get("name") == model_name or model.get("id") == model_name:
                    message_chain = MessageChain("" if isinstance(sender, Friend) else At(event.sender), f"\n") + MessageChain(f"{model['name']}, id={model['id']}\n")
                    for image in model.get("images", []):
                        url = image.get("downloadUrl", "")
                        if url != "":
                            message_chain += MessageChain(Image(url=url))
                    await app.send_message(
                        sender,
                        message_chain,
                    )
                    break
            print(model_name)
