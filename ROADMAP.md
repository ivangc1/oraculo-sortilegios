# 🔮 El Oráculo de los Sortilegios — @oraculo_sortilegios_bot
## Hoja de Ruta Definitiva

---

## 1. Visión del Proyecto

Bot de Telegram para el grupo "La Taberna de los Sortilegios" (~2,600 miembros, ~100 activos) que ofrece lecturas de adivinación y consultas esotéricas, impulsado por Claude Sonnet 4.6 de Anthropic.

El bot actúa como **El Pezuñento** (Baphomet) — el oráculo residente de la taberna. Energía Marte/Aries: hermético con fuego, directo, humor oscuro y seco, no endulza las lecturas. Sabe de lo oculto porque lo ha vivido. Dice la verdad en la cara, pero si preguntas en serio la respuesta es profunda y precisa. Castellano peninsular con actitud, tuteo, sin arcaísmos pomposos.

**Presupuesto:** €200/año (~$218)
**Plazo de desarrollo:** 2-3 semanas con Claude Code
**Obligatoriamente público:** Solo funciona en el grupo, nunca en DM

---

## 2. Stack Técnico

| Componente | Tecnología | Notas |
|---|---|---|
| Lenguaje | **Python 3.13** | REPL mejorado, colores traceback, JIT experimental, ecosistema maduro |
| Framework Telegram | `python-telegram-bot` v22+ | Async, ConversationHandler, JobQueue, PicklePersistence |
| IA | API de Anthropic (Claude Sonnet 4.6) | **AsyncAnthropic**, prompt caching, API version pinned |
| Validación | `pydantic` v2 | model_validate(), errores traducidos a mensajes amigables |
| Base de datos | SQLite3 + `aiosqlite` | Async, WAL mode (requiere permisos directorio) |
| Astrología tropical | `kerykeion` v5 | Swiss Ephemeris wrapper, Placidus/Whole Sign |
| Astrología védica | `kerykeion` v5 sidereal | Lahiri nativo + nakshatras/dashas propios |
| Geocoding | `geopy` (Nominatim) | Caché local, rate limit lock, user_agent, ciudades homónimas |
| Timezone | `timezonefinder` + `zoneinfo` | Crítico para natales, limitaciones pre-1970 documentadas |
| Imágenes | `Pillow` | JPEG, LRU cache, file handles cerrados, fuente para etiquetas |
| Aleatoriedad | `random.SystemRandom` | /dev/urandom, criptográfico |
| Logging | `loguru` | backtrace=False, diagnose=False (no filtrar datos sensibles) |
| Config | `python-dotenv` + `pydantic-settings` | dev/prod, max_tokens configurable |
| Testing | `pytest` + `pytest-asyncio` | Unitarios + mocks API |
| Hosting | VPS propio (Debian 13) | Ya existente |
| Deploy | systemd service | Restart + graceful shutdown |

### requirements.txt — Versiones pineadas

```
python-telegram-bot[webhooks]==22.7
anthropic==0.86.0
pydantic==2.12.5
pydantic-settings==2.13.1
aiosqlite==0.22.1
kerykeion==5.12.6
pyswisseph==2.10.3.2
geopy==2.4.1
timezonefinder==8.2.1
Pillow==12.1.1
loguru==0.7.3
python-dotenv==1.2.2
pytest==9.0.2
pytest-asyncio==1.3.0
```

> **NOTA DE IMPLEMENTACION (marzo 2026):** Versiones actualizadas a las ultimas estables.
> kerykeion v5 soporta sidereal/Lahiri nativamente — pyswisseph ya NO es necesario como
> dependencia separada (viene como transitive dep de kerykeion). Se mantiene en la lista
> por si se necesitan calculos raw de Swiss Ephemeris en el futuro.

**Pinear versiones exactas.** Breaking changes entre versiones mayores de kerykeion (v3→v4), python-telegram-bot (v20→v21) y pyswisseph pueden romper el bot silenciosamente. Mantener un `requirements.lock` con `pip freeze` separado del `requirements.txt` si se prefieren rangos.

### Licencia: AGPL-3.0 obliga repo público

**Kerykeion es AGPL-3.0** (no GPL simple). Pyswisseph también es AGPL-3.0. AGPL es más restrictivo que GPL: cualquier uso en red (como un bot de Telegram) requiere que el código fuente esté disponible públicamente.

**El repo DEBE ser público.** No es una decisión — es un requisito legal. API keys, chat_id y tokens van en `.env` (que está en `.gitignore`), así que no hay riesgo de filtrar secretos.

Alternativa si se quiere repo privado: usar la API de pago de Kerykeion (AstrologerAPI) en vez de la librería directamente. Pero añade coste y dependencia de servicio externo.

### pyswisseph: compilación desde source en Python 3.13

Los wheels pre-compilados de pyswisseph solo llegan hasta CPython 3.11 (última release: junio 2023). En Python 3.13, `pip install pyswisseph` compilará desde el tarball source. Requiere en Debian 13:

```bash
sudo apt install build-essential python3-dev
```

Kerykeion depende de pyswisseph internamente — al instalar kerykeion, pyswisseph se compila automáticamente si no hay wheel. Verificar que la compilación funciona en el VPS antes de empezar desarrollo.

---

## 3. Arquitectura — Dos Capas Separadas

### Capa 1: BOT (Telegram)

- Recibe comandos y callbacks (callback_data ≤64 bytes, códigos cortos)
- **Bloqueo de peticiones concurrentes por usuario:** si tiene una petición en curso, rechaza nuevos comandos
- Gestiona onboarding y perfiles (SQLite)
- Verifica membresía (caché 1h, limpieza periódica JobQueue)
- Aplica límites y cooldowns
- Genera cartas/runas/hexagramas con `SystemRandom` (sin repetición)
- Compone imágenes (Pillow → JPEG, LRU cache, file handles cerrados, fuente para etiquetas, **BytesIO cerrado tras envío**)
- **Envío ordenado:** await send_photo → texto como reply a la foto → feedback
- Caption descriptivo en imágenes
- Si composición falla: degradación a texto descriptivo
- Detecta respuestas truncadas y vacías, cierra gracefully
- Escapa HTML entities, aplica marcadores custom `[[T]]` `[[C]]` (no ## ni **)
- Feedback: expiración 7d, anti-ajeno, anti-doble, tolerante a mensajes borrados
- Typing indicator renovado cada 4s
- **Timeout global del flujo:** 45s, no solo timeout de API
- Maneja Telegram 429 (RetryAfter), Forbidden (bot removido), BadRequest (permisos)
- Errores de pydantic traducidos a mensajes amigables, nunca técnicos
- Tareas programadas via JobQueue
- **PicklePersistence** para estado ConversationHandlers entre restarts (+ fallback SQLite)
- Ignora: ediciones, fotos, stickers, forwards, audio

### Capa 2: SERVICIO DE INTERPRETACIÓN (API + IA)

- **AsyncAnthropic singleton** (no síncrono — síncrono bloquea el event loop 10-15s por llamada)
- System prompt siempre idéntico (se cachea, **≥1024 tokens** mínimo para que caching se active)
- **API version pinned** (anthropic-version header)
- max_tokens configurable desde .env
- Parseo seguro de respuesta (IndexError/AttributeError protegido)
- Detecta respuestas vacías (200 OK pero texto en blanco)
- Devuelve texto plano + stop_reason + coste real
- Signo solar con efemérides (no tabla fija), mediodía como approx sin hora
- Timezone hora local → UTC
- Placidus fallback Whole Sign si |lat| > 60°
- Numerología: normalización Unicode, nombre completo pedido solo al usar /numerologia
- **Escrituras en SQLite dentro de transacciones** (usage_log + last_activity atómicos)

### Comunicación

```python
class InterpretationRequest(BaseModel):
    mode: str
    variant: str
    drawn_items: list[DrawnItem]
    question: str | None
    user_profile: UserProfile

    @classmethod
    def build(cls, **data) -> "InterpretationRequest":
        return cls.model_validate(data)

class InterpretationResponse(BaseModel):
    text: str              # Texto plano
    tokens_input: int      # Real de usage API
    tokens_output: int
    cost_usd: float
    cached: bool
    truncated: bool        # stop_reason == "max_tokens"
    error: str | None      # "empty_response", "api_format_error", "timeout", None
```

### Bloqueo de peticiones concurrentes por usuario

```python
_active_requests: set[int] = set()

async def handler(update, context):
    user_id = update.effective_user.id
    if user_id in _active_requests:
        await update.message.reply_text(
            "Tu consulta anterior aún está en proceso. Espera un momento.",
            reply_to_message_id=update.message.message_id
        )
        return
    _active_requests.add(user_id)
    try:
        # ... flujo completo
    finally:
        _active_requests.discard(user_id)
```

---

## 4. Seguridad y Restricciones

### 4.1 Triple barrera (BotFather + chat_id + anti-DM)

### 4.2 Membresía — Caché 1h + limpieza periódica JobQueue

### 4.3 Middleware completo

Incluye: edits, no-texto, DM, /start, chat_id, topics, membresía, username update.

Detección de bot removido o sin permisos:
```python
from telegram.error import Forbidden, BadRequest

try:
    await bot.send_message(chat_id, text)
except Forbidden:
    logger.error("Bot removed or blocked!")
    # Alerta throttled al admin
except BadRequest as e:
    if "not enough rights" in str(e):
        logger.error(f"Missing permissions: {e}")
```

### 4.3.1 CRÍTICO: Migración grupo → supergrupo

Cuando un admin activa features avanzadas (topics, permisos granulares), Telegram migra el grupo a supergrupo y **el chat_id cambia**. El bot deja de funcionar silenciosamente — el filtro hardcodeado rechaza todos los mensajes sin ningún error visible.

```python
async def handle_migration(update: Update, context):
    old_id = update.message.migrate_from_chat_id
    new_id = update.effective_chat.id
    logger.critical(f"Group migrated! Old: {old_id} → New: {new_id}")
    await send_alert(context.bot, "migration",
        f"🚨 El grupo migró de ID.\n"
        f"Viejo: {old_id}\nNuevo: {new_id}\n"
        f"Actualizar ALLOWED_CHAT_ID en .env y reiniciar."
    )

# Registrar handler
app.add_handler(MessageHandler(filters.StatusUpdate.MIGRATE, handle_migration))
```

Sin este handler, el bot muere silenciosamente y nadie sabe por qué. La alerta debe ser de máxima prioridad (sin throttle).

### 4.4 Sanitización

200 chars, strip control, XML delimiters, pydantic validation con **try/except que traduce errores técnicos a mensajes amigables:**

```python
try:
    birth_date = parse_and_validate_date(user_input)
except (ValueError, ValidationError):
    await update.message.reply_text(
        "Esa fecha no parece válida. Usa el formato DD/MM/AAAA."
    )
    return
```

Nunca mostrar al usuario: `ValueError: day is out of range for month`.

### 4.5 Anti-abuse

Límites, cooldown, flood. **Filtro antigüedad cuenta eliminado** (Telegram no expone fecha creación).

### 4.6 Spending limit Anthropic: $25/mes

### 4.7 Permisos del bot en el grupo

| Permiso | Necesario | Por qué |
|---|---|---|
| Send Messages | Sí | Responder |
| Send Photos | Sí | Imágenes tiradas |
| Read Messages | Sí | Recibir comandos |

**No necesita:** admin, ban, pin, delete, invite.

Documentar para el admin del grupo.

### 4.8 Rotación de token

Si el token se filtra:
1. `/revoke` en BotFather → nuevo token
2. Actualizar `.env`
3. `systemctl restart bot-taberna`

Asegurar que el token NUNCA aparezca en logs. No loguear `Settings` completo.

---

## 5. Prompt Caching + API Client

System siempre idéntico → máximo cache hit. Sub-prompts en user message.

### CRÍTICO: Mínimo 1024 tokens para caching

Anthropic requiere que el bloque cacheado tenga **≥1024 tokens** para que el caching se active. Si el system prompt queda por debajo, `cache_control` se ignora silenciosamente y **todas las estimaciones de coste son incorrectas** (pagas $3.00/1M en cada llamada en vez de $0.30/1M).

El system prompt debe llegar a ≥1024 tokens. No rellenar con basura — añadir instrucciones detalladas que mejoren la calidad: reglas de interpretación, tono, ejemplos de formato, disclaimers, personalidad rica. **Verificar el conteo de tokens antes de lanzar.**

### AsyncAnthropic singleton

**NUNCA usar el cliente síncrono.** `anthropic.Anthropic()` bloquea el event loop 10-15 segundos por llamada. El typing indicator, otros handlers y la cola se congelan. Usar `AsyncAnthropic`:

```python
class AnthropicService:
    """Singleton. Se crea una vez, se reutiliza en todas las llamadas."""

    def __init__(self, settings: Settings):
        self._client = anthropic.AsyncAnthropic(
            api_key=settings.ANTHROPIC_API_KEY,
            default_headers={"anthropic-version": settings.ANTHROPIC_API_VERSION},
            max_retries=2,   # SDK maneja retries (429, 500). NO añadir retries manuales.
            timeout=30.0,
        )
```

**CRÍTICO — NO hacer double retry:** El SDK ya reintenta automáticamente (2 veces para 429 y 500). Si además añadimos retries manuales en nuestro código, el resultado es SDK retries × nuestros retries = hasta 9 intentos. Puede convertir un 429 temporal en un ban por bombardear la API. **Confiar en los retries del SDK. No añadir propios.**

```python
    async def interpret(self, request: InterpretationRequest) -> InterpretationResponse:
        try:
            response = await self._client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=request.max_tokens,
                system=[{
                    "type": "text",
                    "text": MASTER_SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"}
                }],
                messages=[{
                    "role": "user",
                    "content": build_user_message(request)
                }]
            )
        except anthropic.APITimeoutError:
            return InterpretationResponse(error="timeout", ...)
        except anthropic.RateLimitError:
            return InterpretationResponse(error="rate_limit", ...)
        except anthropic.APIError as e:
            logger.error(f"API error: {e}")
            return InterpretationResponse(error="api_error", ...)

        # Parseo seguro — formato de respuesta puede cambiar
        try:
            text = response.content[0].text
            stop = response.stop_reason
            tokens_in = response.usage.input_tokens
            tokens_out = response.usage.output_tokens
        except (IndexError, AttributeError) as e:
            logger.error(f"Unexpected response format: {e}")
            return InterpretationResponse(error="api_format_error", ...)

        if not text or text.strip() == "":
            logger.error(f"Empty response: {request.mode}/{request.variant}")
            return InterpretationResponse(error="empty_response", ...)

        return InterpretationResponse(
            text=text,
            tokens_input=tokens_in,
            tokens_output=tokens_out,
            cost_usd=calculate_real_cost(response.usage),
            cached=(response.usage.cache_read_input_tokens or 0) > 0,
            truncated=(stop == "max_tokens"),
            error=None
        )
```

### Fórmula de coste real — Tokens cacheados vs frescos tienen precios diferentes

La API devuelve `cache_read_input_tokens` y `cache_creation_input_tokens` separados. Sin esta fórmula, /stats sobreestima costes:

```python
def calculate_real_cost(usage) -> float:
    """Coste real basado en desglose de tokens cache hit/miss/write."""
    fresh_input = usage.input_tokens - (usage.cache_read_input_tokens or 0)
    cached_input = usage.cache_read_input_tokens or 0
    cache_write = usage.cache_creation_input_tokens or 0

    cost = (
        (fresh_input / 1_000_000) * 3.00 +      # Input no cacheado
        (cached_input / 1_000_000) * 0.30 +       # Cache read
        (cache_write / 1_000_000) * 3.75 +         # Cache write
        (usage.output_tokens / 1_000_000) * 15.00  # Output
    )
    return round(cost, 6)
```

**No crear un cliente por llamada** — abre y cierra conexiones HTTP innecesariamente.

---

## 6. Contexto del Usuario

Perfil inyectado. ~15-40 tokens. Enriquecimiento progresivo. Coste despreciable.

---

## 7. Modos y Funcionalidades

### 7.1-7.8 (Tarot, Runas, I Ching, Geomancia, Numerología, Natales, Oráculo)

Todo igual que documento anterior, con estas adiciones:

**Tarot — Sin repetición explícita:**
```python
_rng = random.SystemRandom()

def draw_cards(n: int, deck_size: int = 78) -> list[int]:
    return _rng.sample(range(deck_size), n)
```

**I Ching — Sin mutables = sin derivado:**
Si ninguna línea es mutable (todas yang joven o yin joven), no hay hexagrama derivado.
- Renderer: imagen de 1 hexagrama (no 2 con flecha)
- Sub-prompt: instrucciones para ambos escenarios (con y sin transformación)

**Numerología — Nombre completo pedido aparte:**
El onboarding pide alias. Para numerología se necesita nombre completo de nacimiento.
Se pide solo cuando el usuario usa /numerologia por primera vez si `full_birth_name` es NULL.
Se guarda en perfil para futuras lecturas.

Añadir al schema de users:
```sql
full_birth_name TEXT,  -- Solo para numerología, pedido aparte
```

**Compatibilidad:** solo camino de vida (no pide nombre de la otra persona, solo fecha).

**Geomancia escudo — Validación matemática estricta:**
Tests unitarios con al menos 3 escudos calculados a mano: 4 madres input → escudo completo verificado fila por fila.

### 7.9 max_tokens configurables en .env

Si un modo se trunca >30%/día → ajustar sin redeploy.

### 7.10 /bibliomancia — Fragmentos de textos sagrados (€0 API)

Código existente migrado desde `/opt/evangelio/` (evangeliobot.py + datos.py ~6MB).

**Dos vías de acceso (patrón browse + directo):**
- `/bibliomancia` → Grid de botones inline: `[Biblia] [Corán] [Gita] [Evangelio de Tomás]`
- `/bibliomancia biblia` → Fragmento aleatorio directo
- `/bibliomancia coran` → Fragmento aleatorio directo
- `/bibliomancia gita` → Fragmento aleatorio directo
- `/bibliomancia evangelio` → Fragmento aleatorio directo

**Implementación:**
- Datos cargados en memoria desde `datos.py` al arrancar (CORAN, EVANGELIO, BIBLIA, GITA)
- `SystemRandom` para selección (consistente con el resto del bot)
- Anti-repetición: no repetir último fragmento (ya implementado en evangeliobot.py)
- Mensajes >4096 chars: split con `textwrap.wrap` (ya implementado)
- NO consume API de Anthropic — respuesta directa sin interpretación
- Tono del bot no aplica aquí — el texto sagrado se devuelve tal cual

**Migración:** Mover `datos.py` a `data/bibliomancia_datos.py`. Adaptar import path. Eliminar bot standalone.

### 7.11 /admins — Directorio de guardianes de la taberna (€0 API)

20 admins con sus bios. Dos vías de acceso:

- `/admins` → Grid de botones inline (2 columnas):
  ```
  [Tam ☥∆Ωπ]     [Void]
  [Wolf]          [Desco]
  [Null]          [SenderoSolar]
  [Deva]          [Zarandonga]
  [Vernalles]     [John]
  [Noodless]      [Lucia]
  [Nick-G 𒀭]     [Babalon]
  [Frater Lead]   [Ink 𒀭]
  [LilaAzul]      [Yhennefer]
  ```
- `/admins @void` o `/admins void` → Bio directa + **mención por user_id** (notifica al admin)
- Si no matchea: "No conozco a ese guardián."
- Botón `[← Volver]` tras ver una bio → vuelve al grid
- Un solo mensaje que se edita (zero spam)

**Mención por user_id (no por username):** Los usernames cambian, los IDs no. La mención se hace con HTML:
```html
<a href="tg://user?id=123456789">Void</a>
```
Esto genera notificación al admin aunque cambie de username.

**Datos PRIVADOS — IDs fuera del repo:**
- `admins_private.json` → Archivo real con IDs + bios. **En `.gitignore`.**
- `admins_private.example.json` → En el repo, con datos fake para que se sepa el formato.

```json
// admins_private.example.json (en repo)
[
  {
    "key": "tam",
    "telegram_user_id": 000000000,
    "display_name": "Tam ☥∆Ωπ",
    "username": "Tam170717",
    "bio": "Bio del admin aquí..."
  }
]

// admins_private.json (en .gitignore, NUNCA en repo)
[
  {
    "key": "tam",
    "telegram_user_id": 915056450,
    "display_name": "Tam ☥∆Ωπ",
    "username": "Tam170717",
    "bio": "Iniciada practicante en Magia Hermética & Rosacruz..."
  }
]
```

**Auto-captura fallback:** Si un admin no tiene `telegram_user_id` en el JSON (valor 0 o null), cuando escriba en el grupo el bot captura su user_id por username match y lo loguea. El admin del bot puede actualizarlo manualmente en el JSON.

**NO consume API de Anthropic.**

### 7.12 /start — Presentación in-character (€0 API)

- **En grupo:** El Pezuñento se presenta brevemente. Si el usuario ya está registrado → "Usa /consulta".
- **En DM:** Mismo texto + "Solo funciono en La Taberna."
- Texto estático, tono Baphomet, breve.
- NO consume API de Anthropic.

---

## 8. Assets de Imágenes

### 8.1 Resumen

| Sistema | En disco | Espacio |
|---|---|---|
| Tarot PNGs | 78 | ~15-25 MB |
| Texturas | 2-3 | ~1-2 MB |
| **Fuente etiquetas (NotoSans-Regular)** | 1 | ~500 KB |
| Runas | 0 (trazos Pillow) | 0 |

**Fuente para etiquetas:** Las composiciones necesitan texto ("Pasado", "Presente", "Futuro"). `ImageFont.load_default()` es minúscula e ilegible. Empaquetar una fuente legible:

```
assets/fonts/
└── NotoSans-Regular.ttf         # Etiquetas en composiciones
```

O una fuente temática (serif medieval libre de derechos) para coherencia visual.

### 8.2-8.5 (Invertidas, LRU cache, JPEG resolución alta, captions)

Todo igual, con aclaración sobre file handles y EXIF:
```python
from functools import lru_cache
from PIL import Image, ImageOps

@lru_cache(maxsize=78)
def load_card_image(card_id: str) -> Image.Image:
    with Image.open(f"assets/tarot/{card_id}.png") as img:
        img = ImageOps.exif_transpose(img)  # Normalizar EXIF antes de cachear
        return img.copy()  # with cierra el handle, copy mantiene datos en RAM
```

**EXIF obligatorio:** Algunos PNGs de Rider-Waite descargados de GitHub tienen metadata EXIF con orientación. Sin `exif_transpose()`, una carta "normal" puede verse invertida y `rotate(180)` la pone bien — o al revés. `exif_transpose()` aplica la rotación EXIF a los píxeles y limpia la metadata. Así `rotate(180)` siempre funciona como se espera.

**Concurrencia:** `lru_cache` es seguro en asyncio single-thread. No usar `run_in_executor` para Pillow.

**Composición → JPEG con verificación de tamaño (Telegram limita 10MB):**

```python
from io import BytesIO

def compose_to_jpeg(composition: Image, quality: int = 85) -> BytesIO:
    buffer = BytesIO()
    composition.convert("RGB").save(buffer, format="JPEG", quality=quality)

    # Telegram rechaza fotos >10MB
    size_mb = buffer.getbuffer().nbytes / (1024 * 1024)
    if size_mb > 9.5:
        logger.warning(f"Image too large: {size_mb:.1f}MB, reducing quality")
        buffer = BytesIO()
        composition.convert("RGB").save(buffer, format="JPEG", quality=70)

    buffer.seek(0)
    return buffer
```

**BytesIO cleanup** — cerrar tras envío para no acumular buffers:

```python
jpeg_buffer = compose_to_jpeg(composition)
try:
    await bot.send_photo(chat_id, photo=jpeg_buffer, caption=caption, ...)
finally:
    jpeg_buffer.close()
```

Testear tamaño de Cruz Celta (10 cartas a resolución alta) antes de lanzar.

### 8.6 Cruz Celta: carta 2 rotación + escala

Disposición Waite. Carta 2 rotada 90°, redimensionada para caber sobre carta 1:

```python
card2_rotated = card2.rotate(90, expand=True)
scale = card1.width / card2_rotated.width
card2_final = card2_rotated.resize(
    (int(card2_rotated.width * scale), int(card2_rotated.height * scale))
)
```

### 8.7 Degradación si composición falla

Si Pillow falla (PNG corrupto, memoria): texto descriptivo + continuar interpretación normalmente.

### 8.8 Runas: trazos vectoriales con Pillow (sin fuentes, sin Unicode, sin assets)

Cada runa del Elder Futhark se define como lista de segmentos de línea en coordenadas normalizadas (0-1). Se renderiza con Pillow sobre textura piedra.

```python
RUNE_PATHS = {
    "fehu": [
        ((0.5, 0.0), (0.5, 1.0)),    # Vertical
        ((0.5, 0.15), (0.85, 0.35)),  # Diagonal superior
        ((0.5, 0.40), (0.85, 0.55)),  # Diagonal inferior
    ],
    "uruz": [
        ((0.25, 0.0), (0.25, 1.0)),
        ((0.25, 1.0), (0.75, 0.6)),
        ((0.75, 0.6), (0.75, 0.0)),
    ],
    # ... 24 runas + Wyrd (círculo vacío)
}

def render_rune(rune_id: str, size: int = 300) -> Image.Image:
    img = stone_texture.copy().resize((size, size))
    draw = ImageDraw.Draw(img)
    paths = RUNE_PATHS[rune_id]
    for (x1, y1), (x2, y2) in paths:
        # Sombra (efecto tallado)
        draw.line([(x1*size+2, y1*size+2), (x2*size+2, y2*size+2)],
                  fill=(40, 40, 40), width=8)
        # Trazo principal
        draw.line([(x1*size, y1*size), (x2*size, y2*size)],
                  fill=(220, 200, 160), width=6)
    return img
```

**Ventajas sobre Unicode/fuentes:**
- Estilo visual único — ningún otro bot tiene las mismas runas
- Efecto tallado en piedra (sombra desplazada = profundidad)
- Zero dependencias de fuentes, zero problemas de rendering
- Ajustable: grosor, color, textura, tamaño sin cambiar assets
- AGPL-compatible: 100% código propio

**Esfuerzo:** 24 definiciones de coordenadas + Wyrd (~2h). Renderer ~50 líneas. Claude Code genera ambos.

### 8.9 Nombres cartas español — RESUELTO

Nomenclatura definida por Tam (admin del grupo):
- **El Hierofante** (no Sumo Sacerdote)
- **Bastos** (no Varas)
- **Sota** (no Paje)
- **Caballero** (no Caballo)

Oros, Copas y Espadas no tienen variante. Aplicar consistentemente en `tarot_cards.json`, sub-prompts y respuestas de Sonnet.

---

## 9. Sistema de Usuarios

### 9.1 Onboarding (timeout 5 min)

### CRÍTICO: ForceReply en TODOS los pasos que esperan texto libre

Por defecto, los bots de Telegram tienen **privacy mode ON**. En un grupo, el bot solo ve: comandos (/xxx), replies directos al bot, y @menciones. Si el bot pregunta "¿Cuándo naciste?" y el usuario escribe "15/06/1993" como mensaje nuevo (no como reply), **el bot no lo recibe**. El ConversationHandler muere silenciosamente.

**Solución:** Usar `ForceReply(selective=True)` en cada mensaje que espera texto libre del usuario:

```python
from telegram import ForceReply

await update.message.reply_text(
    "¿Cuándo naciste? (DD/MM/AAAA)",
    reply_markup=ForceReply(selective=True)
)
```

`ForceReply(selective=True)` hace que Telegram muestre automáticamente la interfaz de reply al usuario específico. Su respuesta es un reply directo al bot → el bot la recibe con privacy mode ON.

**Afecta a TODOS los ConversationHandlers:**
- Onboarding: alias, fecha, hora, ciudad
- Flujo de pregunta: "¿Tienes alguna pregunta para las cartas?"
- Compatibilidad numerológica: segunda fecha
- Actualización de perfil: hora, ciudad
- Numerología primera vez: nombre completo

**Sin ForceReply, el bot funciona en testing (DM o grupo con privacy off) y falla completamente en producción.** Esta es la causa #1 de bots de Telegram que "no funcionan en grupos" y nadie sabe por qué.

**NO desactivar privacy mode** (`/setprivacy` → Disable) como alternativa — haría que el bot reciba TODOS los mensajes de 2,600 miembros, desperdiciando recursos.

Onboarding simultáneo de dos usuarios funciona correctamente (`per_user=True` es default). No requiere manejo especial.

### 9.2 Onboarding incompleto: retomar desde SQLite (funciona post-restart)

### 9.3 Perfil (SQLite)

```sql
CREATE TABLE users (
    telegram_user_id    INTEGER PRIMARY KEY,
    telegram_username   TEXT,
    alias               TEXT NOT NULL,
    full_birth_name     TEXT,                   -- Solo numerología, pedido aparte
    birth_date          TEXT NOT NULL,
    birth_time          TEXT,
    birth_city          TEXT,
    birth_lat           REAL,
    birth_lon           REAL,
    birth_timezone      TEXT,
    sun_sign            TEXT,
    moon_sign           TEXT,
    ascendant           TEXT,
    lunar_nakshatra     TEXT,
    life_path           INTEGER,
    registered_at       TEXT NOT NULL,
    last_activity       TEXT,
    onboarding_complete BOOLEAN DEFAULT FALSE
);
```

### 9.4 Comandos perfil (/miperfil, /actualizarperfil, /borrarme)

### 9.5 Username actualizado en middleware

### 9.6 Privacidad

Token nunca en logs. Settings completo nunca logueado.

### 9.7 Signo solar con efemérides (no tabla fija)

Limitación documentada: para nacimientos pre-1900 (fecha mínima), zonas horarias históricas dependen de la base de datos IANA, que es buena pero no perfecta para todos los países en 1900-1970.

---

## 10. Límites y Control de Uso

### 10.1 Límites (5 tiradas pool, 2 numerología, 1 natal, 3 oráculo, 60s cooldown, 200 chars)

### 10.2 Mensajes in-character (tono Baphomet)

```python
LIMIT_MESSAGES = {
    "daily_limit": "Ya has quemado tus tiradas de hoy. Vuelve mañana, que las cartas también descansan.",
    "cooldown": "Tranquilo, que las runas no se van a ir a ningún sitio. Espera un poco.",
    "empty_response": "Las cartas no tienen nada que decirte ahora. Será que no es el momento.",
    "queue_timeout": "Hay cola en el oráculo. Inténtalo en un momento.",
    "request_in_progress": "Aún estoy con tu consulta anterior. Paciencia.",
    "truncated": "\n\n...El oráculo ha dicho lo que tenía que decir.",
    "not_registered": "No te conozco. Usa /consulta para presentarte primero.",
    "off_topic": "Eso pregúntaselo a Google. Yo leo las cartas, no hago recados.",
    "admin_only": "Este comando es solo para el guardián de la taberna.",
    "nominatim_down": "No puedo verificar esa ciudad ahora. Inténtalo en un rato o usa /cancelaroraculo.",
}
```

---

## 11. Interacción y Comandos

### 11.1 /setcommands en BotFather

### 11.2 /start (DM → informativo, grupo → /consulta)

### 11.3 Callback data ≤ 64 bytes

```python
CALLBACKS = {
    "t:1": ("tarot", "1_carta"),
    "t:3": ("tarot", "3_cartas"),
    "t:cc": ("tarot", "cruz_celta"),
    "r:1": ("runas", "odin"),
    "r:3": ("runas", "nornas"),
    "r:cr": ("runas", "cruz"),
    "ic": ("iching", "hexagrama"),
    "g:1": ("geomancia", "1_figura"),
    "g:e": ("geomancia", "escudo"),
    "n:i": ("numerologia", "informe"),
    "n:c": ("numerologia", "compatibilidad"),
    "nt": ("natal", "tropical"),
    "nv": ("natal", "vedica"),
    "or": ("oraculo", "libre"),
    "q:y": ("question", "yes"),
    "q:n": ("question", "no"),
    # Bibliomancia
    "bl:bi": ("bibliomancia", "biblia"),
    "bl:co": ("bibliomancia", "coran"),
    "bl:gi": ("bibliomancia", "gita"),
    "bl:ev": ("bibliomancia", "evangelio"),
    # Admins (a:0 a a:19 — índice del admin)
    "a:0": ("admins", "tam"),
    # ... a:1 a a:19
    "a:bk": ("admins", "back"),  # Volver al grid
}
```

### 11.4 /ayuda contenido definido

```
🔮 Modos disponibles:

🃏 /tarot — Consulta las cartas del Tarot
   Una carta (Sí/No) · Tres cartas · Cruz Celta

ᚱ /runa — Consulta las runas del Elder Futhark
   Runa de Odin · Tres Nornas · Cruz Rúnica

☯ /iching — Consulta el I Ching
   Hexagrama con líneas mutables

⊕ /geomancia — Consulta las figuras geománticas
   Una figura · Escudo completo

🔢 /numerologia — Tu mapa numerológico
   Informe completo · Compatibilidad

🪐 /natal — Carta natal tropical
🕉 /vedica — Carta natal védica (Jyotish)
🔮 /oraculo — Pregunta libre al oráculo

📖 /bibliomancia — Fragmento de texto sagrado
   Biblia · Corán · Gita · Evangelio de Tomás

🛡 /admins — Guardianes de la taberna

🆕 /consulta — Registrarte para empezar
📋 /miperfil · ✏️ /actualizarperfil · 🗑 /borrarme
❌ /cancelaroraculo — Cancelar operación en curso
❓ /ayudaoraculo — Este mensaje

Tienes 5 tiradas diarias + 3 consultas al oráculo.
```

### 11.5 Flujo completo: orden garantizado + timeout global

```
 1. Verificar no hay petición en curso para este usuario
 2. Comando/botón → sub-menú → pregunta
 3. Typing indicator (renovado 4s)
 4. Genera cartas SystemRandom.sample
 5. Compone imagen Pillow → JPEG (degradación si falla)
 6. await send_photo con caption, REPLY al original
 7. Lee perfil SQLite
 8. InterpretationRequest → Capa 2

    ── TIMEOUT GLOBAL 45s para todo el flujo desde aquí ──

 9. Capa 2: system (cacheado) + user + max_tokens
10. API Anthropic (version pinned, parseo seguro)
11. InterpretationResponse (texto plano + stop_reason + coste real)
12. Si error (vacío, timeout, format): mensaje amigable
13. Si truncated: cierre graceful
14. HTML escape + formateo
15. Send texto REPLY A LA FOTO
16. Send feedback (inline keyboard)
17. Registra usage_log (drawn_data JSON + truncated)
18. Actualiza last_activity
19. Liberar bloqueo de petición concurrente
```

**Timeout global:**
```python
try:
    response = await asyncio.wait_for(
        request_queue.process(request),
        timeout=45
    )
except asyncio.TimeoutError:
    await message.reply_text(LIMIT_MESSAGES["queue_timeout"], ...)
    return
```

### 11.6 Typing renovado 4s — Con error handling

```python
async def keep_typing(chat_id, bot):
    while True:
        try:
            await bot.send_chat_action(chat_id, "typing")
        except (Forbidden, BadRequest, RetryAfter):
            return  # Bot removido o sin permisos, dejar de intentar
        await asyncio.sleep(4)

async def send_with_typing(chat_id, bot, coro):
    typing_task = asyncio.create_task(keep_typing(chat_id, bot))
    try:
        result = await coro
    finally:
        typing_task.cancel()
    return result
```

Sin error handling, si el bot pierde permisos mientras espera respuesta de Sonnet, la task de typing lanza excepciones silenciosas o cancela el flujo.

### 11.7 Truncamiento + respuesta vacía

```python
if response.error == "empty_response":
    await send_reply(LIMIT_MESSAGES["empty_response"])
    return
if response.truncated:
    text += LIMIT_MESSAGES["truncated"]
```

### 11.8 Formateo: marcadores custom (no ## ni **)

`##` y `**` son frágiles — Sonnet los usa inconsistentemente, pueden conflictuar con HTML escape. Usar marcadores custom no ambiguos:

```
# En el system prompt:
"Usa [[T]] para títulos de sección y [[C]] para nombres de cartas/runas/figuras."

# Sonnet produce:
"[[T]]El Pasado[[/T]]\nLa carta [[C]]El Loco[[/C]] invertida indica..."
```

```python
import html

def format_response(raw_text: str) -> str:
    safe = html.escape(raw_text)  # Primero escapar & < >
    safe = safe.replace("[[T]]", "<b>").replace("[[/T]]", "</b>")
    safe = safe.replace("[[C]]", "<i>").replace("[[/C]]", "</i>")
    return safe
```

`[[T]]` nunca aparece naturalmente en texto → parsing determinista. Con `##` y `**` no hay esa garantía.

### 11.9 ConversationHandler: PicklePersistence + corrupción + fallback

python-telegram-bot tiene `PicklePersistence` built-in:

```python
import pickle
from pathlib import Path

# Startup con protección contra pickle corrupto
try:
    persistence = PicklePersistence(
        filepath="bot_persistence.pickle",
        update_interval=60,  # Escribir cada 60s, no en cada update (reduce riesgo corrupción)
    )
except (pickle.UnpicklingError, EOFError, FileNotFoundError, Exception):
    logger.warning("Persistence corrupted or missing, starting fresh")
    Path("bot_persistence.pickle").unlink(missing_ok=True)
    persistence = PicklePersistence(
        filepath="bot_persistence.pickle",
        update_interval=60,
    )

app = ApplicationBuilder().token(TOKEN).persistence(persistence).build()
```

**`update_interval=60`:** Reduce frecuencia de escritura a disco. Si el bot crashea entre escrituras, se pierde máximo 60s de estado, pero el pickle no se corrompe por escritura interrumpida.

**Fallback SQLite:** Si el pickle se corrompe al arrancar, se borra y empieza fresco. Los datos parciales de onboarding en SQLite permiten retomar sin repetir pasos.

Añadir `bot_persistence.pickle` a `.gitignore` y al backup.

### 11.10 /cancelaroraculo, timeout 5 min

### 11.11 Feedback: expiración 7d + tolerancia a mensajes borrados

```python
async def handle_feedback(update, context):
    query = update.callback_query
    _, sentiment, usage_id_str = query.data.split(":")
    usage_id = int(usage_id_str)

    # Verificar existencia
    usage = await db.get_usage(usage_id)
    if not usage:
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except BadRequest:
            pass  # Mensaje ya borrado por admin
        await query.answer("Esta lectura ya no existe.", show_alert=False)
        return

    # Solo dueño
    if query.from_user.id != usage.user_id:
        await query.answer("Este feedback no es tuyo.", show_alert=False)
        return

    # Expiración 7 días
    age = datetime.utcnow() - datetime.fromisoformat(usage.timestamp)
    if age.days > 7:
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except BadRequest:
            pass
        await query.answer("Feedback expirado.", show_alert=False)
        return

    # No doble
    existing = await db.get_feedback(usage_id)
    if existing:
        await query.answer("Ya diste tu opinión.", show_alert=False)
        return

    # Guardar y limpiar
    await db.save_feedback(usage_id, query.from_user.id, positive=(sentiment == "p"))
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except BadRequest:
        pass  # Tolerante a mensaje borrado
    await query.answer("Gracias ✨")
```

### 11.12 Telegram flood control (RetryAfter + Forbidden + BadRequest)

### 11.13 Webhook vs Long Polling → Long polling dev, webhook producción

### 11.14 Geocoding: ciudades homónimas

Si Nominatim devuelve una ciudad y el usuario dice "No, otra", pedir que sea más específico:

```
Bot: "¿Te refieres a Santiago del Estero, Argentina?"
→ [Sí] [No, otra ciudad]

Si "No":
Bot: "Escríbelo más completo, por ejemplo: Santiago de Chile, Santiago de Compostela."
→ Usuario reescribe con más detalle
```

### 11.15 Geocoding: Nominatim caído durante onboarding

Si Nominatim está completamente caído (no solo rate limit), el usuario queda atrapado en "¿En qué ciudad naciste?" sin poder avanzar.

```python
try:
    result = await geocode_city(city_input)
except Exception:
    result = None

if result is None:
    await update.message.reply_text(
        "No puedo verificar esa ciudad ahora. Puedes:\n"
        "• Intentarlo de nuevo en unos minutos\n"
        "• Usar /cancelaroraculo y completar después con /actualizarperfil"
    )
    return  # Se queda en el mismo paso, puede reintentar o cancelar
```

El usuario siempre tiene una salida.

### 11.16 /stats puede crecer: limitado a top 5

Output de /stats siempre limitado (top 5 usuarios, no variable). Si aún supera 4096 chars, splitear.

---

## 12. Infraestructura y Admin

### 12.1 Entornos dev/prod

```python
class Settings(BaseSettings):
    ENV: str = "dev"
    BOT_TOKEN: str
    ANTHROPIC_API_KEY: str
    ANTHROPIC_API_VERSION: str = "2024-10-22"
    ALLOWED_CHAT_ID: int
    ALLOWED_THREAD_ID: int | None = None
    ADMIN_USER_ID: int
    BOT_VERSION: str = "1.0.0"
    MONTHLY_SPENDING_LIMIT: float = 25.0
    DAILY_ALERT_THRESHOLD: float = 5.0
    QUEUE_TIMEOUT: float = 45.0
    FEEDBACK_EXPIRY_DAYS: int = 7
    # max_tokens (todos configurables)
    # ...
```

### 12.2 SQLite: lifecycle + WAL + transacciones

```python
class Database:
    _instance: aiosqlite.Connection | None = None

    @classmethod
    async def get(cls) -> aiosqlite.Connection:
        if cls._instance is None:
            cls._instance = await aiosqlite.connect("bot-taberna.db")
            await cls._instance.execute("PRAGMA journal_mode=WAL")
            await cls._instance.execute("PRAGMA busy_timeout=5000")
            await cls._instance.execute("PRAGMA foreign_keys=ON")
            await cls._init_tables(cls._instance)
            await cls._apply_migrations(cls._instance)
        return cls._instance

    @classmethod
    async def close(cls):
        if cls._instance:
            await cls._instance.close()
            cls._instance = None
```

**WAL archivos auxiliares:** WAL mode crea `bot-taberna.db-wal` y `bot-taberna.db-shm`. Si `botuser` no tiene permiso de escritura en el **directorio** (no solo el .db), WAL falla silenciosamente y vuelve a DELETE mode (que bloquea). Asegurar: `chown -R botuser:botuser /path/bot-taberna/`.

**Transacciones:** Múltiples escrituras (usage_log + last_activity) deben ser atómicas:

```python
async def record_usage(db, user_id, mode, variant, ...):
    async with db.execute("BEGIN"):
        await db.execute("INSERT INTO usage_log (...) VALUES (...)", (...))
        await db.execute("UPDATE users SET last_activity = ? WHERE telegram_user_id = ?", (now, user_id))
        await db.commit()
```

Si el bot crashea entre las dos escrituras, la DB queda inconsistente sin transacción.

**VACUUM periódico:** Añadir al mantenimiento mensual (no mientras hay escrituras activas):

```bash
# En cron mensual o system-maintenance.sh, en horas muertas
sqlite3 /path/bot-taberna.db "VACUUM;"
```

### 12.3 Migraciones SQL (schema_version + carpeta migrations/)

### 12.4 Tracking de uso

```sql
CREATE TABLE usage_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    mode            TEXT NOT NULL,
    variant         TEXT,
    tokens_input    INTEGER NOT NULL,
    tokens_output   INTEGER NOT NULL,
    cost_usd        REAL NOT NULL,
    cached          BOOLEAN NOT NULL,
    truncated       BOOLEAN NOT NULL DEFAULT FALSE,
    drawn_data      TEXT,
    timestamp       TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(telegram_user_id) ON DELETE CASCADE
);

CREATE TABLE feedback (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    usage_id    INTEGER NOT NULL UNIQUE,
    positive    BOOLEAN NOT NULL,
    timestamp   TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(telegram_user_id) ON DELETE CASCADE,
    FOREIGN KEY (usage_id) REFERENCES usage_log(id) ON DELETE CASCADE
);
```

### 12.5 drawn_data JSON schema

```python
# Tarot
{"cards": [
    {"id": "major_00", "name": "El Loco", "inverted": true, "position": "pasado"},
]}
# Runas
{"runes": [
    {"id": "fehu", "name": "Fehu", "inverted": false, "position": "pasado"},
]}
# I Ching
{"hexagram": {
    "lines": [9, 8, 7, 7, 6, 8],
    "primary": 23, "primary_name": "Po",
    "derived": 2, "derived_name": "Kun",  # null si sin mutables
    "mutable_lines": [1, 5]               # [] si sin mutables
}}
# Geomancia
{"figures": [
    {"name": "Amissio", "points": [1, 2, 1, 2], "position": "madre_1"},
]}
# Numerología
{"life_path": 7, "expression": 3, "soul": 9,
 "personal_year": 5, "personal_month": 8}
# Numerología compatibilidad
{"life_path_1": 7, "life_path_2": 3}
# Natal tropical (datos calculados, útiles para debug)
{"sun": "Gemini", "moon": "Pisces", "asc": "Virgo",
 "planets_calculated": 11, "aspects_found": 14}
# Natal védica
{"sun": "Taurus", "moon": "Pisces", "nakshatra": "Revati",
 "mahadasha": "Jupiter", "antardasha": "Saturn"}
# Oráculo (NO guardar pregunta completa — privacidad)
{"question_length": 87}
```

### 12.6 Retención: sin borrado automático v1

SQLite maneja millones de filas. Documentar para futuro: posible retención >1 año con agregados.

**Práctica para futuro:** Si se implementa limpieza (ej: feedback >7d), usar un solo DELETE con WHERE, no loop con execute individual:
```python
# Bien
await db.execute("DELETE FROM feedback WHERE timestamp < ?", (cutoff,))
# Mal
for id in expired_ids:
    await db.execute("DELETE FROM feedback WHERE id = ?", (id,))
```

### 12.7 Caché geocoding (con lock + user_agent + ciudades homónimas)

```python
_nominatim_lock = asyncio.Lock()
geolocator = Nominatim(user_agent="oraculo-sortilegios/1.0")
```

### 12.8 Dashboard admin — /stats limitado, /version

/stats y /version: solo `ADMIN_USER_ID`. Top 5 siempre. Si >4096 chars, splitear.

**Usuarios no-admin reciben respuesta in-character** (no silencio):

```python
async def stats_handler(update, context):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text(
            "Este comando es solo para el guardián de la taberna.",
            reply_to_message_id=update.message.message_id
        )
        return
    # ... mostrar stats
```

Sin esto, un usuario que escribe `/stats` piensa que el bot se colgó.

### 12.9 Alertas DM — Throttle completo

```python
_alert_timestamps: dict[str, float] = {}

async def send_alert(bot, alert_type: str, message: str, throttle_seconds: int = 300):
    now = time.time()
    last = _alert_timestamps.get(alert_type, 0)
    if now - last < throttle_seconds:
        return
    _alert_timestamps[alert_type] = now
    try:
        await bot.send_message(ADMIN_USER_ID, message)
    except Exception:
        logger.error(f"Failed to send alert: {alert_type}")
```

| Trigger | Throttle |
|---|---|
| Gasto diario > umbral | Sin throttle |
| Gasto acumulado > 80% | Una vez |
| Usuario > 10 usos/día | Sin throttle |
| Error API | 1 cada 5 min |
| API caída > 5 min | Una vez |
| Bot reiniciado | 1 cada 5 min |
| Truncamiento >30% modo/día | 1 al día |
| Bot removido (Forbidden) | Una vez |
| Respuesta vacía | 1 cada 5 min |

### 12.10 Tareas programadas (JobQueue)

```python
app.job_queue.run_repeating(cleanup_membership_cache, interval=3600, first=60)
app.job_queue.run_daily(send_weekly_summary, time=time(hour=9, minute=0), days=(0,))
```

### 12.11 Cola: 3 simultáneas, timeout 45s global

**Limitación conocida:** `asyncio.Semaphore` no garantiza FIFO. Si 5 peticiones esperan y se libera un slot, puede entrar cualquiera, no la más antigua. Con ≤3 personas esperando simultáneamente (caso raro), el impacto es mínimo. Si escala en el futuro, cambiar a `asyncio.Queue` explícita.

### 12.12 Manejo errores completo

| Error | Acción |
|---|---|
| Anthropic timeout | SDK reintenta ×2 automáticamente. Si falla → amigable |
| Anthropic 429 | SDK reintenta ×2 con backoff. Si falla → amigable + alerta |
| Anthropic 500 | SDK reintenta ×2. Si falla → amigable + alerta |
| Anthropic caída > 5 min | Degradado |
| Anthropic truncated | Cierre graceful + log |
| Anthropic vacío | "Las cartas guardan silencio" + log |
| Anthropic format inesperado | Log + error genérico |
| Queue timeout 45s | "Muchas consultas, inténtalo después" |
| Telegram 429 | RetryAfter |
| Telegram Forbidden | Log + alerta (removido) |
| Telegram BadRequest | Log + alerta (permisos) |
| Mensaje borrado (feedback) | try/except BadRequest, ignorar |
| Composición imagen | Degradación texto |
| Geocoding | Pedir alternativa más específica |
| Msg >4096 | Split párrafos |
| Sin perfil | Onboarding |
| Pydantic ValidationError | Mensaje amigable, no técnico |
| Excepción no controlada | Log (sin datos sensibles) + genérico + alerta |
| Placidus lat extrema | Whole Sign + disclaimer |

### 12.13 Logging — Sin datos sensibles

```python
logger.add(
    "/var/log/bot-taberna/bot_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
    rotation="00:00", retention="30 days", compression="gz", level="INFO",
    backtrace=False,     # No variables locales en stack traces
    diagnose=False,      # No contexto extra de diagnóstico
)
```

`backtrace=False` y `diagnose=False` evitan que fechas de nacimiento, ciudades u otros datos del usuario acaben en los logs por stack traces de excepciones.

**NUNCA loguear:** Settings completo (contiene token), contenido preguntas, respuestas Sonnet.

### 12.14 Backup (integrity check + pickle + VACUUM)

```bash
# SQLite backup diario
cp /path/bot-taberna.db /path/backups/bot-taberna-$(date +%Y%m%d).db
sqlite3 /path/backups/bot-taberna-$(date +%Y%m%d).db "PRAGMA integrity_check;"
find /path/backups/ -name "bot-taberna-*.db" -mtime +7 -delete

# Pickle persistence backup (junto con el DB)
cp /path/bot-taberna/bot_persistence.pickle /path/backups/bot_persistence-$(date +%Y%m%d).pickle

# VACUUM mensual (en horas muertas, no durante escrituras activas)
# Incluir en cron mensual o system-maintenance.sh
sqlite3 /path/bot-taberna.db "VACUUM;"
```

### 12.15 Deploy (systemd + botuser + venv + graceful shutdown)

**Graceful shutdown: SIGTERM (systemd) + SIGINT (Ctrl+C en desarrollo):**

```python
import signal

for sig in (signal.SIGTERM, signal.SIGINT):
    loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown(app)))
```

Sin SIGINT, un Ctrl+C durante desarrollo puede dejar la DB sin commit de transacción.

### 12.16 Topics preparado

### 12.17 Setup inicial del grupo

Procedimiento documentado para el primer arranque:

```
1. Crear bot en BotFather → token
2. Configurar: /setjoingroups off, /setcommands, foto, descripción
3. **NO tocar /setprivacy** — Dejar privacy mode ON (default). ForceReply maneja la comunicación.
4. Un admin de La Taberna añade el bot al grupo
5. Obtener chat_id:
   Opción A: Modo discovery temporal que loguea chat_ids
   Opción B: Enviar mensaje en el grupo, llamar a getUpdates
6. Copiar chat_id a .env (ALLOWED_CHAT_ID)
7. Configurar permisos del bot en ajustes del grupo (ver 4.7)
8. Reiniciar bot con chat_id correcto
9. Verificar que responde en el grupo y no en DM
10. **Verificar que onboarding funciona con privacy mode ON** (paso crítico)
```

---

## 13. Timezone — Crítico

Hora local → UTC con `timezonefinder` + `zoneinfo`.

**Limitación documentada:** Para nacimientos 1900-1970 en ciertos países, las zonas horarias históricas dependen de la precisión de la base de datos IANA. Generalmente buena, pero no perfecta universalmente. Para nacimientos pre-1900 (fecha mínima del bot), mayor incertidumbre. El bot no puede garantizar precisión al minuto para fechas muy antiguas.

---

## 14. Efemérides

`sepl_18.se1`, `semo_18.se1`, `seas_18.se1` (~5.5 MB). `swe.set_ephe_path()`.

### RESUELTO: kerykeion v5 cubre tropical + vedica

**Decisión (marzo 2026):** kerykeion v5 soporta `zodiac_type="Sidereal"` con `sidereal_mode="LAHIRI"` nativamente. No se necesita pyswisseph como dependencia separada.

- **Tropical:** `AstrologicalSubjectFactory.from_birth_data(...)` con Placidus (o Whole Sign si |lat|>60°)
- **Védica:** misma factory con `zodiac_type="Sidereal", sidereal_mode="LAHIRI", houses_system_identifier="W"`
- **Nakshatras y Vimshottari dashas:** cálculo propio a partir de `subject.moon.abs_pos` (kerykeion no los computa)
- **pyswisseph** viene como transitive dep de kerykeion — disponible via `import swisseph as swe` si se necesitan cálculos raw en el futuro
- Las efemérides están bundled en el paquete kerykeion (`kerykeion/sweph/`)

---

## 15. Personalidad — El Pezuñento (Baphomet)

### 15.0 Arquetipo

**El Pezuñento** — Baphomet de taberna. Energía Marte/Aries. Definido por Tam (admin de La Taberna).

Rasgos clave para el system prompt:
- Hermético con fuego: sabe de lo oculto porque lo ha vivido, no porque lo leyó
- Directo como un carnero: no endulza las lecturas, dice lo que las cartas dicen
- Humor oscuro y seco: se ríe mientras te dice la verdad
- Profundo cuando importa: si preguntas en serio, la respuesta es precisa
- Castellano peninsular: tuteo, expresiones con garra, sin arcaísmos pomposos
- NO es solemne, NO es críptico, NO es servil, NO pide perdón

Ejemplos de tono en mensajes del bot:
- Límite diario: "Ya has quemado tus tiradas de hoy. Vuelve mañana, que las cartas también descansan."
- Pregunta fuera de tema: "Eso pregúntaselo a Google. Yo leo las cartas, no hago recados."
- Respuesta vacía: "Las cartas no tienen nada que decirte ahora. Será que no es el momento."
- Cooldown: "Tranquilo, que las runas no se van a ir a ningún sitio. Espera un poco."

### 15.1 System prompt maestro

Siempre idéntico (se cachea). **Debe ser ≥1024 tokens** (requisito mínimo de Anthropic para caching). Incluye:
- "Responde en texto plano, sin HTML ni markdown"
- "Usa [[T]]...[[/T]] para títulos de sección y [[C]]...[[/C]] para nombres de cartas, runas o figuras"
- Nunca mostrar datos técnicos al usuario
- "No inventes cartas ni posiciones que no se te hayan dado"
- "Si no recibes hexagrama derivado, no inventes uno"
- Personalidad rica y detallada (ayuda a llegar a 1024 tokens)
- Reglas de interpretación extensas
- Disclaimers integrados en el tono

**CRÍTICO — Debe ser una constante literal.** Cualquier elemento dinámico rompe el caché:

```python
# BIEN: constante
MASTER_SYSTEM_PROMPT = """Eres El Pezuñento, el oráculo de La Taberna de los Sortilegios..."""

# MAL: fecha actual → hash cambia en cada llamada → caché nunca funciona
MASTER_SYSTEM_PROMPT = f"""Eres El Pezuñento... Hoy es {datetime.now()}..."""

# MAL: versión → cambia en cada deploy
MASTER_SYSTEM_PROMPT = f"""Versión {BOT_VERSION}. Eres El Pezuñento..."""
```

**Doble verificación antes de lanzar:**
1. Conteo de tokens ≥1024
2. El prompt es estático (no contiene f-strings, variables, ni nada dinámico)

```python
# test_system_prompt.py
def test_system_prompt_is_static():
    """El prompt debe ser idéntico en cada llamada para que el caché funcione."""
    prompt1 = get_master_prompt()
    prompt2 = get_master_prompt()
    assert prompt1 == prompt2

def test_system_prompt_no_fstrings():
    """No debe contener f-strings residuales ni variables."""
    prompt = get_master_prompt()
    assert "{" not in prompt or "{{" in prompt  # {{ es escape literal, OK

def test_system_prompt_min_tokens():
    """Debe tener ≥1024 tokens para que el caching se active."""
    prompt = get_master_prompt()
    # Estimación conservadora: ~4 chars = 1 token
    estimated_tokens = len(prompt) / 4
    assert estimated_tokens >= 1024, f"System prompt too short: ~{estimated_tokens} tokens"
```

### 15.2 Sub-prompts en user message

I Ching: instrucciones para ambos escenarios (con mutables y sin mutables / con derivado y sin derivado).

---

## 16. Costes — Recalculados para system prompt ≥1024 tokens

### 16.1 Pricing Sonnet 4.6

| Concepto | Precio/1M tokens |
|---|---|
| Input (no cacheado) | $3.00 |
| Output | $15.00 |
| Cache read (system prompt) | $0.30 |
| Cache write (primera vez/tras 5 min) | $3.75 |

### 16.2 Desglose de input por llamada

| Componente | Tokens | Cacheado | Coste típico/llamada |
|---|---|---|---|
| System prompt | 1,024 | Sí ($0.30/1M) | $0.00031 |
| Sub-prompt modo (en user msg) | 200-400 | No ($3.00/1M) | $0.0006-0.0012 |
| Perfil usuario | 15-40 | No | $0.00005-0.00012 |
| Datos tirada | 30-300 | No | $0.00009-0.0009 |
| Pregunta | 0-50 | No | $0-0.00015 |
| **Total input** | **~1,269-1,814** | | **~$0.0010-0.0025** |

System prompt cacheado: ~70% hit rate estimado. En cache miss (primera llamada tras 5 min sin uso), system cuesta $0.00384 en vez de $0.00031. Efecto amortizado en el coste medio.

### 16.3 Coste por uso — Peor caso (max_tokens agotados, system cacheado)

| Modo | Variante | Input total | Output (max) | Coste/uso |
|---|---|---|---|---|
| Tarot | 1 carta | ~1,309 | 400 | ~$0.007 |
| Tarot | 3 cartas | ~1,359 | 800 | ~$0.013 |
| Tarot | Cruz Celta | ~1,529 | 1,800 | ~$0.029 |
| Runas | 1 runa | ~1,299 | 400 | ~$0.007 |
| Runas | 3 Nornas | ~1,329 | 800 | ~$0.013 |
| Runas | Cruz | ~1,359 | 1,000 | ~$0.016 |
| I Ching | Hexagrama | ~1,429 | 1,000 | ~$0.017 |
| Geomancia | 1 figura | ~1,309 | 400 | ~$0.007 |
| Geomancia | Escudo | ~1,629 | 1,800 | ~$0.029 |
| Numerología | Informe | ~1,334 | 1,000 | ~$0.016 |
| Numerología | Compatibilidad | ~1,354 | 700 | ~$0.012 |
| Natal tropical | Completa | ~1,704 | 3,000 | ~$0.047 |
| Natal védica | Completa | ~1,704 | 3,000 | ~$0.047 |
| Oráculo | Libre | ~1,304 | 600 | ~$0.010 |

*Coste real será menor: Sonnet rara vez consume el 100% de max_tokens. Estimación conservadora.*

### 16.4 Proyección mensual

| Fase | Duración | Tiradas/día | Coste/mes |
|---|---|---|---|
| Pico novedad | ~2 semanas | ~200 | ~$32 total |
| Estabilización | ~2 meses | ~40 | ~$16/mes |
| Orgánico | 9+ meses | ~15 | ~$6-9/mes |

### 16.5 Presupuesto anual: €200 ($218)

| Concepto | Coste |
|---|---|
| Pico novedad | ~$32 |
| Estabilización (2 meses) | ~$32 |
| Orgánico (9 meses × ~$7.5) | ~$68 |
| **Subtotal estimado** | **~$132** |
| **Colchón** | **~$86** |
| **Presupuesto total** | **€200 ≈ $218** |

El aumento de 800→1024 tokens en system prompt añade ~$0.00007/llamada cacheada. En 10,000 tiradas/año: ~$0.70 extra. **Impacto despreciable.** El output sigue siendo 80-95% del coste total.

### 16.6 Infraestructura: €0

VPS, geocoding, Swiss Ephemeris, librerías, assets: todo gratuito o ya existente.

---

## 17. Testing

### 17.1 Unitarios

```
tests/
├── conftest.py                 # Mock API Anthropic
├── test_numerologia.py         # + normalización Unicode ñ/acentos
├── test_tarot_generator.py     # Unicidad, sin repetición
├── test_runas_generator.py
├── test_iching_generator.py    # Distribución + caso sin mutables
├── test_geomancia.py           # 3+ escudos calculados a mano, fila por fila
├── test_limits.py
├── test_validators.py          # Fechas inválidas → mensaje amigable, no crash
├── test_user_profile.py
├── test_timezone.py            # Zonas históricas, horario verano/invierno
├── test_formatting.py          # [[T]] [[C]] markers + html.escape + & < >
├── test_truncation.py          # + respuesta vacía
├── test_callback_data.py       # ≤ 64 bytes cada uno
├── test_drawn_data.py          # JSON schema por modo
├── test_sun_sign.py            # Fechas límite con efemérides
├── test_queue_timeout.py       # Timeout 45s global
└── test_system_prompt.py       # Verificar ≥1024 tokens
```

### 17.2 Mock API

### 17.3 Verificación manual — Cálculos

| Qué | Contra qué |
|---|---|
| Natal tropical | Astro.com (5+) |
| Natal védica | Jagannatha Hora (3+) |
| Numerología | Manual (5+) |
| Geomancia escudo | Manual a mano (3+ completos) |
| Timezone | UTC conocidos, verano/invierno |
| I Ching distribución | 1000 tiradas |
| Signo solar fechas límite | 19-22 de cada mes transición |
| Cruz Celta carta 2 | Visual: rotación + escala |
| Runas | 24 trazos correctos contra referencia visual Elder Futhark |
| Fuente etiquetas | NotoSans legible en composiciones |
| System prompt | Verificar ≥1024 tokens con `anthropic.count_tokens()` |

### 17.4 Testing de calidad de prompts

Antes de lanzar, ejecutar manualmente y evaluar calidad narrativa:

| Qué evaluar | Cuántas | Verificar |
|---|---|---|
| Tarot 3 cartas con pregunta | 5+ | ¿Usa el perfil? ¿Tono consistente? ¿[[T]] y [[C]] correctos? |
| Cruz Celta | 3 | ¿Cubre las 10 posiciones? ¿Largo OK antes de truncar? |
| I Ching con mutables | 3 | ¿Interpreta transformación? |
| I Ching sin mutables | 2 | ¿No inventa derivado? |
| Natal tropical | 3 | ¿Interpreta todos los planetas/aspectos dados? |
| Natal védica | 3 | ¿Dashas y yogas correctos? |
| Oráculo fuera de temática | 3 | ¿Rechaza "¿cuánto cuesta un iPhone?" in-character? |
| Perfil personalizado | 2 comparativas | ¿Cambia interpretación si Escorpio vs Aries? |
| Numerología con nombre | 3 | ¿full_birth_name se usa correctamente? |

### 17.5 Integración manual

> Items marcados [x] = implementado en código y/o verificado con tests automatizados.
> Items marcados [ ] = requiere verificación manual en grupo real (post-despliegue).

- [x] Límites + cooldown (test_queue_timeout.py, bot/limits.py)
- [x] /borrarme cascade (ON DELETE CASCADE en schema SQL)
- [x] Onboarding: completo / sin hora / incompleto / timeout / post-restart (ConversationHandler + SQLite partial)
- [x] Petición en curso + nuevo comando → "aún en proceso" (bot/concurrency.py)
- [x] Msg >4096 (bot/formatting.py split_message, test_formatting.py)
- [x] Ciudad homónima → "escríbelo más completo" (onboarding.py confirm_city_callback)
- [x] Fecha/hora inválida → mensaje amigable (test_validators.py, nunca técnico)
- [x] /cancelaroraculo todos los flujos (ConversationHandler fallbacks)
- [x] Concurrencia (_active_requests + semaphore, test_queue_timeout.py)
- [x] DMs, otros grupos, edits, fotos, stickers → ignorados (bot/middleware.py)
- [x] Feedback: solo dueño, no doble, expirado, otro usuario, mensaje borrado (bot/feedback.py)
- [x] Reply-to: foto → texto → feedback (cadena visual en handlers)
- [x] Caption en imágenes (build_caption en cada composer)
- [x] JPEG resolución + verificación <10MB (compose_to_jpeg, test_tarot_images.py)
- [x] Etiquetas legibles en composiciones (NotoSans-Regular.ttf descargada)
- [x] /stats, /version solo admin, no-admin → in-character (bot/handlers/admin.py)
- [x] /start DM y grupo (bot/handlers/start.py, test_handlers_basic.py)
- [x] /ayuda contenido completo (test_handlers_basic.py verifica 16 comandos)
- [x] Runas renderizadas correctamente (trazos vectoriales Pillow, test_runas_generator.py 24 runas)
- [x] Cruz Celta carta 2 rotación + escala (images/tarot_composer.py, test_tarot_images.py)
- [x] Graceful shutdown (post_shutdown cierra DB + Anthropic client)
- [x] Telegram 429, Forbidden, BadRequest (middleware + typing + feedback handlers)
- [x] Username actualizado (middleware._update_username_if_changed)
- [x] Truncamiento: cierre + log (test_truncation.py)
- [x] Respuesta vacía: mensaje + log (test_truncation.py)
- [x] Typing no expira (renovado 4s, bot/typing.py)
- [x] Latitud extrema → Whole Sign (natal_tropical.py |lat|>60)
- [x] HTML escape (test_formatting.py, html.escape + [[T]][[C]])
- [x] drawn_data JSON (test_drawn_data.py, todos los modos)
- [x] Composición falla → degradación texto (build_text_fallback en cada composer)
- [x] Callback data ≤ 64 bytes (test_callback_data.py, 47 tests parametrizados)
- [x] Signo solar fecha límite (test_sun_sign.py, efemérides si kerykeion disponible)
- [x] Alerta restart throttled (bot/alerts.py throttle_seconds=300)
- [x] Token no aparece en logs (backtrace=False, diagnose=False)
- [x] Queue timeout 45s → mensaje amigable (test_queue_timeout.py)
- [x] Numerología pide nombre completo si no lo tiene (ForceReply en handler)
- [x] I Ching sin mutables → 1 hexagrama, no 2 (test_iching_generator.py)
- [x] Geomancia escudo derivación correcta (3 escudos a mano, test_geomancia.py)
- [x] System prompt ≥1024 tokens verificado (test_system_prompt.py)
- [x] PicklePersistence: corruption handling en startup (bot/main.py)
- [x] EXIF: ImageOps.exif_transpose() antes de cachear (images/card_cache.py)
- [x] SDK retries: no hay retry manual adicional (anthropic_client.py max_retries=2 solo)
- [x] Kerykeion v5: tropical y védica nativo en misma sesión (sidereal_mode="LAHIRI")
- [x] Typing: bot removido durante tirada → try/except Forbidden (bot/typing.py)
- [x] BytesIO cerrado tras envío (finally: jpeg_buffer.close() en handlers)
- [x] /stats por usuario no-admin → "solo para el guardián" (bot/handlers/admin.py)
- [x] /version por usuario no-admin → "solo para el guardián"
- [x] Migración grupo→supergrupo → alerta con IDs (bot/middleware.py handle_migration)
- [x] Imagen Cruz Celta <10MB (test_tarot_images.py, verificado 369KB con cartas reales)
- [x] /bibliomancia → grid de 4 botones (bot/handlers/bibliomancia.py)
- [x] /bibliomancia biblia → fragmento directo (test_bibliomancia.py)
- [x] /bibliomancia coran → fragmento directo (test_bibliomancia.py)
- [x] /bibliomancia gita → fragmento directo (test_bibliomancia.py)
- [x] /bibliomancia evangelio → fragmento directo (test_bibliomancia.py)
- [x] /bibliomancia no repite último fragmento (test_bibliomancia.py anti-repetición)
- [x] /bibliomancia mensaje >4096 → split correcto (test_bibliomancia.py)
- [x] /admins → grid 2 columnas (test_admins.py grid_keyboard_structure)
- [x] /admins @void → bio directa (test_admins.py find_admin_by_username)
- [x] /admins void → bio directa sin @ (test_admins.py find_admin_by_key)
- [x] /admins nombre_inexistente → "No conozco a ese guardián" (test_admins.py)
- [x] /admins botón bio → edit message + [← Volver] (admins_callback)
- [x] /admins [← Volver] → grid original edit message (admins_callback "back")
- [x] /start en grupo → presentación + registrado vs no registrado (test_handlers_basic.py)
- [x] /start en DM → "solo funciono en La Taberna" (test_handlers_basic.py)
- [ ] Todos los modos end-to-end (requiere despliegue con API key real)
- [ ] Onboarding simultáneo 2 usuarios (requiere grupo real)
- [ ] ForceReply: onboarding funciona en grupo CON privacy mode ON (requiere grupo real)
- [ ] ForceReply: flujo pregunta funciona en grupo con privacy mode ON (requiere grupo real)
- [ ] ForceReply: compatibilidad (segunda fecha) funciona con privacy ON (requiere grupo real)
- [ ] ForceReply: actualizarperfil funciona con privacy ON (requiere grupo real)

---

## 18. Planning (Claude Code, ~3 semanas)

### Semana 1: Infraestructura + Tarot + Runas + I Ching — COMPLETADA

**Día 1-2: Esqueleto** — COMPLETADO
- [x] Estructura proyecto (sección 19)
- [x] Config pydantic (dev/prod, max_tokens, version, API version, timeouts)
- [x] .env.example
- [x] Dependencias pineadas (actualizadas a últimas versiones)
- [x] SQLite: WAL + FK + auto-init + migraciones + singleton + close()
- [x] Middleware completo (edits, DM, /start, chat_id, topics, membresía caché, username, Forbidden, BadRequest, **ChatMigration handler**)
- [x] Bloqueo peticiones concurrentes por usuario
- [x] Límites + cooldown
- [x] PicklePersistence (update_interval=60, corruption handling en startup)
- [x] Pydantic models (model_validate, truncated, error types)
- [x] AsyncAnthropic singleton: cache system fijo ≥1024, version pinned, SDK retries (NO manuales), cola, max_tokens, coste real, stop_reason, vacío, parseo seguro
- [x] Timeout global 45s
- [x] Typing renovado 4s (con error handling Forbidden/BadRequest)
- [x] HTML escape + formateo ([[T]][[C]] markers)
- [x] Telegram 429 + Forbidden + BadRequest
- [x] Reply-to cadena: foto → texto → feedback
- [x] Graceful shutdown (post_shutdown + DB close)
- [x] BOT_START_TIME
- [x] Loguru (backtrace=False, diagnose=False)
- [x] .gitignore
- [x] JobQueue (limpieza caché, resumen semanal)
- [x] Alertas throttled
- [x] SystemRandom
- [x] ConversationHandler onboarding completo (bot/handlers/onboarding.py: alias→fecha→hora→ciudad, ForceReply, timeout 5min, /cancelaroraculo, retomar SQLite, PicklePersistence)

**Día 3-4: Tarot** — COMPLETADO (51 tests)
- [x] tarot_cards.json nombres español (Hierofante, Bastos, Sota, Caballero)
- [x] Generador SystemRandom.sample
- [x] LRU cache (with + copy + EXIF transpose)
- [x] Composiciones JPEG 85% + verificación <10MB
- [x] Cruz Celta Waite + carta 2 rotación + escala
- [x] Caption + degradación si falla + BytesIO.close()
- [x] System prompt maestro (texto plano, ≥1024 tokens, constante)
- [x] Sub-prompt tarot
- [x] Feedback (expiración 7d, protecciones, BadRequest tolerante)
- [x] drawn_data JSON
- [x] Tests
- [x] PNGs Rider-Waite — 78 cartas descargadas (krates98/tarotcardapi, dominio publico)
- [x] Fuente NotoSans-Regular.ttf — descargada de Google Fonts (2MB)

**Día 5: Runas + I Ching** — COMPLETADO (38 tests)
- [x] RUNE_PATHS (24 coordenadas + Wyrd) + renderer trazos Pillow
- [x] runas.json + composiciones + captions
- [x] Sub-prompt runas
- [x] Generador I Ching (distribución 6=1/8, 7=3/8, 8=3/8, 9=1/8)
- [x] Caso sin mutables (1 hexagrama, no 2)
- [x] iching_hexagrams.json (64 hexagramas + tabla King Wen completa)
- [x] Renderer + sub-prompt (con y sin derivado)
- [x] Tests (distribución 10000 tiradas + sin mutables + probabilidad 17.8%)

### Semana 2: Geomancia + Numerología + Natales + Oráculo — COMPLETADA

**Día 1: Geomancia + Numerología** — COMPLETADO (45 tests)
- [x] Generador escudo completo (4M → 4H → 4S → 2T → J → R)
- [x] Renderer (1 figura + escudo)
- [x] 3+ escudos calculados a mano (fila por fila, verificados)
- [x] Numerología pitagórica + normalización Unicode (ñ→n, á→a, ü→u, ç→c)
- [x] full_birth_name pedido aparte (ForceReply)
- [x] Compatibilidad solo camino vida
- [x] Sub-prompts

**Día 2-3: Natales** — COMPLETADO (62 tests, 10 skipped en Windows)
- [x] kerykeion v5 — **NO necesita pyswisseph separado** (sidereal Lahiri nativo)
- [x] Geocoding caché SQLite + asyncio.Lock + 1.1s sleep + user_agent
- [x] Timezone (timezonefinder + zoneinfo) + limitaciones históricas documentadas
- [x] Signo solar con efemérides (fallback tabla si sin kerykeion)
- [x] Natal tropical: Placidus, Whole Sign si |lat|>60°
- [x] Natal védica: Lahiri, nakshatras.json (27), Vimshottari dashas
- [x] Sin hora → simplificada (sin ascendente ni casas)
- [x] Tests contra Astro.com (5: Lennon, Kahlo, Einstein, Madonna, sin hora)
- [x] Tests timezone (verano/invierno Madrid/NY/India, zonas 1900/1920/1950)
- [x] Tests signo solar fechas límite (12 signos + 4 transiciones)

**Día 4-5: Oráculo + Extras + Admin** — COMPLETADO (28 tests)
- [x] Oráculo + sub-prompt + ForceReply + inline /oraculo ¿pregunta?
- [x] /bibliomancia: handler browse+directo, 4 textos (BIBLIA/CORAN/GITA/EVANGELIO), anti-repetición, split >4096
- [x] /admins: grid 2 columnas + bio + mención tg://user + volver + búsqueda
- [x] /start: presentación in-character (grupo vs DM, registrado vs no)
- [x] /stats (top 5, solo admin, no-admin → in-character) + /version
- [x] /miperfil + /borrarme
- [x] /ayuda (contenido completo con 16 comandos)
- [x] Alertas throttled
- [x] Mensajes in-character pulidos (tono Baphomet, sin lenguaje técnico, sin tono servil)

### Semana 3: Testing + Lanzamiento

**Día 1-2: Testing completo** — COMPLETADO (293 tests, 10 skipped)
- [x] test_drawn_data.py: todos los modos (tarot, runas, iching, geomancia, numerología, oráculo)
- [x] test_callback_data.py: 41+ callbacks, cada uno ≤64 bytes, parametrized
- [x] test_queue_timeout.py: concurrencia, semáforo, timeout
- [x] test_validators.py: sanitización, truncamiento 200 chars, perfiles
- [x] test_truncation.py: respuestas truncadas, vacías, todos los tipos de error
- [x] test_system_prompt.py: estático, sin f-strings, ≥1024 tokens
- [x] README.md completo
- [x] AGPL-3.0 LICENSE
- [x] ROADMAP.md actualizado con estado real

**Completado en Semana 3:**
- [x] PNGs Rider-Waite dominio publico (78 cartas descargadas, krates98/tarotcardapi)
- [x] NotoSans-Regular.ttf (Google Fonts, 2MB)
- [x] ConversationHandler onboarding completo (bot/handlers/onboarding.py)
- [x] /actualizarperfil handler completo (bot/handlers/profile.py ConversationHandler)
- [x] Todos los handlers registrados en main.py (16 CommandHandlers + dispatcher callbacks)
- [x] botfather_commands.txt (16 comandos, coincide con /ayuda)
- [x] Auditoria final: .env.example completo (33 variables), sin TODOs, sin dead code

**Pendientes para despliegue (requieren grupo real):**
- [ ] BotFather setup (/setjoingroups off, /setcommands con data/botfather_commands.txt, foto)
- [ ] Obtener chat_id del grupo (via getUpdates)
- [ ] admins_private.json con datos reales (20 admins)
- [ ] Verificar onboarding con privacy mode ON en grupo real
- [ ] Verificar natales contra Astro.com/Jagannatha Hora (en VPS con kerykeion)
- [ ] Setup VPS: systemd service, venv, build-essential
- [ ] Backup cron (SQLite + pickle)
- [ ] Monitorizar primeras horas post-lanzamiento

---

## 19. Estructura del Proyecto

```
bot-taberna/
│
├── bot/                                # CAPA 1
│   ├── __init__.py
│   ├── main.py                         # Entry, signals, BOT_START_TIME, JobQueue, PicklePersistence
│   ├── config.py                       # Settings completo
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── start.py
│   │   ├── menu.py
│   │   ├── onboarding.py              # Timeout, retomar, bloqueo, ForceReply, simultáneo
│   │   ├── tarot.py
│   │   ├── runas.py
│   │   ├── iching.py                  # Con y sin derivado
│   │   ├── geomancia.py
│   │   ├── numerologia.py             # Pide nombre completo si falta
│   │   ├── natal.py
│   │   ├── vedica.py
│   │   ├── oraculo.py
│   │   ├── bibliomancia.py            # Browse + directo, datos en memoria, €0 API
│   │   ├── admins.py                  # Grid inline + bio + volver, edit_message, €0 API
│   │   ├── profile.py
│   │   ├── admin.py                   # /stats, /version, alertas, no-admin → in-character
│   │   └── help.py                    # Contenido definido
│   ├── middleware.py                   # Completo (Forbidden, BadRequest, token seguro)
│   ├── keyboards.py                   # Callback ≤ 64 bytes
│   ├── limits.py
│   ├── messages.py                    # In-character + vacío + timeout + en proceso
│   ├── feedback.py                    # 7d expiración, BadRequest tolerante
│   ├── formatting.py                  # html.escape + [[T]][[C]] markers → HTML
│   ├── typing.py                      # Renovado 4s
│   ├── concurrency.py                # _active_requests bloqueo por usuario
│   └── jobs.py                        # JobQueue tasks
│
├── service/                            # CAPA 2
│   ├── __init__.py
│   ├── interpreter.py
│   ├── anthropic_client.py            # AsyncAnthropic singleton, version pinned, parseo seguro
│   ├── models.py                      # model_validate(), error types
│   ├── prompts/
│   │   ├── master.py                  # Texto plano, idéntico siempre
│   │   ├── tarot.py
│   │   ├── runas.py
│   │   ├── iching.py                  # Con y sin derivado
│   │   ├── geomancia.py
│   │   ├── numerologia.py
│   │   ├── natal_tropical.py
│   │   ├── natal_vedica.py
│   │   └── oraculo.py
│   └── calculators/
│       ├── natal_tropical.py          # Whole Sign fallback
│       ├── natal_vedica.py
│       ├── numerologia.py             # Unicode norm + nombre completo
│       ├── geocoding.py               # Caché + lock + homónimas
│       ├── timezone.py                # Limitaciones documentadas
│       └── sun_sign.py                # Efemérides
│
├── generators/                         # SystemRandom, sin repetición
│   ├── tarot.py
│   ├── runas.py
│   ├── iching.py                      # Distribución + sin mutables
│   └── geomancia.py                   # Método documentado
│
├── images/
│   ├── tarot_composer.py              # Cruz Celta carta 2, degradación
│   ├── rune_renderer.py               # Trazos vectoriales Pillow (RUNE_PATHS)
│   ├── hexagram_renderer.py           # 1 o 2 hexagramas según mutables
│   ├── geomancy_renderer.py
│   ├── card_cache.py                  # LRU, with+copy, EXIF transpose
│   └── textures/
│
├── database/
│   ├── connection.py                  # Singleton, WAL (permisos dir), FK, transactions, close()
│   ├── migrations/
│   ├── migrator.py
│   ├── users.py                       # + full_birth_name + update_username
│   ├── usage.py                       # drawn_data JSON + truncated
│   ├── feedback.py                    # UNIQUE + expiración queries
│   └── geocache.py                    # timezone + homónimas
│
├── assets/
│   ├── tarot/                          # 78 PNGs
│   └── fonts/
│       └── NotoSans-Regular.ttf        # Etiquetas composiciones
│
├── ephe/                               # Swiss Ephemeris
├── data/                               # JSONs + datos estáticos
│   ├── tarot_cards.json               # 78 cartas, nomenclatura Tam
│   ├── runas.json                     # 24 Elder Futhark + Wyrd
│   ├── iching_hexagrams.json          # 64 hexagramas
│   ├── nakshatras.json                # Natales védicas
│   ├── bibliomancia_datos.py          # ~6MB, CORAN/EVANGELIO/BIBLIA/GITA
│   ├── admins_private.json            # IDs reales + bios. EN .GITIGNORE.
│   └── admins_private.example.json    # En repo, datos fake, formato referencia
├── tests/                              # + conftest, queue_timeout, drawn_data, sun_sign
│
├── .env / .env.example / .gitignore / requirements.txt / README.md
└── bot-taberna.db
```

### .env.example (valores fake, nunca vacíos)

```env
ENV=dev
BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
ANTHROPIC_API_KEY=sk-ant-api03-FAKE-KEY-HERE
ANTHROPIC_API_VERSION=2024-10-22
ALLOWED_CHAT_ID=-1001234567890
ALLOWED_THREAD_ID=
ADMIN_USER_ID=123456789
BOT_VERSION=1.0.0
MONTHLY_SPENDING_LIMIT=25.0
DAILY_ALERT_THRESHOLD=5.0
QUEUE_TIMEOUT=45.0
FEEDBACK_EXPIRY_DAYS=7
MAX_TOKENS_TAROT_1=400
MAX_TOKENS_TAROT_3=800
MAX_TOKENS_TAROT_CRUZ=1800
MAX_TOKENS_RUNAS_1=400
MAX_TOKENS_RUNAS_3=800
MAX_TOKENS_RUNAS_CRUZ=1000
MAX_TOKENS_ICHING=1000
MAX_TOKENS_GEOMANCIA_1=400
MAX_TOKENS_GEOMANCIA_ESCUDO=1800
MAX_TOKENS_NUMEROLOGIA=1000
MAX_TOKENS_NUMEROLOGIA_COMPAT=700
MAX_TOKENS_NATAL_TROPICAL=3000
MAX_TOKENS_NATAL_VEDICA=3000
MAX_TOKENS_ORACULO=600
```

### .gitignore

```
.env
bot-taberna.db
bot-taberna.db-wal
bot-taberna.db-shm
bot_persistence.pickle
admins_private.json
__pycache__/
*.pyc
.venv/
ephe/
*.log
*.log.gz
```

---

## 20. Riesgos

| Riesgo | Prob. | Mitigación |
|---|---|---|
| Pico presupuesto | Baja | Límites + alertas + spending limit |
| Kerykeion mal | Media | Verificar Astro.com |
| Timezone incorrecto | Media | timezonefinder + tests + limitaciones documentadas |
| Signo solar fecha límite | Media | Efemérides, no tabla fija |
| Efemérides ausentes | Baja | Descargar .se1 |
| Runas: coordenadas incorrectas | Media | Verificar visual de las 24 runas contra referencia |
| Placidus lat extrema | Baja | Whole Sign fallback |
| Nominatim homónimas | Media | Pedir más específico |
| Nominatim rate limit | Media | Caché + lock |
| Lecturas genéricas | Media | Feedback → iterar |
| Truncadas | Media | Cierre graceful + ajustar max_tokens |
| Respuesta vacía | Baja | Mensaje amigable + log |
| API format cambio | Baja | Version pinned + parseo seguro |
| HTML roto | Media | Texto plano + escape |
| Prompt injection | Media | 200 chars + sanitización + XML |
| Bot crash | Baja | systemd + graceful + alerta throttled |
| Crash loop | Baja | Alerta throttled 5 min |
| SQLite locked | Baja | WAL + busy_timeout |
| SQLite corrupción | Muy baja | Backup + integrity |
| ConversationHandler conflicto | Media | Bloqueo onboarding |
| ConversationHandler perdido | Media | Retomar SQLite |
| Peticiones concurrentes usuario | Media | _active_requests bloqueo |
| Queue saturada | Baja | Timeout 45s + mensaje |
| Anthropic precios | Baja | Colchón + migración |
| API caída | Baja | Degradado + alerta |
| Telegram 429 | Baja | RetryAfter |
| Bot removido | Baja | Forbidden → alerta |
| Permisos removidos | Baja | BadRequest → alerta |
| Mensaje borrado admin | Media | try/except BadRequest |
| Callback >64 bytes | Baja | Códigos cortos + test |
| Typing expira | Media | Renovar 4s |
| Imagen no carga | Baja | Caption descriptivo |
| Composición falla | Baja | Degradación texto |
| Feedback huérfano | Media | Expiración 7d |
| Feedback ajeno | Baja | Solo dueño |
| Generador sesgado | Baja | SystemRandom + drawn_data |
| Username cambiado | Alta | Update middleware |
| Numerología ñ/acentos | Alta | Normalización |
| Pydantic error al usuario | Media | try/except → amigable |
| Token filtrado | Baja | .env + nunca en logs + /revoke |
| Datos sensibles en logs | Baja | backtrace=False, diagnose=False |
| Breaking changes deps | Media | Versiones pineadas |
| Kerykeion AGPL-3.0 obliga repo público | Ninguno | Repo público obligatorio. Secretos en .env/.gitignore |
| /stats >4096 | Baja | Top 5 limitado + split |
| Nombre numerología ≠ alias | Media | full_birth_name pedido aparte |
| System prompt <1024 tokens | Media | Verificar conteo, enriquecer si necesario |
| Cliente Anthropic síncrono | Alta | AsyncAnthropic obligatorio, nunca síncrono |
| Formateo ## y ** inconsistente | Media | Marcadores custom [[T]] [[C]] |
| Escrituras no atómicas SQLite | Baja | Transacciones explícitas |
| PicklePersistence corrupto | Baja | Fallback retomar desde SQLite |
| WAL sin permisos directorio | Baja | chown directorio completo |
| BytesIO memory leak | Baja | close() tras envío |
| SQLite crecimiento sin VACUUM | Baja | VACUUM mensual en mantenimiento |
| Double retry (SDK × manual) | Alta | Usar solo SDK retries, NO añadir manuales |
| Kerykeion/pyswisseph conflicto | Media | Verificar comparten instancia, testear juntos |
| Pickle corrupto impide arranque | Baja | try/except + borrar + recrear + fallback SQLite |
| Typing task exception silenciosa | Baja | try/except Forbidden/BadRequest en keep_typing |
| EXIF invierte cartas | Baja | ImageOps.exif_transpose() antes de cachear |
| Semaphore no FIFO | Muy baja | Documentado, migrar a Queue si escala |
| Privacy mode: bot no recibe texto en grupo | **Crítica** | **ForceReply(selective=True) en todos los ConversationHandlers** |
| Migración grupo→supergrupo cambia chat_id | Baja | Handler ChatMigration + alerta sin throttle |
| Imagen >10MB rechazada por Telegram | Baja | Verificación tamaño + reducción quality automática |
| /stats silencioso para no-admin | Media | Respuesta in-character "solo para el guardián" |

---

## 21. Mejoras futuras

Memoria entre tiradas, compatibilidad tarot, tránsitos, sinastría, revolución solar, fases lunares, modo educativo, canal premium, dashboard web, migración modelo, foto tirada → interpretación, Marsella, oráculo historial, avisos lunaciones, webhook (si long polling), retención datos, múltiples resultados geocoding como botones, /frase (frases aleatorias de bot externo — pendiente datos).

---

## 22. Decisiones (17 resueltas + 1 acción pendiente)

### Todas resueltas

| # | Decisión | Resolución |
|---|---|---|
| 1 | Nombre del bot | **El Oráculo de los Sortilegios** |
| 2 | Username Telegram | **@oraculo_sortilegios_bot** |
| 3 | Arquetipo y tono | **Baphomet de taberna** — hermético con fuego Marte/Aries. Directo, humor oscuro y seco, no endulza las lecturas. Sabe de lo oculto porque lo ha vivido. Dice la verdad en la cara, pero si preguntas en serio la respuesta es profunda y precisa. Personalidad definida por Tam (admin del grupo). |
| 4 | Framework tarot | **Rider-Waite con toques herméticos** (raíces Golden Dawn, simbología alquímica) |
| 5 | Nomenclatura cartas | **Hierofante, Bastos, Sota, Caballero**. Decisión de Tam. |
| 6 | Invertir cartas | **Todas las 78** (mayores y menores). Estándar Rider-Waite, lecturas más ricas. |
| 7 | Sistema numerológico | **Pitagórico**. Estándar occidental, más documentado. |
| 8 | Textos líneas I Ching | **Delegar en Sonnet**. Conoce el Wilhelm. Sin JSON de 384 líneas que curar/traducir. |
| 9 | Disposición Cruz Celta | **Waite clásica**. Estándar reconocible. |
| 10 | Framework runas | **Nórdico con interpretación esotérica moderna**. Equilibrio entre rigor histórico y lectura accesible. |
| 11 | Framework I Ching | **Wilhelm**. Traducción de referencia en Occidente. |
| 12 | Idioma | **Castellano peninsular con actitud**. Tuteo, directo, sin arcaísmos pomposos. Coherente con el arquetipo Baphomet/Aries. |
| 13 | Estilo visual runas | **Trazos vectoriales Pillow sobre textura piedra**. Zero assets, estilo único tallado, 100% código propio, AGPL-compatible. |
| 14 | Umbral alerta gasto | **$3/día**. Conservador — con uso orgánico ~$6-8/mes, $3 avisa antes de que sea tarde. |
| 16 | Webhook vs Long Polling | **Long polling dev → webhook producción**. LP para desarrollo rápido, webhook cuando estable. |
| 17 | Repo | **Público obligatorio** (AGPL-3.0 kerykeion/pyswisseph). Secretos en .env/.gitignore. |
| 18 | Fuente etiquetas | **NotoSans-Regular**. Legible, libre, sin problemas de licencia. |

### Acción pendiente (1)

| # | Acción | Cómo |
|---|---|---|
| 15 | **Chat ID del grupo** | Añadir @oraculo_sortilegios_bot a La Taberna → llamar getUpdates → copiar chat_id a .env |

---
