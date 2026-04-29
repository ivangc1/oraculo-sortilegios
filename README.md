# El Oraculo de los Sortilegios

Bot de Telegram para el grupo **La Taberna de los Sortilegios** (~2,600 miembros). Ofrece lecturas de tarot (Rider-Waite y Marsella), runas, I Ching, geomancia, numerologia, cartas natales, demonologia y angelologia, impulsado por Claude Sonnet 4.6 de Anthropic con extended thinking.

**@oraculo_sortilegios_bot** | Licencia: AGPL-3.0

## Modos disponibles

| Comando | Sistema | Variantes |
|---|---|---|
| `/tirartarot` | Tarot (RWS / Marsella) | Selector de mazo, 1 carta, 3 cartas, Cruz Celta, Si/No, Herradura (7), Relacion (6), Estrella (7), Cruz Simple (5), Tirada del dia, Smart selector |
| `/runa` | Runas Elder Futhark | Odin, Tres Nornas, Cruz Runica, Cinco Runas, Siete Runas |
| `/iching` | I Ching (Wilhelm) | Hexagrama con/sin lineas mutables |
| `/geomancia` | Geomancia | Una figura, Escudo completo |
| `/numerologia` | Pitagorica | Informe completo, Compatibilidad |
| `/natal` | Carta natal tropical | Placidus (Whole Sign si lat >60) |
| `/vedica` | Carta natal vedica | Lahiri ayanamsa, Nakshatras, Dashas |
| `/oraculo` | Pregunta libre | Sonnet interpreta directamente |
| `/bibliomancia` | Textos sagrados | Biblia, Coran, Gita, Evangelio de Tomas, Liber AL vel Legis |
| `/demonio` | Demonologia | 72 demonios Goetia, carta + sigilo + ficha, opcional interpretacion LLM |
| `/angel` | Angelologia | 72 angeles Shem, ficha o interpretacion LLM si hay pregunta |
| `/sello` | Demonologia | Solo el sigilo canonico Goetia 1904, sin retrato ni ficha (€0 API) |
| `/firma` | Angelologia | Firma hebrea del angel Shem sobre pergamino (€0 API) |
| `/invocar` | Roleplay | La entidad (demonio o angel) habla en primera persona como ese ser |
| `/consulta` | Registro | Redirige a DM para onboarding privado |
| `/startoraculo` | Presentacion | Intro del oraculo en grupo |
| `/ayudaoraculo` | Ayuda | Lista de todos los comandos |
| `/miperfil` | Perfil | Envia datos registrados por DM (privacidad) |
| `/actualizarperfil` | Perfil | Redirige a DM para actualizar hora/ciudad |
| `/borrarme` | Perfil | Eliminar perfil y historial |
| `/cancelaroraculo` | Control | Cancelar operacion en curso |
| `/reportar` | Moderacion | Reportar usuario/mensaje a los admins (reply o @usuario) |

## Stack tecnico

| Componente | Tecnologia |
|---|---|
| Lenguaje | Python 3.12+ |
| Framework Telegram | python-telegram-bot 22.7 |
| IA | Anthropic API (Claude Sonnet 4.6) via AsyncAnthropic 0.97 |
| Modelo | `claude-sonnet-4-6` (configurable via `ANTHROPIC_MODEL`) |
| Extended thinking | Activo (low/medium/high por modo, mapea a `budget_tokens`) |
| Validacion | pydantic 2.13 + pydantic-settings 2.14 |
| Base de datos | SQLite3 + aiosqlite 0.22 (WAL, FK off para guests, índices en usage_log) |
| Astrologia | kerykeion 5.12.8 (tropical + sidereal Lahiri nativo) |
| Geocoding | geopy 2.4 (Nominatim) |
| Timezone | timezonefinder 8.2 + zoneinfo |
| Imagenes | Pillow 12.2 |
| Aleatoriedad | random.SystemRandom |
| Logging | loguru 0.7 |
| Testing | pytest 9.0 + pytest-asyncio 1.3 (en `requirements-dev.txt`) |

## Arquitectura

Dos capas separadas:

- **Capa Bot** (`bot/`): Telegram handlers, middleware, limites, concurrencia, imagenes
- **Capa Servicio** (`service/`): AsyncAnthropic singleton, sub-prompts, calculadoras

Comunicacion via `InterpretationRequest` / `InterpretationResponse` (modelos Pydantic).

## Setup

### Requisitos previos

- Python 3.12+
- `build-essential python3-dev` (Linux, para compilar pyswisseph)

### Instalacion

```bash
git clone https://github.com/tu-usuario/oraculo-sortilegios.git
cd oraculo-sortilegios
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt        # produccion
pip install -r requirements-dev.txt    # incluye pytest para desarrollo
```

### Configuracion

```bash
cp .env.example .env
# Editar .env con valores reales
```

Variables obligatorias en `.env`: `BOT_TOKEN`, `ANTHROPIC_API_KEY`, `ALLOWED_CHAT_ID`, `ADMIN_USER_ID`.

Todas las demas variables tienen defaults razonables en `config.py`. Ver `.env.example` para la lista completa. Los valores `MAX_TOKENS_*` y `EFFORT_*` son defaults del codigo — no hace falta ponerlos en `.env` salvo que quieras overrides especificos por entorno.

### Setup BotFather

1. Crear bot en BotFather, obtener token
2. `/setjoingroups` off
3. `/setcommands` con la lista de `data/botfather_commands.txt`
4. `/setprivacy` → **Disable** (privacy mode OFF — el bot necesita recibir mensajes del grupo; middleware filtra por chat_id/thread_id)
5. Anadir bot al grupo, obtener chat_id via getUpdates
6. Permisos recomendados: "Delete messages" (borrar datos sensibles en grupo), "Pin messages" (opcional)
7. `ALLOWED_THREAD_ID` es opcional — solo necesario si el grupo usa forum/topics y quieres restringir a un hilo concreto

### Ejecucion

```bash
python -m bot.main          # Desarrollo (long polling)
sudo systemctl start oraculo      # Produccion (systemd)
```

### Tests

```bash
python -m pytest tests/ -v
```

Tests de natales con kerykeion se saltan en Windows (necesitan pyswisseph compilado). Se ejecutan en el VPS Linux.

## Estructura del proyecto

```
bot/                    # Capa 1: Telegram
  handlers/             # Handlers por modo (+ dm_onboarding.py para flujos DM)
  main.py               # Entry point, signals, persistence
  config.py             # Settings (pydantic-settings, 47 variables)
  middleware.py          # Edits, DM whitelist, chat_id, membresia, migracion
service/                # Capa 2: Interpretacion
  anthropic_client.py   # AsyncAnthropic singleton, adaptive thinking, cache
  prompts/              # System + sub-prompts por modo
  calculators/          # Geocoding, timezone, natal, numerologia
generators/             # SystemRandom, sin repeticion
images/                 # Pillow: tarot, runas, hexagramas, geomancia
database/               # SQLite singleton, WAL, migraciones
data/                   # JSONs + datos estaticos
assets/                 # Imagenes estaticas
  goetia_sigils/        # 72 sigilos canonicos (Wikimedia, PD)
  goetia_cards/         # 72 cartas (retrato + sigilo esquina sup. derecha)
  goetia_portraits_lebreton/  # 32 grabados originales Le Breton 1863 (PD)
  shem_firmas/          # 72 firmas hebreas sobre pergamino
tests/                  # 464+ tests
```

### Pipeline Goetia (72 cartas)

Cada demonio tiene una carta 1024x1536 con retrato + sigilo. El flujo:

1. **`scripts/download_sigils.py`** — 72 sigilos Goetia 1904 desde Wikimedia Commons.
2. **`scripts/download_lebreton.py`** — 32 planchas Le Breton del Dictionnaire Infernal 1863 (Wikimedia, dominio publico).
3. **`scripts/remove_gemini_watermark.py`** — limpia la marca de agua ◇ de Gemini en las 40 imagenes IA regeneradas (parche de pergamino muestreado, sin IA).
4. **`scripts/rename_goetia_regen.py`** — normaliza nomenclatura a `NN_Nombre.png`.
5. **`scripts/normalize_goetia_portraits.py`** — unifica las 72 a 1024x1536 (2:3 vertical) con textura de pergamino homogenea.
6. **`scripts/compose_goetia_cards.py`** — pega el sigilo canonico en esquina superior derecha (multiply blend).
7. **`scripts/generate_shem_firmas.py`** — 72 firmas hebreas del Shem sobre pergamino (Times New Roman, PIL).

Verificacion empirica contra el PDF de Gallica BNF: Le Breton ilustro 35 de los 72 Goetia en el DI 1863. Se usan 32 auténticos + 40 IA regeneradas por fidelidad a Mathers (algunos Le Breton son bustos minimalistas o interpretan iconografia que Goetia describe distinto).

## Politica de uso

El bot **NO impone limites de uso**: ni cooldown, ni cuota diaria, ni tope mensual de gasto, ni rate limit de onboarding, ni cap en longitud de pregunta. Decision consciente — cualquier proteccion contra abuso se hace via Telegram (admins del grupo) o reintroduciendo limites en `bot/limits.py` (es un stub no-op preparado para ello).

Lo que SI sigue activo (no son limites de usuario, son protecciones tecnicas):

- `QUEUE_TIMEOUT` (45 s) para no bloquear el chat indefinidamente si la API no responde.
- `MAX_CONCURRENT_API` (3) — semaforo asyncio para no saturar la API ni Telegram.
- `request_in_progress` por usuario — un usuario no puede lanzar dos lecturas en paralelo.
- `FEEDBACK_EXPIRY_DAYS` (7) — los botones 👍/👎 expiran.

## Privacidad y seguridad

- **Onboarding en DM**: `/consulta` en grupo redirige a DM via deep link (`t.me/bot?start=onboarding`). Datos personales (fecha, hora, ciudad, nombre) se recogen en privado.
- **Deep link whitelist**: solo 3 parametros validos (`onboarding`, `update_profile`, `set_fullname`). Set estricto, no regex. Cualquier otro parametro se ignora.
- **Middleware DM**: solo `/start`, `/startoraculo`, `/cancelaroraculo` permitidos en DM. Tiradas bloqueadas en privado.
- **Sanitizacion XML**: cualquier campo de usuario inyectado en el prompt LLM (alias, full_birth_name, birth_city, pregunta) se neutraliza para que no pueda forzar el cierre/apertura de tags estructurales del prompt. Ver `service/sanitization.py`.
- **HTML escaping**: el output del LLM pasa por `html.escape` antes de aplicar marcadores `[[T]]` `[[C]]`. Imposible inyectar HTML al chat.
- **SQL column whitelist**: `update_profile()` solo acepta 11 columnas predefinidas (`frozenset`). Rechaza cualquier otra con `ValueError`.
- **Cascade manual en `/borrarme`**: como `PRAGMA foreign_keys=OFF` (necesario para guests), `delete_user` borra explicitamente de `users`, `usage_log` y `feedback` para no dejar huerfanos (RGPD).
- **User ID real**: toda operacion de identidad usa `update.effective_user.id` o `query.from_user.id`, nunca `user_data`.
- **SQL parameterizado**: todas las queries usan `?` placeholders. Zero concatenacion de strings.
- **Anti-ajeno reforzado**: callbacks sin `reply_to_message` solo los acepta el admin (no fail-open silencioso).
- **Sin secrets en logs**: errores de API solo loguean `status_code`, nunca API keys ni excepciones completas.

## Extended thinking

Activado en cada llamada via `thinking={"type": "enabled", "budget_tokens": N}`. Effort por modo (configurable en `config.py` o `.env`):

| Effort | budget_tokens | Modos |
|---|---|---|
| `low` | 2000 | tarot 1 carta, tirada del dia, runas Odin, geomancia 1 figura |
| `medium` | 5000 | tarot 3 cartas, si/no, cruz simple, runas Nornas, numerologia, oraculo |
| `high` | 10000 | Cruz Celta, herradura, relacion, estrella, runas Cruz/Cinco/Siete, I Ching, escudo, natales, demonio, angel |

`max_tokens` enviado a la API es `MAX_TOKENS_<MODO> + budget_tokens` para que el output visible no se vea recortado por el thinking. `temperature=1` (requisito de la API con thinking activo). El parseo de respuesta filtra `ThinkingBlock` y solo concatena bloques `type=="text"`.

## Prompt caching

Aprovecha hasta 2 cache breakpoints simultaneos del SDK Anthropic 0.97:

1. `MASTER_SYSTEM_PROMPT` (~5k tokens, comun a todos los modos) — siempre cacheado.
2. Sub-prompt del modo (tarot/runas/iching/etc.) — cacheado por modo. Demonio/angel quedan inline porque su sub-prompt depende de la entidad consultada.

Anthropic cachea por prefijo, asi que el cache de MASTER se reutiliza al cambiar de modo. Llamadas consecutivas del mismo modo entran como `cache_read` (0.30 $/Mtoken) en vez de `fresh_input` (3.00 $/Mtoken). TTL 5 min (`ephemeral`).

## Decisiones de implementacion

- **kerykeion v5 cubre tropical Y vedica**: sidereal/Lahiri es nativo, no se necesita pyswisseph como dependencia separada.
- **Nakshatras y dashas (Vimshottari)**: calculo propio a partir de posicion lunar sidereal. Mahadasha calculada con dias exactos (no anos enteros) para evitar errores cerca de transiciones.
- **Runas vectoriales**: trazos Pillow sobre textura piedra procedural. Zero assets de fuentes.
- **Marcadores custom `[[T]]` `[[C]]`**: en vez de `##` y `**` (que Sonnet usa inconsistentemente).
- **NO retry manual** salvo `empty_response`: el SDK de Anthropic ya reintenta 2x en 429/500. Reintenta UNA vez si la respuesta llega vacia (problema conocido en lecturas densas con thinking).
- **System prompt estatico**: constante literal (no f-strings) para que el prompt caching funcione. Perfil del usuario se inyecta en el user message saneado contra inyeccion XML.
- **Guardrails minimos**: solo anti-jailbreak y proteccion de identidad (nunca revela que es IA). El oraculo responde a cualquier tema — amor, fertilidad, dinero, muerte, enemigos — sin restricciones ni disclaimers.
- **Personalidad Baphomet**: El Pezuñento es omnisciente — NUNCA dice "no se". Tono modulado segun contexto (humor acido para preguntas casuales, gravedad para dolor, autoridad para decisiones vitales). Todos los mensajes mantienen caracter, sin servilismo.
- **Deteccion dinamica de forum/topics**: el bot se adapta automaticamente a grupos con o sin hilos. Usa `chat.is_forum` para decidir si enviar `message_thread_id`. `ALLOWED_THREAD_ID` solo se comprueba en grupos forum.
- **Anti-ajeno en callbacks**: solo el usuario que inicio una tirada puede pulsar sus botones inline. Otros usuarios reciben "Esa consulta no es tuya". Cuando el callback no tiene `reply_to_message` para verificar, solo el admin pasa.
- **Geocoding multiples resultados**: ciudades homonimas (Valencia, Santiago...) muestran botones inline con hasta 5 opciones de Nominatim para que el usuario seleccione la correcta.
- **Smart selector**: `/tirartarot <pregunta>` analiza keywords (coste cero, sin API) y elige la tirada mas apropiada. Tambien disponible como boton en el menu.
- **Blockquote expandible**: todas las respuestas (tarot, runas, I Ching, geomancia, numerologia, natales, oraculo, bibliomancia, /ayudaoraculo) se muestran colapsadas con "Mostrar mas". Controlado por `frozenset` en config, desactivable globalmente con `USE_BLOCKQUOTE=false`.
- **Menu tarot con sub-categorias**: Rapidas / Completas / Especiales. Edita el mismo mensaje, sin spam en el chat.
- **Multi-mazo tarot**: Rider-Waite-Smith (PCS 1909, CC0, 300px) y Tarot de Marsella (Lequart ~1890, dominio publico, 800px). Selector de mazo → selector de variante → tirada. Prompts deck-aware con nomenclatura Marsella (La Papisa, El Papa, El Arcano sin Nombre, La Casa de Dios). Imagenes: 76 de TarotCaster (Wikimedia) + 2 Papisa/Papa de Wikimedia directas.
- **Timeout en preguntas pendientes**: flags `awaiting_*` guardan `time.time()` y expiran a los 5 minutos. Si el usuario no responde, el oraculo cierra la mesa y avisa in-character. Evita captura indefinida de texto.
- **`async with user_busy(user_id):`** en `bot/concurrency.py` libera al usuario incluso ante excepciones, sin try/finally repetido en handlers.
- **Split tag-aware**: cuando una respuesta excede 4096 chars, se corta sin romper tags HTML (`<b>`, `<i>`) entre chunks.

## Licencia

AGPL-3.0 — obligatorio por dependencias (kerykeion, pyswisseph).

El repo debe ser publico. Secretos en `.env` (en `.gitignore`).
