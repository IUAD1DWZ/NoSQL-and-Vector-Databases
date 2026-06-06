# Аналітична платформа для музичного стрімінгового сервісу на MongoDB Atlas

Цей проєкт реалізує навчальне завдання з NoSQL / MongoDB на основі Spotify Tracks Dataset. У межах роботи дані були завантажені в MongoDB Atlas, трансформовані з плоскої CSV-структури в документоорієнтовану схему, після чого для колекції були реалізовані запити, aggregation pipelines та аналіз індексів через `explain()`.

## Зміст

- [Мета проєкту](#мета-проєкту)
- [Використаний датасет](#використаний-датасет)
- [Структура репозиторію](#структура-репозиторію)
- [Налаштування оточення](#налаштування-оточення)
- [Частина 1 — Завантаження даних і схема](#частина-1--завантаження-даних-і-схема)
- [Частина 2 — Запити до даних](#частина-2--запити-до-даних)
- [Частина 3 — Аналітика через Aggregation Pipeline](#частина-3--аналітика-через-aggregation-pipeline)
- [Частина 4 — Індекси та оптимізація](#частина-4--індекси-та-оптимізація)
- [Висновок](#висновок)

## Мета проєкту

Мета проєкту — практично опрацювати документоорієнтовану модель MongoDB, навчитися працювати з вкладеними полями та масивами, будувати аналітичні aggregation pipelines і оптимізувати запити за допомогою compound indexes та `explain()`.

## Використаний датасет

У проєкті використано датасет **Spotify Tracks Dataset** з Kaggle. Він містить інформацію про треки, жанри, популярність, тривалість і набір аудіо-характеристик, зокрема `danceability`, `energy`, `valence`, `tempo` та інші.

## Структура репозиторію

```text
.
├── .env
├── README.MD
├── image.png
├── image-1.png
├── image-2.png
├── image-3.png
├── image-4.png
├── scripts/
│   ├── 01_load_data.py
│   └── 02_transform.js
├── queries/
│   ├── part2_queries.js
│   ├── part3_aggregations.js
│   └── part4_indexes.js
└── explain/
    ├── 1.txt
    ├── 2.txt
    └── 3.txt
```

## Налаштування оточення

### 1. MongoDB Atlas

Для виконання роботи використовується MongoDB Atlas. Для цього завдання достатньо безкоштовного кластера **M0 Shared**.

Порядок налаштування:

1. Зареєструватися в MongoDB Atlas.
2. Створити кластер.
3. Створити database user.
4. Додати власний IP у `Network Access`.
5. Скопіювати connection string формату `mongodb+srv://...`.

### 2. Файл `.env`

У корені цієї папки потрібно створити файл `.env`:

```env
MONGO_URI=mongodb+srv://user:password@cluster.mongodb.net/
```

### 3. Встановлення залежностей

Python-залежності, які використовуються у скрипті завантаження даних:

```txt
pandas
pymongo
tqdm
python-dotenv
kagglehub
```

Команда встановлення:

```bash
python3 -m pip install --user pandas pymongo tqdm python-dotenv kagglehub
```

### 4. Отримання датасету

У проєкті реалізовано два способи отримання CSV:

- використати локальний файл `dataset.csv`, якщо він уже є в корені проєкту;
- або автоматично завантажити датасет `maharshipandya/-spotify-tracks-dataset` через `kagglehub`.

### 5. Порядок запуску

```bash
set -a
source .env
set +a

python3 scripts/01_load_data.py
mongosh "$MONGO_URI/spotify" --file scripts/02_transform.js
mongosh "$MONGO_URI/spotify" --file queries/part2_queries.js
mongosh "$MONGO_URI/spotify" --file queries/part3_aggregations.js
mongosh "$MONGO_URI/spotify" --file queries/part4_indexes.js
```

## Частина 1 — Завантаження даних і схема

### Завантаження сирих даних

Скрипт `scripts/01_load_data.py`:

- підключається до бази `spotify`;
- очищає колекцію `tracks_raw`;
- зчитує CSV через `pandas`;
- приводить типи полів;
- видаляє рядки без `artists` або `track_name`;
- завантажує записи батчами в MongoDB.

Такий підхід робить повторний запуск ідемпотентним і зменшує ризик помилок при вставці великого обсягу даних.

### Трансформація схеми

Сирі CSV-дані мають плоску структуру, тому вони були трансформовані в нову колекцію `tracks` за допомогою Aggregation Pipeline.

Було виконано такі кроки:

1. Видалення старої колекції `tracks`.
2. Вибір тільки потрібних полів із `tracks_raw`.
3. Перетворення рядка `artists` на масив `artists` через розбиття по `;` і очищення пробілів.
4. Формування вкладеного об’єкта `audio_features`.
5. Обчислення `duration_sec`.
6. Обчислення `popularity_tier`.
7. Запис результату в `tracks` через `$out`.

### Підсумкова схема документа

Приклад структури документа в колекції `tracks`:

```json
{
  "_id": "ObjectId(...)",
  "track_id": "5SuOjkwjRWrPMVoIQDUJgsv",
  "album_name": "Comedy",
  "track_name": "Comedy",
  "popularity": 73,
  "duration_ms": 230666,
  "explicit": false,
  "track_genre": "acoustic",
  "artists": ["Gen Hoshino"],
  "audio_features": {
    "danceability": 0.676,
    "energy": 0.461,
    "loudness": -6.746,
    "speechiness": 0.143,
    "acousticness": 0.0322,
    "instrumentalness": 0.00000101,
    "liveness": 0.358,
    "valence": 0.715,
    "tempo": 87.917,
    "key": 1,
    "mode": 0,
    "time_signature": 4
  },
  "duration_sec": 230.7,
  "popularity_tier": "high"
}
```

### Чому `audio_features` винесено в окремий об’єкт

Поля `danceability`, `energy`, `tempo`, `valence`, `speechiness` та інші описують одну логічну групу характеристик, тому їх доцільно винести у вкладений об’єкт `audio_features`. Це робить схему більш читабельною та дозволяє відокремити метадані треку від аналітичних ознак.

Такий підхід вигідний, коли пов’язані поля часто використовуються разом у фільтрах і агрегаціях. Потенційний недолік з’являється тоді, коли вкладеність стає надто глибокою або якщо зовнішні системи очікують плоску структуру, але в цьому проєкті вкладення є помірним і виправданим.

### Чому `artists` зберігається як масив

Поле `artists` зберігається як масив, тому що один трек може мати кількох виконавців. Це природна форма представлення one-to-many зв’язку всередині документа.

Таке рішення значно спрощує подальші запити. Зокрема, можна використовувати `$unwind`, щоб працювати з кожним артистом окремо, рахувати кількість треків на виконавця, обчислювати середню популярність і будувати агрегації без додаткового парсингу рядка.

### `$out` і `$merge`

`$out` записує результат агрегації у вказану колекцію як новий повний набір даних. Це зручно тоді, коли потрібно повністю перебудувати результат трансформації.

`$merge` використовується тоді, коли потрібно не повністю замінити колекцію, а оновлювати або дописувати дані в уже існуючу collection. У цьому завданні логічніше використовувати саме `$out`, бо колекція `tracks` формується заново з `tracks_raw`.

## Частина 2 — Запити до даних

У частині 2 були реалізовані чотири запити до колекції `tracks`.

### 1. Треки для вечірки

Запит відбирає треки, які:

- мають `danceability > 0.7`;
- мають `energy > 0.7`;
- мають тривалість у межах від 180000 до 300000 мс.

У цьому запиті використовується фільтрація за вкладеними полями через dot notation.

### 2. Виконавці, у яких усі треки популярні

Для цього запиту використано:

- `$unwind`;
- `$group`;
- `$match`;
- `$project`;
- `$sort`;
- `$limit`.

Логіка запиту:

1. Розгорнути масив `artists`.
2. Згрупувати документи по артисту.
3. Порахувати `track_count`, `min_popularity`, `avg_popularity`.
4. Залишити тільки артистів із мінімум 3 треками і `min_popularity >= 60`.
5. Вивести топ-20.

### 3. Нетипові треки за темпом

У запиті використано:

- `$group` для агрегації по жанру;
- `$avg` для обчислення середнього `tempo`;
- `$stdDevPop` для population standard deviation.

Outlier визначався за правилом:

```text
tempo > avg_tempo + 2 * stdDevPop
```

### 4. Треки для фонової роботи

У запиті використано такі умови:

- `audio_features.loudness < -10`;
- `audio_features.speechiness < 0.1`;
- `audio_features.instrumentalness > 0.5`;
- `explicit = false`.

### Для чого використовується `$unwind`

`$unwind` перетворює масив у набір окремих документів — по одному документу на кожен елемент масиву. У цьому проєкті він потрібен насамперед для аналітики по виконавцях.

### Чим `$stdDevPop` відрізняється від `$stdDevSamp`

`$stdDevPop` рахує population standard deviation, тобто відхилення по всіх значеннях у групі. `$stdDevSamp` рахує sample standard deviation і застосовує поправку для вибірки. Для цього завдання використано саме `$stdDevPop`, бо в умові явно задано population standard deviation.

## Частина 3 — Аналітика через Aggregation Pipeline

### 1. Топ-10 виконавців за середньою популярністю

У pipeline використано:

- `$unwind` по `artists`;
- `$group` по імені артиста;
- `$avg` для `popularity`;
- `$match` для відсікання артистів із менш ніж 5 треками;
- `$sort` і `$limit`.

### 2. Розподіл треків за настроєм

Для класифікації настрою використано `$switch`. На основі `audio_features.valence` і `audio_features.energy` кожному треку було присвоєно категорію:

- `happy`;
- `angry`;
- `calm`;
- `sad`.

Порогові значення:

- `valence >= 0.5` і `energy >= 0.5` → `happy`;
- `valence < 0.5` і `energy >= 0.5` → `angry`;
- `valence >= 0.5` і `energy < 0.5` → `calm`;
- інакше → `sad`.

### 3. Найбільш танцювальний жанр

Треки були згруповані за `track_genre`, після чого по кожному жанру обчислювалися:

- `avg_danceability`;
- `avg_energy`;
- `avg_valence`;
- `track_count`.

Після цього жанри з кількістю треків менше 100 були відфільтровані, щоб зменшити вплив малих вибірок.

### Чому у запиті 1 обрано поріг 5 треків

Поріг у 5 треків зменшує вплив випадкових високих значень. Якщо знизити поріг до 1, у топ можуть потрапляти артисти з одним або двома дуже популярними треками, але така оцінка не буде репрезентативною.

Якщо ж підняти поріг до більше ніж 50 треків, результат суттєво звузиться, і в ньому залишаться лише дуже продуктивні виконавці з великим каталогом.

### Чому у запиті 3 використано поріг 100 треків на жанр

Фільтр `track_count >= 100` зменшує ризик того, що результат буде визначатися випадковими властивостями малих вибірок. Якщо знизити поріг до 50, у результат можуть потрапити вужчі жанри, і висновок стане менш статистично стабільним.

## Частина 4 — Індекси та оптимізація

У межах частини 4 було створено два compound indexes і проаналізовано їх вплив через `explain("executionStats")`.

### Створені індекси

На колекції `tracks` присутні такі індекси:

- `_id_` — стандартний індекс MongoDB, який створюється автоматично;
- `idx_genre_popularity_danceability` — compound index для запиту з фільтром по `track_genre`, сортуванням по `popularity` і умовою по `audio_features.danceability`;
- `idx_explicit_instrumentalness_speechiness` — compound index для фільтрації по `explicit`, `audio_features.instrumentalness` і `audio_features.speechiness`.

### Завдання 4.1 — Explain після індексу для запиту по `track_genre`, `danceability` і `popularity`

Запит:

```javascript
db.tracks.find(
  {
    track_genre: "pop",
    "audio_features.danceability": { $gte: 0.7 }
  },
  {
    track_name: 1,
    popularity: 1,
    track_genre: 1,
    "audio_features.danceability": 1
  }
).sort({ popularity: -1 }).explain("executionStats")
```

MongoDB використала індекс `idx_genre_popularity_danceability`. Це видно по `IXSCAN` і полю `indexName`.

Після створення індексу отримано такі метрики:

| Метрика | Значення |
|---------|----------|
| `nReturned` | 354 |
| `totalKeysExamined` | 412 |
| `totalDocsExamined` | 354 |
| `executionTimeMillis` | 1 |

У плані присутні `IXSCAN`, `FETCH` і `PROJECTION_DEFAULT`. Це означає, що індекс використовується для відбору кандидатів, але MongoDB все ще звертається до повних документів через `FETCH`, тому запит не є covered query.

### Завдання 4.2 — Explain для індексу пошуку музики для роботи

Запит:

```javascript
db.tracks.find(
  {
    explicit: false,
    "audio_features.instrumentalness": { $gt: 0.5 },
    "audio_features.speechiness": { $lt: 0.1 }
  },
  {
    track_name: 1,
    artists: 1,
    explicit: 1,
    "audio_features.instrumentalness": 1,
    "audio_features.speechiness": 1
  }
).explain("executionStats")
```

MongoDB використала індекс `idx_explicit_instrumentalness_speechiness`.

Ключові метрики:

| Метрика | Значення |
|---------|----------|
| `nReturned` | 16141 |
| `totalKeysExamined` | 16602 |
| `totalDocsExamined` | 16141 |
| `executionTimeMillis` | 54 |

У плані присутні `PROJECTION_DEFAULT`, `FETCH` і `IXSCAN`. Це означає, що індекс працює, але MongoDB все ще читає повні документи, тому цей запит також не є covered query.

### Що змінилося в плані виконання після створення індексу

Після створення індексу оптимізатор переходить від повного перегляду колекції до читання індексних ключів через `IXSCAN`. Якщо індекс підібраний коректно, зменшується кількість переглянутих документів, а також може зникати окремий `SORT`, якщо індекс покриває і фільтр, і сортування.

Для запиту з `track_genre`, `popularity` і `audio_features.danceability` порядок полів в індексі було обрано за правилом **ESR**:

- Equality — `track_genre`;
- Sort — `popularity`;
- Range — `audio_features.danceability`.

### Як зрозуміти, що індекс використовується

Індекс використовується, якщо:

- у `winningPlan` або у вкладених stages присутній `IXSCAN`;
- у плані вказано `indexName`;
- відсутній `COLLSCAN`;
- `totalKeysExamined > 0`.

### Завдання 4.3 — Чи є запит covered query

Для перевірки було виконано запит:

```javascript
db.tracks.find(
  {
    track_genre: "pop",
    popularity: { $gte: 70 }
  }
).explain("executionStats")
```

У плані виконання присутні `IXSCAN` і `FETCH`, причому використовується індекс `idx_genre_popularity_danceability`.

Ключові метрики:

| Метрика | Значення |
|---------|----------|
| `nReturned` | 317 |
| `totalKeysExamined` | 317 |
| `totalDocsExamined` | 317 |
| `executionTimeMillis` | 0 |

Цей запит **не є covered query**, тому що:

- MongoDB за замовчуванням повертає повний документ, якщо не задано проєкцію;
- у `winningPlan` є stage `FETCH`;
- `totalDocsExamined` не дорівнює 0.

Щоб запит міг бути covered query, потрібно, щоб усі поля з фільтра і всі поля з проєкції повністю містилися в індексі, а `_id` був або включений в індекс, або явно виключений із проєкції.

Приклад ближчого до covered query варіанта:

```javascript
db.tracks.find(
  {
    track_genre: "pop",
    popularity: { $gte: 70 }
  },
  {
    _id: 0,
    track_genre: 1,
    popularity: 1
  }
)
```

Навіть у такому випадку коректність потрібно перевіряти через `explain("executionStats")`.

## Висновок

У ході роботи було побудовано повний пайплайн обробки даних для музичного стрімінгового сервісу на MongoDB Atlas: від завантаження сирого CSV до побудови документної схеми, виконання запитів, аналітичних aggregation pipelines та оптимізації запитів за допомогою compound indexes.

Результат показує, що MongoDB добре підходить для задач, де потрібно поєднати гнучку модель зберігання даних із аналітичними сценаріями, вкладеними структурами, масивами та оптимізацією продуктивності через індекси.



01_load_data.py
![alt text](image.png)

Ось що ми бачимо на монго 
все відпрацювало гарно 
![alt text](image-1.png)

02_transform.js запускав через mongodb compass
![alt text](image-2.png)

part2_queries.js  
![alt text](image-3.png)



![alt text](image-4.png)