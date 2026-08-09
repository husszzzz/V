import telebot
import os
from PIL import Image

# توكن البوت مالتك
TOKEN = "8774379921:AAEx_USlCPgXD8Jm_WccoR6mY7yhAjW0mK0"
bot = telebot.TeleBot(TOKEN)

# قاموس لحفظ معلومات المستخدم
user_state = {}

@bot.message_handler(content_types=['document'])
def handle_document(message):
    # التأكد من حجم الملف (تليجرام يحد البوتات بـ 20 ميجا للتحميل)
    if message.document.file_size > 20 * 1024 * 1024:
        bot.reply_to(message, "⚠️ حجم الملف أكبر من 20 ميكا، البوت ما يگدر يحمله بسبب قيود تليجرام.")
        return

    # حفظ ايدي الملف واسمه
    user_state[message.chat.id] = {
        'file_id': message.document.file_id,
        'file_name': message.document.file_name
    }
    bot.reply_to(message, "✅ استلمت الملف! هسة دزلي الصورة اللي تريدها تصير غلاف (Thumbnail) للملف.")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    chat_id = message.chat.id
    if chat_id not in user_state:
        bot.reply_to(message, "⚠️ دزلي الملف بالبداية يا بطل!")
        return

    msg = bot.reply_to(message, "⏳ جاري دمج الصورة كغلاف للملف... ثواني.")

    try:
        # 1. تحميل الملف (الـ IPA أو أي ملف)
        doc_info = bot.get_file(user_state[chat_id]['file_id'])
        doc_file = bot.download_file(doc_info.file_path)
        doc_path = f"file_{chat_id}.ipa"
        with open(doc_path, 'wb') as f:
            f.write(doc_file)

        # 2. تحميل الصورة
        photo_info = bot.get_file(message.photo[-1].file_id)
        photo_file = bot.download_file(photo_info.file_path)
        photo_path = f"photo_{chat_id}.jpg"
        with open(photo_path, 'wb') as f:
            f.write(photo_file)

        # 3. تصغير الصورة (شرط تليجرام الصارم: الغلاف لازم يكون 320x320 كحد أقصى)
        thumb_path = f"thumb_{chat_id}.jpg"
        with Image.open(photo_path) as img:
            img.thumbnail((320, 320))
            img.save(thumb_path, format="JPEG")

        # 4. إرسال الملف مع الغلاف الجديد
        bot.edit_message_text("✅ كملت! جاري رفع الملف للتليجرام...", chat_id=chat_id, message_id=msg.message_id)

        with open(doc_path, 'rb') as doc_to_send, open(thumb_path, 'rb') as thumb_to_send:
            bot.send_document(
                chat_id,
                doc_to_send,
                thumbnail=thumb_to_send,
                caption="🔥 تم تركيب الغلاف بنجاح!\n\n👨🏻‍💻 @hassanyIPA",
                visible_file_name=user_state[chat_id]['file_name']
            )

        # 5. تنظيف السيرفر (مسح الملفات حتى ما ينترس)
        os.remove(doc_path)
        os.remove(photo_path)
        os.remove(thumb_path)
        del user_state[chat_id]

    except Exception as e:
        bot.reply_to(message, f"❌ صارت مشكلة: {str(e)}")

print("🔥 بوت تغيير الأغلفة اشتغل بنجاح!")
bot.polling(none_stop=True)
