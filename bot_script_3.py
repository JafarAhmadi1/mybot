import instaloader
from telegram import Update, InputMediaPhoto, InputMediaVideo, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from io import BytesIO
import aiohttp
import os
from dotenv import load_dotenv

# بارگذاری متغیرهای محیطی از فایل .env
load_dotenv()

# دریافت توکن از متغیر محیطی
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
# اگر توکن وجود نداشت، خطا بده
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("توکن یافت نشد! لطفا متغیر محیطی TELEGRAM_BOT_TOKEN را تنظیم کنید.")

L = instaloader.Instaloader(
    download_video_thumbnails=False,
    save_metadata=False,
    compress_json=False
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام! لینک پست اینستاگرام رو بفرست تا برات دانلود کنم.")

async def download_instagram_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if "instagram.com" not in url:
        await update.message.reply_text("لطفا یک لینک معتبر اینستاگرام ارسال کنید.")
        return

    try:
        await update.message.reply_text("در حال دانلود پست، لطفا صبر کنید...")
        shortcode = url.rstrip('/').split("/")[-1]
        post = instaloader.Post.from_shortcode(L.context, shortcode)

        if post.typename == "GraphVideo":
            video_url = post.video_url
            async with aiohttp.ClientSession() as session:
                async with session.get(video_url) as resp:
                    if resp.status == 200:
                        video_data = await resp.read()
                        await update.message.reply_video(
                            video=InputFile(BytesIO(video_data), filename="video.mp4"),
                            caption=post.caption if post.caption else None
                        )
                    else:
                        await update.message.reply_text("خطا در دانلود ویدیو.")

        elif post.typename == "GraphImage":
            image_url = post.url
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as resp:
                    if resp.status == 200:
                        image_data = await resp.read()
                        await update.message.reply_photo(
                            photo=InputFile(BytesIO(image_data), filename="image.jpg"),
                            caption=post.caption if post.caption else None
                        )
                    else:
                        await update.message.reply_text("خطا در دانلود عکس.")

        elif post.typename == "GraphSidecar":
            media_group = []
            async with aiohttp.ClientSession() as session:
                for idx, node in enumerate(post.get_sidecar_nodes()):
                    if node.is_video:
                        media_url = node.video_url
                    else:
                        media_url = node.url

                    async with session.get(media_url) as resp:
                        if resp.status != 200:
                            continue

                        media_data = await resp.read()
                        if node.is_video:
                            media = InputMediaVideo(
                                media=InputFile(BytesIO(media_data), filename=f"video_{idx}.mp4"),
                                caption=post.caption if idx == 0 and post.caption else None
                            )
                        else:
                            media = InputMediaPhoto(
                                media=InputFile(BytesIO(media_data), filename=f"image_{idx}.jpg"),
                                caption=post.caption if idx == 0 and post.caption else None
                            )
                        media_group.append(media)

                        if len(media_group) >= 10:
                            await update.message.reply_media_group(media=media_group)
                            media_group = []

                if media_group:
                    await update.message.reply_media_group(media=media_group)

        else:
            await update.message.reply_text("نوع پست پشتیبانی نمیشود.")

    except Exception as e:
        await update.message.reply_text(f"خطا: {str(e)}")

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_instagram_post))
    print("ربات فعال شد...")
    app.run_polling()

if __name__ == '__main__':

    main()



    