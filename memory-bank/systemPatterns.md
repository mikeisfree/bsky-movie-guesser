# System Patterns: BlueTrivia

## Core Architecture

```mermaid
graph TD
    GC[Game Controller] --> QS[Question Sources]
    GC --> BC[BlueSky Client]
    GC --> DB[Database]
    GC --> IP[Image Processor]

    QS --> MQ[Movie Questions]
    QS --> TQ[Trivia Questions]
    MQ --> TC[TMDB Client]

    IP --> IO[Image Optimizer]
    IP --> IC[Image Censor]
    IP --> IW[Image Watermarker]
```

## Key Components

### Game Controller (bmg/game/game.py)

- Orchestrates game flow and component interactions
- Manages round timing and state transitions
- Processes user responses and calculates results
- Configuration through environment variables

```python
class GameController:
    def __init__(self, config: GameConfig):
        self.bsky: BskyClient = config.bsky
        self.tmdb: TmdbClient = config.tmdb
        self.imgp: ImagePreparer = config.imgp
        self.db: Database = config.db
```

### Question Sources

Abstract interface pattern for extensible question types:

```python
class QuestionSource(ABC):
    @abstractmethod
    def get_question(self) -> Question:
        pass

class MovieQuestionSource(QuestionSource):
    def get_question(self) -> MovieQuestion:
        # Fetch from TMDB

class TriviaQuestionSource(QuestionSource):
    def get_question(self) -> TriviaQuestion:
        # Fetch from local database
```

### Image Processing Pipeline

Three-stage pipeline for image preparation:

1. **Optimization**

   - Resize to max 1280x720
   - JPEG compression with configurable quality
   - Memory-efficient buffer management

2. **Censoring**

   - Random visible window generation
   - Black rectangle overlay
   - Configurable coverage settings

3. **Watermarking**
   - TMDB attribution
   - Consistent positioning
   - Transparency handling

## Critical Implementation Paths

### Game Flow

```mermaid
sequenceDiagram
    participant GC as Game Controller
    participant QS as Question Source
    participant IP as Image Processor
    participant BS as BlueSky
    participant DB as Database

    GC->>QS: Select random source
    QS->>GC: Return question
    GC->>IP: Process images
    IP->>GC: Return processed images
    GC->>BS: Post question
    GC->>DB: Record round start
    loop During round
        BS->>GC: Collect replies
        GC->>DB: Track responses
    end
    GC->>GC: Calculate results
    GC->>BS: Post results
    GC->>DB: Update statistics
```

### Response Processing

1. Reply Collection
   - Monitor BlueSky posts during time window
   - Track response timing for leaderboards
2. Answer Evaluation
   - String cleaning and normalization
   - Fuzzy matching with configurable threshold
   - Position-based tracking for fastest answers

```python
@staticmethod
def clean(string: str) -> str:
    cleaned = string.strip()
    cleaned = ''.join(c for c in cleaned
                     if c.isalnum() or c.isspace())
    return cleaned

@staticmethod
def match(a: str, b: str) -> int:
    return fuzz.ratio(a, b)
```

## Component Relationships

### Database Schema

```mermaid
erDiagram
    ROUNDS ||--o{ POSTS : contains
    ROUNDS ||--o{ PLAYER_RESPONSES : tracks
    TOURNAMENTS ||--o{ ROUNDS : includes
    PLAYER_RESPONSES }|--|| PLAYERS : made_by
```

### Configuration Flow

```mermaid
graph LR
    ENV[Environment Variables] --> GC[Game Config]
    GC --> Components
    subgraph Components
        BC[BlueSky Client]
        TC[TMDB Client]
        IP[Image Preparer]
        DB[Database]
    end
```

## Design Patterns

1. **Strategy Pattern**
   - Question source selection
   - Image processing stages
2. **Observer Pattern**

   - Reply monitoring
   - Round state changes

3. **Factory Pattern**

   - Question creation
   - Image processor instantiation

4. **Repository Pattern**
   - Database access
   - API client implementations

## Error Handling and Recovery

1. **API Failures**

   - Retry mechanisms
   - Fallback content
   - Error logging

2. **Data Consistency**

   - Transactional database operations
   - State validation
   - Round integrity checks

3. **Resource Management**
   - Memory-efficient image processing
   - Connection pooling
   - Cache management

## Performance Considerations

1. **Image Processing**

   - Buffer reuse
   - Optimal compression settings
   - Parallel processing when applicable

2. **Database Operations**

   - Indexed queries
   - Connection pooling
   - Batch operations

3. **API Interactions**
   - Rate limiting compliance
   - Response caching
   - Bulk operations where possible
