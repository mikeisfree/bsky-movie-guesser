# Technical Context: BlueTrivia

## Technologies Used

### Programming Language

- **Python**: Primary programming language

### APIs

- **TMDB API**: Source of movie data and images
- **BlueSky API**: Platform for posting content and gathering user responses

### Image Processing

- **Pillow (PIL)**: Python imaging library for image manipulation
- Custom classes for optimization, censoring, and watermarking

### String Processing

- **FuzzyWuzzy**: Library for fuzzy string matching to evaluate user guesses

### Data Storage

- **SQLite**: Database for storing game rounds, posts, and results
- Custom database models for tracking player responses and tournaments

### Configuration

- **Environment Variables**: Used for configuration settings (thresholds, API keys, etc.)
- **dotenv**: Library for loading environment variables from .env files

## Development Setup

### Environment Variables

- `TMDB_API_KEY`: API key for The Movie Database
- `TMDB_IMAGE_QUALITY`: Quality setting for image compression (default: 75)
- `BOT_THRESHOLD`: Threshold for fuzzy matching (default: 80)
- `BSKY_USERNAME`: BlueSky username for the bot
- `BSKY_PASSWORD`: BlueSky password for the bot
- `DB_PATH`: Path to SQLite database (default: bluetrivia.db)
- `SKIP_ON_INPUT`: Debug setting to allow skipping wait times (default: False)

### Project Structure

```
bsky-movie-guesser/
├── bmg/
│   ├── __init__.py
│   ├── game.py      # Game controller
│   ├── bsky.py      # BlueSky client
│   ├── tmdb.py      # TMDB client
│   ├── image.py     # Image processing
│   ├── database.py  # Database operations
│   └── utils.py     # Utility functions
├── main.py          # Entry point
├── config.py        # Configuration loading
└── memory-bank/     # Documentation
```

## Technical Constraints

### API Limits

- TMDB API has rate limits to consider for movie data fetching
- BlueSky API may have posting frequency limitations

### Image Considerations

- Images need to be optimized for size (max 1280x720)
- BlueSky has limits on post size and attachment count
- Processing must be efficient to allow quick round transitions

### Persistence Requirements

- Game state must be preserved in case of restart
- Posts must be tracked to analyze responses

## Dependencies

### External Libraries

- `atproto`: BlueSky API client
- `requests`: HTTP requests for API calls
- `pillow`: Image processing
- `fuzzywuzzy`: String matching
- `python-Levenshtein`: Optional accelerator for fuzzywuzzy
- `sqlite3`: Database interaction (standard library)

### Third-Party Services

- TMDB (The Movie Database): Primary data source
- BlueSky: Social platform for hosting the game

## Tool Usage Patterns

### Image Preparation Workflow

1. Fetch original images from TMDB
2. Resize/compress for optimization
3. Apply censoring with random visible windows
4. Add TMDB attribution watermark

### Response Processing

1. Collect all replies within time window
2. Clean strings (remove punctuation, normalize spacing)
3. Calculate similarity scores using fuzzy matching
4. Apply threshold to determine correctness
5. Calculate aggregate statistics

### Database Operations

- Store round information (movie, start time, etc.)
- Track post IDs for reply collection
- Record results for potential future features (leaderboards)
