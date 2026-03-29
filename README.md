# El Oraculo de los Sortilegios

Bot de Telegram para el grupo **La Taberna de los Sortilegios** (~2,600 miembros). Ofrece lecturas de tarot (Rider-Waite y Marsella), runas, I Ching, geomancia, numerologia y cartas natales, impulsado por Claude Sonnet 4.6 de Anthropic.

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
| `/bibliomancia` | Textos sagrados | Biblia, Coran, Gita, Evangelio de Tomas |
| `/consulta` | Registro | Redirige a DM para onboarding privado |
| `/startoraculo` | Presentacion | Intro del oraculo en grupo |
| `/ayudaoraculo` | Ayuda | Lista de todos los comandos |
| `/miperfil` | Perfil | Ver datos registrados |
| `/actualizarperfil` | Perfil | Redirige a DM para actualizar hora/ciudad |
| `/borrarme` | Perfil | Eliminar perfil y historial |
| `/cancelaroraculo` | Control | Cancelar operacion en curso |

## Stack tecnico

| Componente | Tecnologia |
|---|---|
| Lenguaje | Python 3.12+ |
| Framework Telegram | python-telegram-bot 22.7 |
| IA | Anthropic API (Claude Sonnet 4.6) via AsyncAnthropic |
| Modelo | `claude-sonnet-4-6` con adaptive thinking |
| Validacion | pydantic 2.12 + pydantic-settings 2.13 |
| Base de datos | SQLite3 + aiosqlite 0.22 (WAL mode) |
| Astrologia | kerykeion 5.12 (tropical + sidereal Lahiri nativo) |
| Geocoding | geopy 2.4 (Nominatim) |
| Timezone | timezonefinder 8.2 + zoneinfo |
| Imagenes | Pillow 12.1 |
| Aleatoriedad | random.SystemRandom |
| Logging | loguru 0.7 |
| Testing | pytest 9.0 + pytest-asyncio 1.3 |

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
pip install -r requirements.txt
```

### Configuracion

```bash
cp .env.example .env
# Editar .env con valores reales
```

Variables obligatorias en `.env`: `BOT_TOKEN`, `ANTHROPIC_API_KEY`, `ALLOWED_CHAT_ID`, `ADMIN_USER_ID`.

Todas las demas variables tienen defaults razonables. Ver `.env.example` para la lista completa (47 variables incluyendo EFFORT_* y MAX_TOKENS_* por modo).

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
tests/                  # 367+ tests
```

## Limites de uso

- 5 tiradas diarias (tarot + runas + iching + geomancia pool)
- 2 numerologia, 1 natal, 3 oraculo por dia
- 60s cooldown entre consultas
- 200 chars max por pregunta
- Spending limit $25/mes
- 3 semaforo concurrente API (configurable)

## Privacidad y seguridad

- **Onboarding en DM**: `/consulta` en grupo redirige a DM via deep link (`t.me/bot?start=onboarding`). Datos personales (fecha, hora, ciudad, nombre) se recogen en privado.
- **Deep link whitelist**: solo 3 parametros validos (`onboarding`, `update_profile`, `set_fullname`). Set estricto, no regex. Cualquier otro parametro se ignora.
- **Rate limit DM**: max 3 intentos de onboarding por user_id por hora.
- **Middleware DM**: solo `/start`, `/startoraculo`, `/cancelaroraculo` permitidos en DM. Tiradas bloqueadas en privado.
- **Anti-command injection**: comandos de tirada durante flujo DM se ignoran con mensaje "termina primero".
- **SQL column whitelist**: `update_profile()` solo acepta 11 columnas predefinidas (`frozenset`). Rechaza cualquier otra con `ValueError`.
- **User ID real**: toda operacion de identidad usa `update.effective_user.id` o `query.from_user.id`, nunca `user_data`.
- **SQL parameterizado**: todas las queries usan `?` placeholders. Zero concatenacion de strings.
- **Sin secrets en logs**: errores de API solo loguean `status_code`, nunca API keys ni excepciones completas.

## Adaptive thinking (Sonnet 4.6)

El modelo usa `thinking: {"type": "adaptive", "effort": effort}` con effort configurable por modo:

| Effort | Modos |
|---|---|
| `low` | tarot 1 carta, tirada dia, runas Odin, geomancia 1 figura |
| `medium` | tarot 3 cartas, si/no, cruz simple, runas Nornas, numerologia, oraculo |
| `high` | Cruz Celta, herradura, relacion, estrella, runas Cruz/Cinco/Siete, I Ching, escudo, natales |

Configurables via `EFFORT_*` en `.env` sin redeploy.

## Decisiones de implementacion

- **kerykeion v5 cubre tropical Y vedica**: sidereal/Lahiri es nativo, no se necesita pyswisseph como dependencia separada.
- **Nakshatras y dashas (Vimshottari)**: calculo propio a partir de posicion lunar sidereal.
- **Runas vectoriales**: trazos Pillow sobre textura piedra procedural. Zero assets de fuentes.
- **Marcadores custom `[[T]]` `[[C]]`**: en vez de `##` y `**` (que Sonnet usa inconsistentemente).
- **NO retry manual**: el SDK de Anthropic ya reintenta 2x automaticamente.
- **System prompt estatico**: constante literal (no f-strings) para que el prompt caching funcione. Perfil del usuario se inyecta en el user message.
- **Guardrails minimos**: solo anti-jailbreak y proteccion de identidad (nunca revela que es IA). El oraculo responde a cualquier tema — amor, fertilidad, dinero, muerte, enemigos — sin restricciones ni disclaimers.
- **Personalidad Baphomet**: El Pezuñento es omnisciente — NUNCA dice "no se". Tono modulado segun contexto (humor acido para preguntas casuales, gravedad para dolor, autoridad para decisiones vitales). Todos los mensajes mantienen caracter, sin servilismo.
- **Deteccion dinamica de forum/topics**: el bot se adapta automaticamente a grupos con o sin hilos. Usa `chat.is_forum` para decidir si enviar `message_thread_id`. `ALLOWED_THREAD_ID` solo se comprueba en grupos forum.
- **Anti-ajeno en callbacks**: solo el usuario que inicio una tirada puede pulsar sus botones inline. Otros usuarios reciben "Esas no son tus cartas".
- **Geocoding multiples resultados**: ciudades homonimas (Valencia, Santiago...) muestran botones inline con hasta 5 opciones de Nominatim para que el usuario seleccione la correcta.
- **Smart selector**: `/tirartarot <pregunta>` analiza keywords (coste cero, sin API) y elige la tirada mas apropiada. Tambien disponible como boton en el menu.
- **Blockquote expandible**: todas las respuestas (tarot, runas, I Ching, geomancia, numerologia, natales, oraculo, bibliomancia) se muestran colapsadas con "Mostrar mas". Controlado por `frozenset` en config, desactivable globalmente con `USE_BLOCKQUOTE=false`.
- **Menu tarot con sub-categorias**: Rapidas / Completas / Especiales. Edita el mismo mensaje, sin spam en el chat.

## Licencia

AGPL-3.0 — obligatorio por dependencias (kerykeion, pyswisseph).

El repo debe ser publico. Secretos en `.env` (en `.gitignore`).
