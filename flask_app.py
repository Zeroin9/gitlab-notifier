# Bot for telegram with Flask + pyTelegramBotAPI to send notification about Gitlab activity
from flask import Flask, request
import telebot
import time

app = Flask(__name__)

@app.route('/')
def hello_world():
    return 'Hello from Flask!'

with open('settings.txt', 'r') as reader:
    this_url = reader.readline().strip()
    bot_token = reader.readline().strip()
    chat_ids = reader.readline().strip().split(',')
    tgsecret = reader.readline().strip()
    glsecret = reader.readline().strip()

action_translation = {
    "open": "открыл",
    "close": "закрыл",
    "merge": "смержил",
    "approved": "одобрил",
    "update": "обновил"
}

bot = telebot.TeleBot(bot_token, threaded=False)
bot.remove_webhook()
time.sleep(10)
bot.set_webhook(url="{}{}".format(this_url, tgsecret))

@app.route('/{}'.format(tgsecret), methods=["POST"])
def tg_webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "ok", 200

@bot.message_handler(func=lambda message: message.text.lower() == "чек")
def handle_message(message):
    chat_id = message.chat.id
    thread_id = message.message_thread_id
    if thread_id:
        print(f"Received message from chat_id: {chat_id}, thread_id: {thread_id}")
        bot.send_message(chat_id, f"Received message from `chat_id`: {chat_id}, `thread_id`: {thread_id}", parse_mode='Markdown', message_thread_id=thread_id)
    else:
        print(f"Received message from chat_id: {chat_id}")
        bot.send_message(chat_id, f"Received *check* message from `chat_id`: {chat_id}", parse_mode='Markdown')

def broadcast_message(message):
    for chat_info in chat_ids:
        if ':' in chat_info:
            chat_id, thread_id = chat_info.split(':')
        else:
            chat_id, thread_id = chat_info, None
        try:
            if thread_id:
                bot.send_message(chat_id, message, parse_mode='MarkdownV2', message_thread_id=int(thread_id))
            else:
                bot.send_message(chat_id, message, parse_mode='MarkdownV2')
            print(f"Message sent to chat_id: {chat_id}, thread_id: {thread_id}")
        except Exception as e:
            print(f"Failed to send message to chat_id: {chat_id}, thread_id: {thread_id}. Error: {e}")

@app.route('/{}'.format(glsecret), methods=["POST"])
def gl_webhook():
    event = request.headers.get('X-Gitlab-Event')
    payload = request.json

    if event in ["Issue Hook", "Merge Request Hook"]:
        user = payload["user"]["name"]
        title = payload["object_attributes"]["title"]
        url = payload["object_attributes"]["url"]
        action = payload["object_attributes"]["action"]
        number = payload["object_attributes"]["iid"]
        state = payload["object_attributes"]["state"]

        if event == "Issue Hook" and action != "open":
            return "ok", 200

        if event == "Merge Request Hook" and state != "opened" and action != "merge":
            return "ok", 200

        # Генерируем сообщение
        message = generate_gitlab_message(event, user, number, title, url, action)
        # Отправляем сообщение
        broadcast_message(message)

    return "ok", 200

def escape_markdown(text):
    escape_chars = "_*[]()~`>#+-=|{}.!"
    return "".join(f"\\{char}" if char in escape_chars else char for char in text)

def generate_gitlab_message(event_type, user, number, title, url, action):
    user_escaped = escape_markdown(user)
    title_escaped = escape_markdown(title)
    url_escaped = escape_markdown(url)
    event_type_escaped = escape_markdown(event_type)

    action_translated = action_translation.get(action, action)

    if event_type == "Issue Hook":
        return f"*{user_escaped}* {action_translated} ишью *\#{number} \"{title_escaped}\"*\n\n[{url_escaped}]({url_escaped})"
    elif event_type == "Merge Request Hook":
        return f"*{user_escaped}* {action_translated} реквест *\!{number} \"{title_escaped}\"*\n\n[{url_escaped}]({url_escaped})"
    else:
        return f"Произошло событие *{event_type_escaped}*, но формат сообщения для него не определён."