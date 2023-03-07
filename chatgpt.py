import openai
import json

with open("config.json") as f:
    config = json.load(f)
openai.api_key = config["chatgpt"]["api_key"]
openai.proxy = config["chatgpt"]["proxy"]

BOT_ROLE = 'assistant'
USER_ROLE = 'user'
SYSTEM_ROLE = 'system'

ChannelSystemConf = {
    'ai_painting_prompt_generator': "你是一个AI绘画助手，我会告诉你我需要生成的图画的需求，你只需要回答用英文准确的提供多个描述的prompt，每一个prompt之间用,隔开，并且不需要引号和句号。",
}


class ChatChannel:
    def __init__(self, system_prompt=None):
        self.messages = []
        self.system_prompt = system_prompt
        self.reset_log()

    def set_system_prompt(self, prompt):
        self.system_prompt = prompt
        if len(self.messages) > 0 and self.messages[0]['role'] == SYSTEM_ROLE:
            self.messages[0]['content'] = prompt
        else:
            self.messages.insert(0, {'role': SYSTEM_ROLE, 'content': prompt})

    async def request_answer(self):
        res = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=self.messages,
        )
        answer = res["choices"][0]["message"]["content"]
        self.add_bot_content(answer)
        return answer

    async def request_answer_with_content(self, content):
        self.add_user_content(content)
        res = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=self.messages,
        )
        answer = res["choices"][0]["message"]["content"]
        self.add_bot_content(answer)
        return answer

    def reset_log(self):
        self.messages = [] if self.system_prompt is None else [{'role': SYSTEM_ROLE, 'content': self.system_prompt}]

    def add_user_content(self, content):
        self.messages.append({'role': USER_ROLE, 'content': content})

    def add_bot_content(self, content):
        self.messages.append({'role': BOT_ROLE, 'content': content})


class ChatGPTBot:
    def __init__(self):
        self.dictionary = dict()
        self.user_conversation = dict()

    def get_channel(self, qid):
        key = self.user_conversation.get(qid, str(qid))
        if self.dictionary.get(key) is None:
            self.dictionary[key] = ChatChannel()
        return self.dictionary.get(key)

    async def request_answer(self, qid, content):
        return await self.get_channel(qid).request_answer_with_content(content)

    async def regenerate_answer(self, qid):
        channel = self.get_channel(qid)
        last = len(channel.messages) - 1
        if last > 0:
            if channel.messages[last]['role'] == BOT_ROLE:
                channel.messages.pop()
            return await channel.request_answer()
        return None

    def reset_log(self, qid):
        return self.get_channel(qid).reset_log()

    def change_channel(self, qid, channelID):
        if self.dictionary.get(channelID) is None:
            self.dictionary[channelID] = ChatChannel()
        self.user_conversation[qid] = channelID

    def set_system_prompt(self, qid, prompt):
        channel = self.get_channel(qid)
        channel.set_system_prompt(prompt)

chatGPTBot = ChatGPTBot()
for key in ChannelSystemConf:
    channel = chatGPTBot.get_channel(key)
    channel.set_system_prompt(ChannelSystemConf[key])
