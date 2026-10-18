# job-hunt-agent

Un kit para buscar trabajo con agentes de IA, que corre completo en tu computadora con
[Claude Code](https://claude.com/claude-code). Pones tu CV y los agentes:

1. **Revisan tu CV** y lo reescriben con estándares ATS, en inglés y/o español, o te lo
   arman desde cero platicando contigo.
2. **Arman tu perfil de búsqueda**: títulos de puesto, seniority, salario, modalidad,
   ciudades y plataformas, a partir de tu CV y de lo que les digas.
3. **Buscan y aplican** en LinkedIn, Indeed, OCC, Computrabajo, Get on Board, Torre y otras,
   usando tu propio navegador y tus sesiones.
4. **Revisan tu correo** y registran respuestas, rechazos, entrevistas y pruebas.
5. **Lo guardan todo** en una base SQLite local, con un dashboard que muestra tus pendientes,
   tu agenda de entrevistas y cuál es tu "plataforma MVP" (la que más convierte).

Sin servidores, sin logins y sin cuentas nuevas: todo vive en tu máquina.

## ⚠️ Antes de usarlo

- Los agentes **envían aplicaciones reales a tu nombre**.
- Automatizar postulaciones **puede ir contra los términos de uso** de LinkedIn, Indeed y
  otros sitios. Tu cuenta podría ser limitada o suspendida. Úsalo con moderación.
- Los agentes no inventan experiencia, pero **tú eres responsable** de revisar tu CV, tu
  perfil y lo que se envía.
- Nunca resuelven CAPTCHAs, nunca crean cuentas, nunca meten datos de pago y nunca
  responden mensajes por ti.

`/setup` te muestra este aviso y no continúa sin tu aceptación explícita.

## Requisitos

- [Claude Code](https://claude.com/claude-code) con una suscripción de Claude.
- La extensión [Claude in Chrome](https://claude.ai/chrome), conectada, con tus sesiones
  iniciadas en las plataformas que quieras usar. Solo se necesita para buscar, aplicar y
  revisar el correo.
- Python 3.9 o superior (solo biblioteca estándar, sin `pip install`).
- Google Chrome o Chromium para generar los PDFs del CV.

## Empezar

```bash
git clone <url-del-repo> job-hunt-agent
cd job-hunt-agent
# opcional: copia tu CV actual (PDF, DOCX o .md) a me/cv_original/
claude
```

Dentro de Claude Code:

```
/setup
```

`/setup` te guía paso a paso: aviso, requisitos, CV, perfil y base de datos. Si lo cortas,
al correrlo de nuevo sigue donde se quedó.

## Comandos

| Comando | Qué hace |
|---|---|
| `/setup` | Configuración inicial completa. |
| `/cv-review` | Revisa el CV de `me/cv_original/`, lo pasa a Markdown con estándares ATS y genera los PDFs. |
| `/cv-interview` | Te entrevista y arma tu CV desde cero. |
| `/profile` | Crea o actualiza `me/profile.yml` (títulos, salario, modalidad, plataformas...). |
| `/hunt` | Busca en paralelo en las plataformas activas y aplica una por una. `/hunt linkedin occ` para elegir plataformas. |
| `/check-email` | Lee tu correo y registra respuestas, rechazos, entrevistas y pruebas. |
| `/dashboard` | Abre el dashboard en http://127.0.0.1:8765. |

## Cómo funciona

```
/hunt
 ├─ platform-search (LinkedIn) ─┐
 ├─ platform-search (Indeed)  ──┼─→ candidatas en la base (aplicar / descartar, con motivo)
 └─ platform-search (OCC)     ──┘
        ↓
    applier (uno solo, en orden) ─→ aplica, guarda respuestas de screening y etapas
        ↓
    preguntas que solo tú puedes responder ─→ te las hace en el chat y retoma
```

- **Skills** (`.claude/skills/`): los comandos que platican contigo.
- **Agentes** (`.claude/agents/`): trabajan en segundo plano y no te hacen preguntas;
  lo que necesite tu respuesta te lo devuelven.
- **Plataformas** (`platforms/*.md`): una ficha por sitio, con cómo buscar, cómo aplicar y
  los problemas conocidos. Agregar un sitio nuevo es escribir un `.md`
  (`platforms/_template.md`). Los agentes actualizan la ficha cuando un sitio cambia.
- **Tracker** (`tracker/`): SQLite con aplicaciones, historial, etapas del proceso,
  pendientes, respuestas de screening, candidatas y corridas. Los agentes lo usan solo a
  través de `tracker/tracker.py` (`python3 tracker/tracker.py -h`).

## Tus datos

Todo lo personal vive en `me/`, que git ignora:

```
me/
├── cv_original/        tu CV original (nunca se modifica)
├── cv_en.md, cv_es.md  tu CV ATS (la fuente de verdad)
├── cv_en.pdf, cv_es.pdf
├── profile.yml         tu perfil de búsqueda
└── data/
    ├── job_search.db   la base
    └── backup/         copia automática después de cada escritura
```

Después de regenerar tu CV, súbelo también a los espacios de CV que guarda cada plataforma
(LinkedIn, Indeed, OCC...). Esas copias no se actualizan solas.

## Dashboard

```bash
python3 tracker/dashboard.py
```

Incluye "Qué me toca", la agenda de entrevistas y pruebas, los procesos activos con sus
etapas, la plataforma MVP con el ranking de plataformas por tasa de avance, la actividad
reciente y todas tus aplicaciones con filtros y paginación. Solo escucha en `127.0.0.1`.

## Contribuir

Lo más útil es mantener al día las fichas de `platforms/`: los sitios cambian seguido.
Agrega la fecha a cada nota.

## Licencia

[MIT](LICENSE)
