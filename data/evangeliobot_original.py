import os, logging, random, textwrap, importlib.util, pathlib
from typing import Optional, List, Dict, Any
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
TELEGRAM_MAX = 4096

# Placeholders (se sobreescriben si hay datos.py)
CORAN: Dict[str, List[List[Any]]] = {}
EVANGELIO: List[str] = []
BIBLIA: List[str] = []
GITA: List[Dict[str, Any]] = []

# Carga opcional desde /opt/evangelio/datos.py
p = pathlib.Path("/opt/evangelio/datos.py")
if p.exists():
    spec = importlib.util.spec_from_file_location("datos", str(p))
    datos = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(datos)     # ejecuta SOLO ese fichero de datos
    CORAN = getattr(datos, "CORAN", CORAN)
    EVANGELIO = getattr(datos, "EVANGELIO", EVANGELIO)
    BIBLIA = getattr(datos, "BIBLIA", BIBLIA)
    GITA = getattr(datos, "GITA", GITA)
    logger.info("✔ Textos cargados desde datos.py")
else:
    logger.warning("⚠ No existe /opt/evangelio/datos.py")

async def _send_long(update: Update, text: str) -> None:
    for chunk in textwrap.wrap(text or "⚠ Sin contenido", TELEGRAM_MAX):
        await update.message.reply_text(chunk)

def _sample_no_repeat(pool: List[str], last: Optional[str]) -> str:
    if not pool: return "⚠ Lista vacía"
    if len(pool) == 1: return pool[0]
    choice = random.choice(pool)
    while choice == last:
        choice = random.choice(pool)
    return choice

def frag_coran(last: Optional[str]) -> str:
    if not CORAN: return "⚠️ CORAN no está cargado."
    sura = random.choice(list(CORAN))
    n, txt = random.choice(CORAN[sura])
    return f"{sura}, Aleya {n}:\n{txt}"

def frag_evangelio(last: Optional[str]) -> str:
    return _sample_no_repeat(EVANGELIO, last) if EVANGELIO else "⚠️ EVANGELIO no está cargado."

def frag_biblia(last: Optional[str]) -> str:
    return _sample_no_repeat(BIBLIA, last) if BIBLIA else "⚠️ BIBLIA no está cargada."

def frag_gita(last_id: Optional[int]) -> tuple[str, Optional[int]]:
    if not GITA: return "⚠️ GITA no está cargada.", None
    sloka = random.choice(GITA)
    if last_id is not None and len(GITA) > 1:
        while sloka["id"] == last_id:
            sloka = random.choice(GITA)
    return f"Śloka {sloka['verso']}:\n{sloka['texto']}", sloka["id"]

async def start_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Comandos: /start /ping /coran /evangelio /biblia /gita")

async def ping_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("pong")

async def coran_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    txt = frag_coran(ctx.chat_data.get("ultimo_coran"))
    ctx.chat_data["ultimo_coran"] = txt
    await _send_long(update, txt)

async def evangelio_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    txt = frag_evangelio(ctx.chat_data.get("ultimo_evangelio"))
    ctx.chat_data["ultimo_evangelio"] = txt
    await _send_long(update, txt)

async def biblia_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    txt = frag_biblia(ctx.chat_data.get("ultimo_biblia"))
    ctx.chat_data["ultimo_biblia"] = txt
    await _send_long(update, txt)

async def gita_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    last_id = ctx.chat_data.get("ultimo_gita_id")
    txt, new_id = frag_gita(last_id)
    if new_id is not None:
        ctx.chat_data["ultimo_gita_id"] = new_id
    await _send_long(update, txt)

async def error_handler(update: object, ctx: ContextTypes.DEFAULT_TYPE):
    logger.exception("Excepción no controlada")
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text("⚠️ Algo salió mal, intenta de nuevo.")

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN no está definido (edita /etc/evangelio.env)")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("ping",  ping_cmd))
    app.add_handler(CommandHandler("coran", coran_cmd))
    app.add_handler(CommandHandler("evangelio", evangelio_cmd))
    app.add_handler(CommandHandler("biblia", biblia_cmd))
    app.add_handler(CommandHandler("gita", gita_cmd))
    app.add_error_handler(error_handler)
    logger.info("Bot iniciado – polling activo.")
    app.run_polling()

if __name__ == "__main__":
    main()
