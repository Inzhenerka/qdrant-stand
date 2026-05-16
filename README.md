# qdrant-stand

Учебный стенд Qdrant с предзапечёнными read-only коллекциями для практик по RAG.

Векторизация корпусов происходит на этапе `docker build`. Финальный образ — обычный `qdrant/qdrant` с уже залитыми
коллекциями внутри. После запуска контейнер слушает порт **6333** и сразу раздаёт коллекции. Студентам выдаётся
`read_only_api_key`, поэтому запись им заблокирована.

## Коллекции

Каждая подпапка в `corpus/` — отдельный корпус и отдельная коллекция Qdrant. Имя коллекции = имя подпапки. Сейчас в
стенде:

| Имя коллекции | Источник              | Содержание                                                              |
|---------------|-----------------------|-------------------------------------------------------------------------|
| `ural_corpus` | `corpus/ural_corpus/` | Уральский краеведческий корпус (3 документа конца XIX — начала XX века) |
| `it_corpus`   | `corpus/it_corpus/`   | Вводный IT-курс: Python, Git, Shell, Pandas, тестирование, SQL          |

Чтобы добавить новый корпус — создайте `corpus/<новое_имя>/` с `manifest.yml` и текстовыми файлами, пересоберите образ.

## Параметры всех коллекций

| Параметр             | Значение                            |
|----------------------|-------------------------------------|
| Размерность векторов | `1536`                              |
| Distance             | `Cosine`                            |
| Модель эмбеддингов   | `text-embedding-3-small`            |
| `base_url` эмбеддера | `https://llm.inzhenerka-cloud.com/` |

Студенты должны эмбедить запросы той же моделью и через тот же `base_url`, иначе векторы окажутся в другом пространстве
и поиск даст мусор.

## Сборка

Для сборки нужен `OPENAI_API_KEY` (используется один раз при индексации, в финальный образ не попадает):

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

query_vec = embedder.embed_query("что такое git rebase и чем отличается от merge")
hits = client.search(collection_name="it_corpus", query_vector=query_vec, limit=5)
for h in hits:
    print(h.score, h.payload["title"], h.payload["chunk_id"])
```

## Доступы

| Ключ                                                 | Кому     | Права                                                |
|------------------------------------------------------|----------|------------------------------------------------------|
| `student` (env `QDRANT__SERVICE__READ_ONLY_API_KEY`) | Студенты | `search`, `scroll`, `retrieve`, `GET /collections/*` |
| `admin-rotate-me` (env `QDRANT__SERVICE__API_KEY`)   | Админ    | Все операции                                         |

Оба ключа задаются как **runtime env-переменные** контейнера — это переопределяет дефолты из `ENV`
в [Dockerfile](Dockerfile) без пересборки.

**В проде** мастер-ключ нужно заменить на длинный случайный (`openssl rand -hex 32`) и задать через переменные окружения
сервиса:

```
QDRANT__SERVICE__API_KEY=<длинный случайный>
QDRANT__SERVICE__READ_ONLY_API_KEY=student
```

**Локально** (docker-compose) — через переменные шелла, [docker-compose.yml](docker-compose.yml) их подхватывает:

```powershell
$env:QDRANT_API_KEY = "$(openssl rand -hex 32)"
$env:QDRANT_READ_ONLY_API_KEY = "student"
docker compose up -d
```

Без переопределения локально работает дефолт `admin-rotate-me` — он зашит в Dockerfile только чтобы стенд запускался при
`docker run` без env, **не используйте его в проде**.

## CI/CD

В [.github/workflows/deploy-image.yml](.github/workflows/deploy-stand.yml) лежит workflow, который на push в `main` (или
вручную через workflow_dispatch):

`OPENAI_API_KEY` передаётся в build как secret — значение маскируется в логах workflow и не сохраняется в финальном слое
образа.

Требуемые GitHub Secrets:

| Secret            | Назначение                                      |
|-------------------|-------------------------------------------------|
| `OPENAI_API_KEY`  | Прокидывается как `--build-arg` в builder stage |
| `COOLIFY_WEBHOOK` | URL webhook'а деплоя                            |
| `COOLIFY_TOKEN`   | Bearer-токен для webhook'а                      |

## Локальная проверка

```powershell
# Коллекции раздаются студентам
curl -H "api-key: student" http://localhost:6333/collections
curl -H "api-key: student" http://localhost:6333/collections/it_corpus

# Запись заблокирована
curl -X DELETE -H "api-key: student" http://localhost:6333/collections/it_corpus
# -> 403 Forbidden

# Без ключа
curl http://localhost:6333/collections
# -> 401 Unauthorized
```
