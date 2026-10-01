# Kafka Project

A small asynchronous lab for following an event from a FastAPI request, through a Kafka topic, into MongoDB. The API only publishes; a separate Kafka consumer validates and stores each message. The unit tests mock Kafka and do not need either infrastructure service.

For the primary-write/replica-read design, configuration, Mermaid diagram, and
operational requirements, see [MongoDB read/write routing](docs/read-write-database-design.md).

## Project Layout

```text
kafka-learning/
├── app/
│   ├── main.py                 # FastAPI app and service lifespan
│   ├── core/
│   │   ├── config.py           # Environment-based settings
│   │   └── database.py         # Beanie write model and Motor read/write clients
│   ├── repositories/
│   │   └── event_repository.py # Primary writes and replica-preferred reads
│   ├── models/event.py         # MongoDB document and indexes
│   ├── schemas/event.py        # Request, Kafka-message, and response schemas
│   ├── services/
│   │   ├── event_service.py    # Create, publish, process, and save flow
│   │   ├── kafka_producer.py   # Async Kafka producer
│   │   └── kafka_consumer.py   # Async Kafka consumer loop
│   ├── api/routes/
│   │   ├── health.py           # GET /health
│   │   └── events.py           # Event publish and listing endpoints
│   └── utils/logger.py         # Basic application logging
├── tests/                      # Infrastructure-free API tests
├── docker/kafka/               # Reserved for Kafka learning configs
├── docker-compose.yml          # MongoDB and single-node KRaft Kafka
├── .env.example                # Local development settings
└── pyproject.toml              # Runtime and test dependencies
```

## Prerequisites and Install

Install Python 3.13, Docker Desktop, and [uv](https://docs.astral.sh/uv/). From this directory:

```powershell
uv sync
```

`uv sync` creates `.venv`, installs the application and development dependencies, and uses `uv.lock` when present. Settings are read from `.env`; the checked-in development file uses the local Docker ports. For a fresh checkout, copy `.env.example` to `.env`.

## Start the Lab

1. Start MongoDB and Kafka:

   ```powershell
   docker compose up -d
   ```

2. Create a topic with three partitions (useful for the experiments below):

   ```powershell
   docker compose exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --create --if-not-exists --topic test-events --partitions 3 --replication-factor 1
   ```

3. Start FastAPI from this directory:

   ```powershell
   uv run uvicorn app.main:app --reload
   ```

The API is at `http://localhost:8000`; interactive API docs are at `http://localhost:8000/docs`.

The lifespan initializes separate Motor clients and binds Beanie to the write database, where Beanie creates the `Event` indexes. Consumer writes use Beanie's atomic upsert with majority write concern on the primary. Normal list requests use the Motor read client and prefer a secondary; `?consistency=strong` reads from the primary. Kafka connection failures are logged and leave the HTTP process running; a publish request returns `503` if the producer could not connect. If Kafka was unavailable during startup, start Kafka and restart the app. The consumer task does not block the event loop. On shutdown, the consumer task, producer, and both MongoDB clients are closed.

The Compose MongoDB service is a standalone development server. With `secondaryPreferred`, reads fall back to that server's primary, so this local setup verifies application behavior but does not provide read offload. Configure both MongoDB URLs for the same real replica set (for example, the same Atlas cluster) to serve normal reads from secondaries. Use the database name `kafka_learning` on every replica-set member; MongoDB replication does not copy data between differently named databases.

## Verify Services

```powershell
docker compose ps
docker compose logs kafka mongodb
```

Wait for both containers to report `healthy`. Check Kafka and its topic:

```powershell
docker compose exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list
docker compose exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --describe --topic test-events
```

Check FastAPI:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Expected response: `status: ok`.

## Exact Manual Event Flow

1. Start infrastructure with `docker compose up -d`, create `test-events` using the command above, and start FastAPI with `uv run uvicorn app.main:app --reload`.
2. In PowerShell, publish an event:

   ```powershell
   $body = @{ event_type = 'user.created'; user_id = 'user_123'; payload = @{ name = 'Sushil' } } | ConvertTo-Json -Depth 5
   Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/events -ContentType 'application/json' -Body $body
   ```

3. The API responds with `success`, `message`, and a generated `event_id` (HTTP `202 Accepted`). The producer log includes `Event published to Kafka`.
4. The consumer logs `Event received from Kafka`, validates the message, and saves it to MongoDB. Successful processing logs `Event saved to MongoDB` and `Event processed`.
5. Read processed events, optionally paginating with `skip` and `limit`:

   ```powershell
   Invoke-RestMethod 'http://localhost:8000/api/events?skip=0&limit=20'
   ```

The API's successful publish response confirms Kafka accepted the message; persistence happens asynchronously afterward. A malformed request returns `422`. If MongoDB is unavailable, the consumer logs the failure and retries the message without committing its offset.

## Verify MongoDB

Open a Mongo shell in the container:

```powershell
docker compose exec mongodb mongosh kafka_learning
```

Then inspect saved events:

```javascript
db.events.find().sort({ created_at: -1 }).limit(10).pretty()
db.events.countDocuments()
```

The document has an `event_id`, event data, `status: "processed"`, `created_at`, and `processed_at`. The `event_id` index is unique, and indexes also cover event type, user, and creation time.

## Kafka Concepts in This Project

- **Kafka** is the broker: it accepts and retains event records so the API and processing code do not have to run as one synchronous operation.
- A **producer** publishes a record. Here FastAPI calls the async producer after validating the request.
- A **topic** is a named stream of records. This project publishes to `test-events`.
- A **partition** is an ordered log within a topic. Kafka distributes records among partitions; order is guaranteed within one partition, not across the whole topic.
- A **consumer** reads records. This project's consumer validates each JSON record and stores it in MongoDB.
- A **consumer group** is one logical subscriber made of one or more consumers. Members divide the topic's partitions; a partition is assigned to at most one member in the group at a time.
- An **offset** is a record's position in a partition. Kafka stores committed offsets per group so that group can continue after a restart.

The producer uses `event_id` as the Kafka key. Kafka hashes a key to select a partition, so records with the same key are routed consistently. Since this demo generates a new event ID per request, each event will typically be spread among the topic's partitions.

```text
Client -> FastAPI -> Producer -> test-events topic -> Consumer -> MongoDB
```

## Tests

Run the unit tests without Docker:

```powershell
uv run pytest
```

- **Unit tests** exercise the health endpoint, request validation, and publishing response with a fake producer. They do not initialize MongoDB or Kafka.
- **Integration tests** use the manual flow above with Docker services running; verify the event appears in `GET /api/events` and in `db.events`.
- **Manual Kafka tests** use the Kafka CLI and the experiments below to observe partitions, groups, and offsets.

## Kafka Experiments

### 1. Multiple Messages

Send ten requests to `POST /api/events` (repeat the PowerShell command in a loop, or send requests from `/docs`). Check the API log for ten `Event published to Kafka` entries, the consumer log for ten received events, and MongoDB for the saved records:

```javascript
db.events.countDocuments()
```

### 2. Two Consumers in One Group

Keep the first app running. In a second terminal, start another app instance with the same group and a different HTTP port:

```powershell
uv run uvicorn app.main:app --port 8001
```

With three partitions and two group members, Kafka assigns partitions across the two consumers. Publish several events and inspect both terminals; each record is delivered to one member, not both. Stop the second instance with `Ctrl+C` when done. Do not use `--reload` for this experiment because reload creates extra processes.

### 3. Different Consumer Groups

Stop both app instances. In separate terminals start each with its own group:

```powershell
$env:KAFKA_CONSUMER_GROUP = 'group-A'; uv run uvicorn app.main:app --port 8000
```

```powershell
$env:KAFKA_CONSUMER_GROUP = 'group-B'; uv run uvicorn app.main:app --port 8001
```

Each group is an independent subscriber and receives its own copy of the topic stream. New groups use the configured `earliest` reset policy when they have no committed offsets. Stop both processes afterward. The two consumers write into the same MongoDB collection; the unique event ID index makes repeat delivery idempotent.

### 4. Consumer Restart and Offsets

Stop the app, publish some events using a separate terminal Kafka producer, then start the app again with the same group. The consumer resumes after that group's committed offsets. A new group has no stored offsets and, with `earliest`, starts at the earliest retained record. For a simple broker-side publisher:

```powershell
docker compose exec -T kafka /opt/kafka/bin/kafka-console-producer.sh --bootstrap-server localhost:9092 --topic test-events --property parse.key=true --property key.separator=:
```

Type one line such as `manual-1:{"event_id":"manual-1","event_type":"demo.message","user_id":"user_123","payload":{"text":"hello"}}`, then press `Ctrl+Z` and Enter to finish. The app's consumer validates the same event fields as API-published messages.

### 5. Kafka Key

The app already sets `event_id` as the message key. Inspect keys and values with the console consumer:

```powershell
docker compose exec kafka /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic test-events --from-beginning --property print.key=true --property key.separator=:
```

The key is visible before the JSON value. Publishing multiple records with an identical key routes them to the same partition, preserving their relative order there.

### 6. Partitions

Inspect the three topic partitions:

```powershell
docker compose exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --describe --topic test-events
```

The resulting assignment is conceptually:

```text
Producer
   -> Kafka topic test-events
      -> Partition 0
      -> Partition 1
      -> Partition 2
```

In a group, at most three consumers can actively read this three-partition topic at once; additional members wait without an assignment. Kafka assigns records with matching keys to the same partition.

## Stop the Lab

```powershell
docker compose down
```

This stops the containers and keeps MongoDB data in its named volume. To remove that data as well, run `docker compose down -v`.


## Study Group Chat — Kafka Implementation

This project now includes **group-only study chat**. There is deliberately no 1-to-1/private chat model. A study group can contain multiple users, and members can exchange text, images, files, and videos.

### Architecture

    User A ─┐
    User B ─┼─ WebSocket connections ─┐
    User C ─┘                         │
                                      ▼
                             FastAPI Study Group API
                                      │
                             Kafka: study-group-chat
                                      │
                         key = group_id (ordering per group)
                                      │
                    ┌─────────────────┴─────────────────┐
                    ▼                                   ▼
           MongoDB persistence                Chat fan-out consumer
           study_group_messages                         │
                    │                                    ▼
                    └──────────────► group WebSockets

Media bytes: FastAPI -> uploads/study-groups/<group_id>/
Kafka payload: metadata + media URL only (never raw binary)

### Why the Kafka key is group_id

Every message published for the same study group uses the group ID as the Kafka record key. Kafka therefore routes that group's messages consistently to one partition, preserving their relative order inside that partition. Different groups can be distributed across the three chat partitions.

The chat fan-out consumer uses its own consumer group (`study-group-chat-fanout`). Every running API instance should receive every chat event so it can broadcast the event to WebSocket users connected to that instance. The existing `kafka-learning-group` remains responsible for the original `test-events` learning flow.

### Supported message types

| Type | Endpoint | Kafka contains | Stored in MongoDB |
|---|---|---|---|
| Text | POST /api/study-groups/{group_id}/messages/text | text + metadata | text |
| Image | POST /api/study-groups/{group_id}/messages/media | media URL + metadata | media URL + metadata |
| File | same media endpoint | media URL + metadata | media URL + metadata |
| Video | same media endpoint | media URL + metadata | media URL + metadata |

Default media limit is **50 MB**. Change `CHAT_MEDIA_MAX_SIZE_MB` for the learning environment. In production, replace local `uploads/` with object storage and keep only the object URL/key in MongoDB/Kafka.

### Group Chat API

Create a group:

    POST /api/study-groups
    Content-Type: application/json

    {
      "name": "Python + Kafka Study Group",
      "owner_id": "user_1",
      "member_ids": ["user_2", "user_3"]
    }

Add a member:

    POST /api/study-groups/{group_id}/members
    {"user_id": "user_4"}

Send text:

    POST /api/study-groups/{group_id}/messages/text
    {"sender_id": "user_1", "text": "Today we will learn Kafka partitions."}

Send image/file/video using multipart form data:

    curl.exe -X POST "http://localhost:8000/api/study-groups/<GROUP_ID>/messages/media?sender_id=user_1" -F "file=@C:\\path\\to\\lesson.mp4"

Read group history:

    GET /api/study-groups/{group_id}/messages?user_id=user_1&skip=0&limit=50

Open the real-time group WebSocket:

    ws://localhost:8000/api/study-groups/{group_id}/ws?user_id=user_1

The WebSocket is **group-only**. The server checks membership before accepting the connection. Messages use the path **HTTP -> Kafka -> consumer -> MongoDB -> WebSocket broadcast**.

### Kafka chat topic

The application automatically creates `study-group-chat` with three partitions and one-day retention for this learning project.

Inspect it with:

    docker compose exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --describe --topic study-group-chat

    docker compose exec kafka /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic study-group-chat --from-beginning --property print.key=true --property key.separator=:

### Multi-user test

1. Create one group with users `user_1`, `user_2`, and `user_3`.
2. Open three WebSocket clients using the same group ID and different member IDs.
3. Send a text message as `user_1`.
4. Verify all three connected members receive the same persisted message.
5. Upload an image, file, and video and verify each message contains its type, file name, MIME type, size, and media URL.
6. Restart the API and reconnect. Use the history endpoint to verify MongoDB persistence.
7. Start a second API instance on another port and connect a member there. Publish a message and verify both API instances receive the Kafka event.

### Important production note

The current WebSocket connection manager is in-process, which is appropriate for this Kafka learning project. Kafka provides cross-instance event delivery, while the dedicated fan-out consumer ensures each API instance sees every chat event. Production deployments should additionally use authentication/authorization, object storage, virus scanning, rate limits, and a durable distributed WebSocket/session layer where needed.

## Next.js Frontend

The repository now includes a production-oriented frontend in `frontend/` for the study-group experience.

### Frontend stack

- Next.js + React + TypeScript
- Framer Motion for interface motion
- React Three Fiber / Drei for the interactive 3D landing visual
- Study AI demo sign-in with a Google-style entry button
- WebSocket client for real-time study-group chat
- Responsive glass/neon visual system

### Run the frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Set `NEXT_PUBLIC_API_URL` to the FastAPI API root (default `http://localhost:8000/api`). The current frontend prototype bypasses Google OAuth and creates a local demo session when the login button is clicked.

### Frontend routes

- `/` — product landing page and 3D hero
- `/login` — Google authentication
- `/study-groups` — study-group discovery and creation
- `/study-groups/[groupId]` — real-time group chat, media uploads and AI companion surface
- `/account` — session and account deletion controls

The current frontend prototype does not perform Google OAuth. The Google-style login button creates a local demo session and redirects directly to `/study-groups`. The backend Google authentication endpoint remains available for a future real OAuth flow.
