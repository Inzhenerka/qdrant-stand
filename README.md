# qdrant-stand

Учебный стенд Qdrant с предзапечённой read-only коллекцией для практик по RAG.

Векторизация корпусов происходит на этапе `docker build`. Финальный образ — обычный `qdrant/qdrant` с уже залитыми коллекциями внутри. После запуска контейнер слушает порт **6333** и сразу раздаёт коллекции. Студентам выдаётся `read_only_api_key`, поэтому запись им заблокирована.

## Коллекции

Каждая подпапка в `corpus/` — отдельный корпус и отдельная коллекция Qdrant. Имя коллекции = имя подпапки. Сейчас в стенде:

| Имя коллекции | Источник | Тексты |
|---|---|---|
| `ural_corpus` | `corpus/ural_corpus/` | Уральский краеведческий корпус (3 документа из edu-librarian) |

Чтобы добавить новый корпус — создать `corpus/<новое_имя>/` с `manifest.yml` и `.txt` файлами, пересобрать образ.

## Параметры всех коллекций

| Параметр | Значение |
|---|---|
| Размерность векторов | `1536` |
| Distance | `Cosine` |
| Модель эмбеддингов (для query) | `text-embedding-3-small` |
| `base_url` эмбеддера | `https://llm.inzhenerka-cloud.com/` |

Студенты обязаны эмбедить запросы той же моделью и через тот же `base_url`, иначе векторы окажутся в другом пространстве и поиск даст мусор.

## Сборка

Нужен `OPENAI_API_KEY` (для прохождения через `https://llm.inzhenerka-cloud.com/`):

```powershell
$env:OPENAI_API_KEY = "sk-..."
docker compose build
docker compose up -d
```

## Подключение со стороны студента

```python
from qdrant_client import QdrantClient
from langchain_openai import OpenAIEmbeddings

client = QdrantClient(url="http://<stand-host>:6333", api_key="student")

embedder = OpenAIEmbeddings(
    model="text-embedding-3-small",
    base_url="https://llm.inzhenerka-cloud.com/",
    dimensions=1536,
)

query_vec = embedder.embed_query("кто такие Демидовы?")
hits = client.search(collection_name="ural_corpus", query_vector=query_vec, limit=5)
for h in hits:
    print(h.score, h.payload["title"], h.payload["chunk_id"])
```

## Доступы

| Ключ | Кому | Права |
|---|---|---|
| `student` (env `QDRANT__SERVICE__READ_ONLY_API_KEY`) | Студенты | `search`, `scroll`, `retrieve`, `GET /collections/*` |
| `admin-rotate-me` (env `QDRANT__SERVICE__API_KEY`) | Преподаватели | Все операции |

Оба ключа задаются как **runtime env-переменные** контейнера — это переопределяет дефолты из `ENV` в [Dockerfile](Dockerfile) без пересборки.

**Coolify** (рекомендуется для прода): Application → Environment Variables:

```
QDRANT__SERVICE__API_KEY=<длинный случайный, например openssl rand -hex 32>
QDRANT__SERVICE__READ_ONLY_API_KEY=student
```

**Локально** (docker-compose) — через переменные шелла, [docker-compose.yml](docker-compose.yml) их подхватывает:

```powershell
$env:QDRANT_API_KEY = "$(openssl rand -hex 32)"
$env:QDRANT_READ_ONLY_API_KEY = "student"
docker compose up -d
```

Без переопределения локально работает дефолт `admin-rotate-me` — он зашит в Dockerfile только чтобы стенд запускался при `docker run` без env, **не используйте его в проде**.

## CI/CD: GitHub Actions → GHCR → Coolify

В [.github/workflows/deploy-image.yml](.github/workflows/deploy-image.yml) лежит workflow, который на push в `main` (или вручную через workflow_dispatch) вызывает reusable `Inzhenerka/ci-workflows/.github/workflows/deploy_image.yml@main`:

1. Билдит образ через Buildx с кешем в `type=gha`.
2. Пушит в GHCR: `ghcr.io/<owner>/<repo>:latest` + теги по ветке и sha.
3. Дёргает Coolify webhook — Coolify pull'ит новый образ и поднимает.

`OPENAI_API_KEY` передаётся в reusable через secret `build_args` — значение маскируется в логах workflow.

Нужны GitHub Secrets в репозитории:

| Secret | Что |
|---|---|
| `OPENAI_API_KEY` | Прокидывается как `--build-arg` в builder stage. В финальный образ не попадает. |
| `COOLIFY_WEBHOOK` | URL вида `https://coolify.../api/v1/deploy?uuid=...` |
| `COOLIFY_TOKEN` | API-токен Coolify (Bearer) |

## Настройка в Coolify

Тип приложения — **Docker Image** (не Dockerfile-from-git): Coolify будет тянуть готовый образ из GHCR после успешного build в GHA. Это быстрее и не требует доступа к `OPENAI_API_KEY` на стороне Coolify.

1. Создать приложение типа Docker Image, источник — `ghcr.io/<owner>/<repo>:latest`.
2. Если репозиторий private — настроить registry credentials в Coolify (PAT с правом `read:packages`).
3. В Environment задать `QDRANT__SERVICE__API_KEY` случайным значением. `QDRANT__SERVICE__READ_ONLY_API_KEY` оставить как `student` или задать своё.
4. Опубликовать порт `6333`.
5. Включить webhook в настройках приложения, скопировать webhook URL и token в GitHub Secrets.

`OPENAI_API_KEY` в финальном слое не сохраняется (ARG объявлен только в builder stage и не наследуется в `FROM qdrant/qdrant`), `docker history` его не покажет.

## Структура проекта

```
qdrant-stand/
├── Dockerfile              # multi-stage: builder поднимает qdrant и заливает коллекцию
├── docker-compose.yml      # локальная сборка/запуск
├── config.yml              # RAG-конфиг для ingest
├── pyproject.toml          # python-зависимости (uv)
├── ingest.py               # точка входа индексации
├── corpus/                 # каждая подпапка = отдельная коллекция
│   └── ural_corpus/        # manifest.yml + .txt файлы (один корпус)
└── stand/                  # минимальный пакет: чанкование, эмбеддер, vector-store
    ├── config.py
    └── rag/
```

Корпус и логика подготовки скопированы из [edu-librarian](../edu-librarian) (без FastAPI / agent / retriever — только pipeline до Qdrant).

## Локальная проверка

```powershell
# Коллекция раздаётся студентам
curl -H "api-key: student" http://localhost:6333/collections
curl -H "api-key: student" http://localhost:6333/collections/ural_corpus

# Запись заблокирована
curl -X DELETE -H "api-key: student" http://localhost:6333/collections/ural_corpus
# -> 403 Forbidden

# Без ключа
curl http://localhost:6333/collections
# -> 401 Unauthorized
```
