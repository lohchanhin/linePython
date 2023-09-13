# -*- coding: utf-8 -*-
"""
Created on Wed Sep 13 11:22:32 2023

@author: User
"""

from fastapi import FastAPI, HTTPException, Request
from linebot import LineBotApi, WebhookParser
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ImageSendMessage
import os
import openai

app = FastAPI()

# 获取 LINE 和 OpenAI 密钥
channel_access_token = os.getenv('CHANNEL_ACCESS_TOKEN')
channel_secret = os.getenv('CHANNEL_SECRET')
openai_api_key = os.getenv('OPENAI_API_KEY')
openai.api_key = openai_api_key

# 创建 LINE 客户端
line_bot_api = LineBotApi(channel_access_token)
parser = WebhookParser(channel_secret)

# 存储用户会话的对象
user_conversations = {}

@app.post("/callback")
async def handle_event(request: Request):
    body = await request.body()
    signature = request.headers.get('X-Line-Signature')

    try:
        events = parser.parse(body.decode('utf-8'), signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400)

    for event in events:
        if not isinstance(event, MessageEvent) or not isinstance(event.message, TextMessage):
            continue

        # 检查前两个字符是否是 "畫圖"
        if event.message.text.startswith("畫圖"):
            response = openai.Image.create(
                prompt=event.message.text[2:],  # 剩下的文本内容作为提示
                n=1,
                size="1024x1024"
            )
            
            imageUrl = response.data[0]['url']

            if not imageUrl:
                reply = TextSendMessage(text='生成图片失败或您的字眼不符合ai规范请修饰')
                line_bot_api.reply_message(event.reply_token, reply)
            else:
                image_message = ImageSendMessage(
                    original_content_url=imageUrl,
                    preview_image_url=imageUrl
                )
                line_bot_api.reply_message(event.reply_token, image_message)
            continue
        
        user_id = event.source.user_id

        # 如果不存在该用户的对话，为其创建一个
        if user_id not in user_conversations:
            user_conversations[user_id] = [{"role": "system", "content": '你是人工智能助理'}]

        # 将用户消息添加到会话中
        user_conversations[user_id].append({"role": "user", "content": event.message.text + '回答字数限制在1000以内'})

        # 如果会话长度超过 4 条消息，则删除最早的一条
        if len(user_conversations[user_id]) > 4:
            user_conversations[user_id].pop(0)

        # 由于您还没有给出文本处理的OpenAI部分，我假设与图片部分类似。如果有其他API，请替换此处
        assistant_reply = "此处是OpenAI回复文本"  # 这里需要替换为适当的调用

        user_conversations[user_id].append({"role": "assistant", "content": assistant_reply})

        reply = TextSendMessage(text=assistant_reply)
        line_bot_api.reply_message(event.reply_token, reply)

    return "OK"
