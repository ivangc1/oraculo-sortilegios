# El Oraculo de los Sortilegios

Bot de Telegram para el grupo **La Taberna de los Sortilegios** (~2,600 miembros). Ofrece lecturas de tarot, runas, I Ching, geomancia, numerologia y cartas natales, impulsado por Claude Sonnet 4.6 de Anthropic.

**@oraculo_sortilegios_bot** | Licencia: AGPL-3.0

## Modos disponibles

| Comando | Sistema | Variantes |
|---|---|---|
| `/tarot` | Tarot Rider-Waite | Una carta, Tres cartas, Cruz Celta |
| `/runa` | Runas Elder Futhark | Runa de Odin, Tres Nornas, Cruz Runica |
| `/iching` | I Ching (Wilhelm) | Hexagrama con/sin lineas mutables |
| `/geomancia` | Geomancia | Una figura, Escudo completo |
| `/numerologia` | Pitagorica | Informe completo, Compatibilidad |
| `/natal` | Carta natal tropical | Placidus (Whole Sign si lat >60) |
| `/vedica` | Carta natal vedica | Lahiri ayanamsa, Nakshatras, Dashas |
| `/oraculo` | Pregunta libre | Sonnet interpreta directamente |
| `/bibliomancia` | Textos sagrados | Biblia, Coran, Gita, Evangelio de Tomas |
| `/admins` | Directorio guardianes | Grid inline con bios |
| `/consulta` | Registro | Onboarding (alias, fecha, hora, ciudad) |
| `/startoraculo` | Presentacion | Intro del oraculo |
| `/ayudaoraculo` | Ayuda | Lista de todos los comandos |
| `/miperfil` | Perfil | Ver datos registrados |
| `/actualizarperfil` | Perfil | Actualizar hora o ciudad |
| `/borrarme` | Perfil | Eliminar perfil y historial |
| `/cancelar` | Control | Cancelar operacion en curso |

## Stack tecnico

| Componente | Tecnologia |
|---|---|
| Lenguaje | Python 3.12+ |
| Framework Telegram | python-telegram-bot 22.7 |
| IA | Anthropic API (Claude Sonnet 4.6) via AsyncAnthropic |
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
cp data/admins_private.example.json data/admins_private.json
# Editar con datos reales de los admins del grupo
```

Variables obligatorias en `.env`: `BOT_TOKEN`, `ANTHROPIC_API_KEY`, `ALLOWED_CHAT_ID`, `ADMIN_USER_ID`.

### Setup BotFather

1. Crear bot en BotFather, obtener token
2. `/setjoingroups` off
3. `/setcommands` con la lista de comandos
4. **NO tocar `/setprivacy`** (dejar privacy mode ON; ForceReply lo maneja)
5. Anadir bot al grupo, obtener chat_id via getUpdates

### Ejecucion

```bash
python -m bot.main          # Desarrollo (long polling)
sudo systemctl start bot-taberna  # Produccion (systemd)
```

### Tests

```bash
python -m pytest tests/ -v
```

Tests de natales con kerykeion se saltan en Windows (necesitan pyswisseph compilado). Se ejecutan en el VPS Linux.

## Estructura del proyecto

```
bot/                    # Capa 1: Telegram
  handlers/             # Handlers por modo
  main.py               # Entry point, signals, persistence
  config.py             # Settings (pydantic-settings)
  middleware.py          # Edits, DM, chat_id, membresia, migracion
service/                # Capa 2: Interpretacion
  anthropic_client.py   # AsyncAnthropic singleton, cache, coste real
  prompts/              # System + sub-prompts por modo
  calculators/          # Geocoding, timezone, natal, numerologia
generators/             # SystemRandom, sin repeticion
images/                 # Pillow: tarot, runas, hexagramas, geomancia
database/               # SQLite singleton, WAL, migraciones
data/                   # JSONs + datos estaticos
tests/                  # 293+ tests
```

## Limites de uso

- 5 tiradas diarias (tarot + runas + iching + geomancia pool)
- 2 numerologia, 1 natal, 3 oraculo por dia
- 60s cooldown entre consultas
- 200 chars max por pregunta
- Spending limit $25/mes

## Decisiones de implementacion

- **kerykeion v5 cubre tropical Y vedica**: sidereal/Lahiri es nativo, no se necesita pyswisseph como dependencia separada.
- **Nakshatras y dashas (Vimshottari)**: calculo propio a partir de posicion lunar sidereal.
- **Runas vectoriales**: trazos Pillow sobre textura piedra procedural. Zero assets de fuentes.
- **Marcadores custom `[[T]]` `[[C]]`**: en vez de `##` y `**` (que Sonnet usa inconsistentemente).
- **NO retry manual**: el SDK de Anthropic ya reintenta 2x automaticamente.

## Licencia

AGPL-3.0 — obligatorio por dependencias (kerykeion, pyswisseph).

El repo debe ser publico. Secretos en `.env` (en `.gitignore`).
