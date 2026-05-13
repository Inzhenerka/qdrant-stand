# Основы SQL и реляционных БД

## Сценарий курса

Этот модуль построен на сквозном примере: датасет научной экспедиции в Антарктику первой половины XX века. Данные распределены по нескольким связанным таблицам:

- **`Person`** — список исследователей. Столбцы: `id`, `personal` (имя), `family` (фамилия). Например: `dyer`, `lake`, `roe`, `pb`.
- **`Site`** — точки сбора измерений. Столбцы: `name` (например, `DR-1`, `DR-3`, `MSK-4`), `lat`, `long`.
- **`Visited`** — посещения сайтов. Столбцы: `id` (идентификатор визита), `site`, `dated`.
- **`Survey`** — собственно измерения: `taken` (id визита), `person` (кто измерял), `quant` (тип величины: `rad` — радиация, `sal` — солёность, `temp` — температура), `reading` (значение).

Реальные данные с пропусками, ошибками и аномалиями — нормальная учебная среда для понимания, зачем нужна реляционная модель и SQL.

## Эпизод 1. SELECT и FROM — выборка данных

Самая частая операция SQL — выборка строк из таблицы:

```sql
SELECT * FROM Person;
```

`*` означает «все столбцы». Если нужны конкретные:

```sql
SELECT family, personal FROM Person;
```

Несколько важных особенностей синтаксиса:

- SQL **регистронезависим** для ключевых слов и имён: `SELECT`, `select`, `Select` — одно и то же. Принято писать ключевые слова заглавными буквами для читаемости.
- Сами **данные** регистрозависимы: `'Lake'` и `'lake'` — разные строки.
- Каждая команда заканчивается точкой с запятой `;`.
- **Порядок строк** в результате не гарантирован, если не задана сортировка.

## Эпизод 2. ORDER BY и DISTINCT

Сортировка результата:

```sql
SELECT * FROM Person ORDER BY family;
SELECT * FROM Site ORDER BY lat DESC;
SELECT * FROM Survey ORDER BY taken, quant;       -- по двум столбцам
```

Уникальные значения столбца:

```sql
SELECT DISTINCT quant FROM Survey;       -- какие типы измерений вообще есть
SELECT DISTINCT site, dated FROM Visited;
```

## Эпизод 3. WHERE — фильтрация

`WHERE` отбирает строки по условиям:

```sql
SELECT * FROM Visited WHERE site = 'DR-1';
SELECT * FROM Visited WHERE site = 'DR-1' AND dated < '1930-01-01';
SELECT * FROM Survey WHERE quant = 'sal' AND person = 'lake';
```

Логические операторы — `AND`, `OR`, `NOT`. При сложных условиях используйте круглые скобки, чтобы избежать неоднозначности приоритетов.

Принадлежность списку — `IN`:

```sql
SELECT * FROM Survey WHERE person IN ('lake', 'roe');
```

Шаблоны строк — `LIKE` с подстановочным символом `%` (любое число символов):

```sql
SELECT * FROM Visited WHERE site LIKE 'DR%';      -- все сайты, начинающиеся на DR
```

Диапазон — `BETWEEN`:

```sql
SELECT * FROM Survey WHERE reading BETWEEN 0.0 AND 1.0;
```

**Важно.** `WHERE` работает построчно по исходным данным. В нём можно использовать столбцы, которых нет в `SELECT` — например, отбирать по дате, а возвращать только сайт.

## Эпизод 4. Вычисления в SELECT

В `SELECT` можно не только выбирать, но и вычислять новые значения:

```sql
SELECT 1.05 * reading FROM Survey WHERE quant = 'rad';
SELECT taken, round(reading, 2) FROM Survey WHERE quant = 'sal';
SELECT personal || ' ' || family FROM Person;     -- конкатенация строк
```

Псевдоним столбца — через `AS`:

```sql
SELECT 1.05 * reading AS adjusted_radiation FROM Survey WHERE quant = 'rad';
```

## Эпизод 5. Пропущенные значения (NULL)

В реальных данных часть значений отсутствует. SQL обозначает это специальным значением `NULL`. Особенность: **любая операция с `NULL` даёт `NULL`** — это «неопределённое», а не «пусто».

```sql
SELECT * FROM Visited WHERE dated < '1930-01-01';
-- Строки, где dated равно NULL, не попадут — даже если они «явно раньше».
```

Проверять `NULL` нужно специальными операторами `IS NULL` и `IS NOT NULL`, а не `=`:

```sql
SELECT * FROM Visited WHERE dated IS NULL;
SELECT * FROM Visited WHERE dated IS NOT NULL;
```

Это одна из самых частых причин неправильных запросов у новичков: написал `WHERE x != 5` и удивился, почему строки с `NULL` тоже не попадают в результат. Они и не должны — `NULL != 5` — это не `TRUE`, это `NULL`.

## Эпизод 6. Агрегация

Агрегатные функции принимают набор строк и возвращают одно значение:

```sql
SELECT min(dated) FROM Visited;                              -- 1927-02-08
SELECT max(dated) FROM Visited;                              -- 1932-03-22
SELECT count(*) FROM Survey;                                 -- общее количество
SELECT count(reading) FROM Survey WHERE quant = 'sal';       -- 9
SELECT sum(reading) FROM Survey WHERE quant = 'sal';         -- 64.83
SELECT avg(reading) FROM Survey WHERE quant = 'sal';         -- 7.20
```

Агрегатные функции **игнорируют `NULL`** — это удобно для неполных данных.

## Эпизод 7. GROUP BY и HAVING

Часто агрегат нужен **по группам**:

```sql
SELECT person, count(reading), round(avg(reading), 2)
FROM Survey
WHERE quant = 'rad'
GROUP BY person;
```

Этот запрос возвращает по одной строке на каждого исследователя с количеством его измерений радиации и средним значением. Группировка возможна и по нескольким полям:

```sql
SELECT person, quant, count(reading)
FROM Survey
GROUP BY person, quant;
```

**Тонкий момент.** `WHERE` применяется к строкам **до** группировки, а `HAVING` — к группам **после**. Если нужно отфильтровать по агрегату — это `HAVING`, не `WHERE`:

```sql
SELECT person, avg(reading) AS mean_rad
FROM Survey
WHERE quant = 'rad'
GROUP BY person
HAVING mean_rad > 5.0;
```

## Эпизод 8. JOIN — связывание таблиц

Реляционная модель распределяет данные по нескольким таблицам, чтобы избежать дублирования. Чтобы получить связанную картинку, таблицы соединяют через `JOIN`.

`JOIN` сам по себе создаёт **декартово произведение** — каждая строка одной таблицы комбинируется с каждой строкой другой. Это редко то, что нужно. Условие связывания задаётся через `ON`:

```sql
SELECT Site.lat, Site.long, Visited.dated
FROM Site
JOIN Visited ON Site.name = Visited.site;
```

Так мы соединяем сайты с их посещениями: для каждого визита получаем координаты сайта.

Несколько JOIN можно цеплять подряд. Получим тип измерения и значение вместе с координатами сайта и датой:

```sql
SELECT Site.lat, Site.long, Visited.dated, Survey.quant, Survey.reading
FROM Site
JOIN Visited ON Site.name = Visited.site
JOIN Survey ON Visited.id = Survey.taken;
```

**Ключи.** Чтобы такие связи работали корректно, в каждой таблице должны быть:

- **Первичный ключ (primary key)** — поле, уникально идентифицирующее строку. Например, `Person.id`, `Site.name`, `Visited.id`.
- **Внешний ключ (foreign key)** — поле, ссылающееся на первичный ключ другой таблицы. Например, `Survey.person` ссылается на `Person.id`, `Survey.taken` ссылается на `Visited.id`, `Visited.site` ссылается на `Site.name`.

БД сама проверяет, что внешние ключи указывают на существующие записи — это гарантирует целостность данных.

Типы JOIN:

- **`INNER JOIN`** (или просто `JOIN`) — только строки, у которых есть пара в обеих таблицах.
- **`LEFT JOIN`** — все строки из левой таблицы; для не имеющих пары в правой — `NULL` справа.
- **`RIGHT JOIN`** — наоборот.
- **`FULL OUTER JOIN`** — все строки из обеих, с `NULL`-ами там, где пары нет.

## Эпизод 9. Создание и изменение данных

SQL умеет не только читать, но и менять данные:

```sql
INSERT INTO Person (id, personal, family)
VALUES ('skol', 'Skywalker', 'Lars');

UPDATE Site SET lat = -47.55 WHERE name = 'DR-1';

DELETE FROM Person WHERE id = 'skol';
```

**Важнейшее правило.** `UPDATE` и `DELETE` без `WHERE` тронут **все** строки таблицы. Перед запуском на боевой БД сначала прогоните то же `WHERE` через `SELECT` и убедитесь, что отбираются именно те строки.

## Эпизод 10. Создание таблиц

```sql
CREATE TABLE Person (
    id TEXT PRIMARY KEY,
    personal TEXT NOT NULL,
    family TEXT NOT NULL
);

CREATE TABLE Survey (
    taken INTEGER NOT NULL,
    person TEXT,
    quant TEXT NOT NULL,
    reading REAL,
    FOREIGN KEY (taken) REFERENCES Visited(id),
    FOREIGN KEY (person) REFERENCES Person(id)
);
```

Ключевые модификаторы:

- `PRIMARY KEY` — первичный ключ.
- `NOT NULL` — поле обязательно для заполнения.
- `UNIQUE` — значения не могут повторяться.
- `DEFAULT <значение>` — значение по умолчанию.
- `CHECK (условие)` — ограничение целостности.
- `FOREIGN KEY ... REFERENCES ...` — внешний ключ.

## Эпизод 11. Индексы и транзакции

Если по столбцу часто идёт фильтрация или сортировка — заведите **индекс**:

```sql
CREATE INDEX idx_survey_quant ON Survey(quant);
```

Индексы ускоряют `SELECT`, но замедляют `INSERT`/`UPDATE` и занимают место. Первичные ключи и `UNIQUE`-поля индексируются автоматически.

**Транзакции** — способ объединить несколько изменений как одно атомарное действие («всё или ничего»):

```sql
BEGIN TRANSACTION;
UPDATE accounts SET balance = balance - 100 WHERE id = 1;
UPDATE accounts SET balance = balance + 100 WHERE id = 2;
COMMIT;            -- зафиксировать
-- или: ROLLBACK; -- откатить, как будто ничего не было
```

## Эпизод 12. SQL из Python

Стандартная библиотека Python содержит модуль `sqlite3` — встроенную БД SQLite, которая хранит данные в одном файле без отдельного сервера:

```python
import sqlite3

conn = sqlite3.connect("survey.db")
cursor = conn.cursor()

cursor.execute("SELECT * FROM Person WHERE id = ?", ("dyer",))
for row in cursor.fetchall():
    print(row)

conn.close()
```

**Никогда не подставляйте значения в запрос через f-string** или конкатенацию — это уязвимость SQL-инъекций. Используйте параметры через `?` (или `%s` в других драйверах), как в примере выше. БД сама подставит значения безопасно.

Для более сложных проектов вместо ручных SQL применяют ORM-библиотеки — **SQLAlchemy**, **Django ORM**: они генерируют SQL из объектных моделей и делают код переносимым между разными СУБД.

## Что дальше

С базовым SQL у вас есть инструмент для работы с любыми структурированными данными — журналами, расписаниями, банками вопросов, логами. В сочетании с `pandas` (для анализа), `pytest` (для тестов запросов) и Git (для версионирования миграций) — это полный набор для построения прикладных систем.
