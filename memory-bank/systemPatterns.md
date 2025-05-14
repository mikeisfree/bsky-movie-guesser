# System Patterns: Bsky Movie Guesser

## System Architecture

The Bsky Movie Guesser follows a modular architecture with distinct components handling specific responsibilities:

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│  Game       │------>│  TMDB       │------>│  Image      │
│  Controller │<------│  Client     │<------│  Preparer   │
└─────────────┘       └─────────────┘       └─────────────┘
       │
       │
       ▼
┌─────────────┐       ┌─────────────┐
│  BlueSky    │------>│  Database   │
│  Client     │<------│  Manager    │
└─────────────┘       └─────────────┘
```

## Key Technical Decisions

### 1. Component-Based Design

The system uses distinct, loosely coupled components connected through a dependency injection pattern:

```python
def __init__(self, config: GameConfig):
    self.bsky: BskyClient = config.bsky
    self.tmdb: TmdbClient = config.tmdb
    self.imgp: ImagePreparer = config.imgp
    self.db: Database = config.db
```

This approach:

- Enhances testability by allowing component mocking
- Improves maintainability with clear separation of concerns
- Facilitates future expansion of features

### 2. Image Processing Pipeline

Images follow a three-stage processing pipeline:

1. **Optimize** - Resize and compress
2. **Censor** - Apply random visibility window
3. **Watermark** - Add attribution

This pattern allows for clear separation of image transformation steps while maintaining a simple API.

### 3. Fuzzy Matching for Answer Evaluation

The system employs fuzzy string matching rather than exact matching to:

- Accommodate typos and minor spelling variations
- Allow for different formatting of movie titles
- Provide configurable strictness through a threshold parameter

### 4. Multi-Stage Game Flow

The game employs a state-based workflow:

1. Selection phase (pick movie)
2. Preparation phase (process images)
3. Guessing phase (post and collect responses)
4. Evaluation phase (determine correctness)
5. Results phase (post outcomes)

### 5. Continuous Operation Pattern

The bot operates in a continuous loop, automatically initiating new rounds:

- Timer-based transitions between game states
- Automatic error recovery
- No manual intervention required for normal operation

## Critical Implementation Paths

### Game Round Execution Path

1. Select movie with sufficient backdrop images
2. Process 4 random backdrops through image pipeline
3. Post to BlueSky with 30-minute timer
4. Monitor and collect replies
5. Apply fuzzy matching to evaluate responses
6. Calculate statistics (correct percentage, attempts)
7. Post results
8. Initiate next round

### Error Handling Path

1. Catch and log exceptions
2. Attempt graceful recovery where possible
3. Fall back to selecting new movie if current one fails
4. Implement retry logic for API calls
