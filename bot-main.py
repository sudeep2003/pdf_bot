import logging
import os
from io import BytesIO

from PIL import Image
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, CallbackContext, MessageHandler, filters, ConversationHandler

load_dotenv()
TOKEN = os.getenv('TOKEN')

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        f"Hello {update.effective_user.first_name}!\n\nTo create images to pdf:\n\t1.Tap on 'menu'\n\t2.Press '/create_pdf'\n\t3.Send photos\n\t4.Send message '/ok' for done or '/cancel' for cancel process.")
    print(f"{update.effective_user.first_name} --> starting")


def unknown_file(update: Update, context: CallbackContext):
    """Handler for unknown file types."""
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Sorry, I can only process image files. Please send me a photo."
    )


def convert_images_to_pdf(image_files):
    images = []
    for image_file in image_files:
        image = Image.open(image_file)
        images.append(image)

    pdf_bytes = BytesIO()
    images[0].save(pdf_bytes, "PDF", save_all=True, append_images=images[1:])
    pdf_bytes.seek(0)
    return pdf_bytes


async def create_pdf(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    reply_keyboard = [['/ok'], ['/cancel']]
    message = update.message
    await message.reply_text("Send photos to convert to PDF.", reply_markup=ReplyKeyboardMarkup(
        reply_keyboard, one_time_keyboard=True
    ))
    print(f"{update.effective_user.first_name} --> creating")
    context.user_data["chat_id"] = chat_id
    context.user_data["image_files"] = []
    return 1


# async def receive_image(update: Update, context: CallbackContext):
#     chat_id = context.user_data["chat_id"]
#     message = update.message
#     file_id = message.photo[-1].file_id
#     file = await context.bot.get_file(file_id)
#     file_path = await file.download_to_drive()
#     context.user_data["image_files"].append(file_path)
#     await message.reply_text("Send more photos or type /ok to create the PDF.")
#     return 1

async def receive_image(update: Update, context: CallbackContext):
    chat_id = context.user_data["chat_id"]
    message = update.message
    file_id = message.photo[-1].file_id
    file = await context.bot.get_file(file_id)
    file_bytes = await file.download_as_bytearray()
    file_path = BytesIO(file_bytes)
    context.user_data["image_files"].append(file_path)
    return 1


async def process_ok(update: Update, context: CallbackContext):
    try:
        chat_id = context.user_data["chat_id"]
        message = update.message
        if context.user_data["image_files"]:
            pdf_bytes = convert_images_to_pdf(context.user_data["image_files"])
            await context.bot.send_document(chat_id=chat_id, document=pdf_bytes, filename="converted_pdf.pdf")
            await message.reply_text("PDF created and sent.", reply_markup=ReplyKeyboardRemove())
            print(f"{update.effective_user.first_name}--> Received")
        else:
            # print("No images!")
            await message.reply_text("No images founded.", reply_markup=ReplyKeyboardRemove())
    except Exception as e:
        await update.message.reply_text("Not processed.", reply_markup=ReplyKeyboardRemove())
        print(f"{update.effective_user.first_name} --> An error has occurred: {e}")
    return ConversationHandler.END


def main(cancel=None):
    application = (
        Application.builder()
        .token(TOKEN)
        .build()
    )

    application.add_handler(CommandHandler("Start", start))
    # application.add_handler(CommandHandler("Create_pdf", create_pdf))
    # application.add_handler(MessageHandler(filters.PHOTO, receive_image))
    # application.add_handler(MessageHandler(filters.Document & ~filters.PHOTO, unknown_file))
    # application.add_handler(MessageHandler((filters.Document | filters.VIDEO | filters.AUDIO | filters.VOICE) & ~filters.PHOTO, unknown_file))

    application.add_handler(CommandHandler("ok", process_ok))

    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler("create_pdf", create_pdf)],
        states={
            1: [MessageHandler(filters.PHOTO | filters.TEXT & ~filters.COMMAND, receive_image)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    ))
    # ...and the error handler
    # application.add_error_handler(error_handler)

    # Run the bot until the user presses Ctrl-C

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
