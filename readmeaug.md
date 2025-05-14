# Bsky Movie Guesser

A BlueSky social media bot that runs a movie guessing game where users collectively try to identify movies from censored images.

## Game Overview

The bot posts partially censored movie images and users have 30 minutes to guess the movie title by replying to the post. After the time expires, the bot calculates the success rate and posts the results.

### Game Flow

1. **Movie Selection**: Bot randomly selects a movie from TMDB with at least 4 backdrop images
2. **Image Processing**: Images are optimized, censored, and watermarked
3. **Round Start**: Bot posts images with a 30-minute timer
4. **Guessing Period**: Users reply with their guesses
5. **Calculation**: Bot analyzes all replies using fuzzy matching
6. **Results**: Bot posts success rate (% correct guesses)
7. **Next Round**: After 30 minutes, a new round begins

## Installation

### Using Docker (Recommended)

1. Create a `docker-compose.yaml` file:

```yaml
services:
  bmg:
    image: ghcr.io/joaoiacillo/bskymovieguesser:latest
    volumes:
      - bmg-app:/code
      - bmg-logs:/code/.logs
    restart: on-failure
    environment:
      TMDB_API_ACCESS_TOKEN: "YOUR_TMDB_TOKEN"
      BSKY_HANDLE: "YOUR_HANDLE"
      BSKY_PASSWORD: "YOUR_APP_PASSWORD"

volumes:
  bmg-app:
  bmg-logs:
```

2. Start the container:

```bash
sudo docker compose up -d
```

### Manual Installation

1. Install requirements (Python 3.9+ required):

```bash
pip3 install -r requirements.txt
```

2. Get API credentials:

   - **TMDB**: Sign up at [themoviedb.org](https://www.themoviedb.org), go to account settings → API and generate an access token
   - **BlueSky**: Create an App Password in Settings → Advanced → App Passwords

3. Configure environment:

   - Copy `.env.example` to `.env`
   - Update required credentials:
     - `TMDB_API_ACCESS_TOKEN`
     - `BSKY_HANDLE` (without @)
     - `BSKY_PASSWORD` (app password)

4. Run the bot:

```bash
python3 main.py
```

## Project Structure

```
bmg/
├── bsky.py               # BlueSky API client
├── database/             # Database models and operations
├── game/                 # Game logic
│   ├── config.py         # Game configuration
│   ├── game.py           # Main game loop
│   └── posts.py          # Post content templates
├── image/                # Image processing
│   ├── movie_image.py    # Image manipulation
│   └── preparer.py       # Image processing pipeline
├── matcher.py            # Fuzzy matching for guesses
└── tmdb.py               # TMDB API client
```

### Core Components

- **TMDB Client**: Fetches movie data and images
- **BlueSky Client**: Handles social media interaction
- **Image Preparer**: Processes images for the game
- **Database**: Tracks rounds, posts, and results
- **Matcher**: Determines if guesses are correct using fuzzy matching

## Technical Details

### Image Processing

The bot processes images through three main steps:

1. **Optimization**

   - Resizes images to max 1280x720
   - Compresses to JPEG with configurable quality

2. **Censoring**

   - Creates a random visible window on the image
   - Draws black rectangles over the rest

3. **Watermarking**
   - Adds TMDB logo for proper attribution
   - Placed at bottom of image

### Scoring System

The bot uses fuzzy string matching to determine if a user's guess is correct:

1. **String Cleaning**

   - Removes extra spaces, symbols
   - Converts to lowercase
   - Keeps only alphanumeric characters and spaces

2. **Similarity Calculation**

   - Uses Levenshtein distance to calculate similarity (0-100 score)
   - A guess is considered correct if score ≥ threshold (default: 80)

3. **Results Calculation**
   - Calculates percentage of correct guesses
   - Likes all correct guesses
   - Posts overall success rate

## Configuration Options

You can customize behavior with environment variables:

- `BOT_DEBUG_MODE`: Set to 'true' for console output (default: false)
- `BOT_THRESHOLD`: Minimum score for correct guesses (default: 80)
- `TMDB_IMAGE_QUALITY`: Image compression quality (default: 75)

See `.env.example` for all available options.

## Logging

- Log files are stored in `.logs/` directory
- Each file includes timestamp of creation
- Debug mode prints to console instead of files

## Game Rules for Players

1. Reply to the bot's post with your guess of the movie title
2. You have 30 minutes to submit your guess
3. Typos are allowed - if you're close enough, it counts as correct
4. The bot will like your reply if your guess was correct
5. After the round ends, the bot posts the correct answer and success rate

## Developer Documentation

### Code Examples

#### 1. Main Game Loop

The main game loop is implemented in `bmg/game/game.py`:

```python
def start(self):
    """
    Starts the game loop.
    """
    self.logger.info('Starting game loop')

    while True:
        try:
            self.select_random_movie()
            self.start_round()

            # Wait 30 minutes for guesses
            self.logger.info('Waiting 30 minutes for guesses')
            sleep(1800)  # 30 minutes

            # Calculate results
            self.logger.info('Calculating results')
            if self.calculate_correctness_percentage():
                self.post_results()

            # Wait 30 minutes before next round
            self.logger.info('Waiting 30 minutes before next round')
            sleep(1800)  # 30 minutes
        except Exception as e:
            self.logger.error(f'Error in game loop: {e}')
            sleep(300)  # Wait 5 minutes before retrying
```

#### 2. Movie Selection

Random movie selection is handled in `bmg/game/game.py`:

```python
def select_random_movie(self):
    movie: Union[Movie, None] = None
    backdrops: Union[list[bytes], None] = None

    # Movies that have under 4 backdrops must not be selected
    while backdrops is None:
        movie = self.tmdb.get_random_movie()
        backdrops = TmdbMovieUtils.get_n_movie_backdrops(
                self.tmdb,
                movie.id
        )

    movie.images = [self.imgp.prepare(i) for i in backdrops]

    self.logger.info(f'Selected movie: {movie.title}')
    self.movie = movie
```

#### 3. Image Processing Pipeline

The image processing pipeline is implemented in `bmg/image/preparer.py`:

```python
def prepare(self, image_bytes: bytes) -> bytes:
    """
    Optimizes, censors and watermarks an image bytes objects automatically.
    """
    image = MovieImage(image_bytes)
    image.optimize(self.quality)
    image.censor()
    image.watermark()

    return image.to_bytes()
```

#### 4. Image Censoring

The censoring logic is implemented in `bmg/image/movie_image.py`:

```python
def censor(self) -> None:
    """
    Important part of the game. The image needs to have certain parts
    censored so that the challenge can rise up. This draws rectangles
    around a random generated rectangle area, so that only it can be
    visible.
    """
    image, output = self.buffer.create_pair()

    visible_rect = CensorUtils.create_visible_window(image.size)
    censor_rects = CensorUtils.create_censor_rects(image.size, visible_rect)

    draw = ImageDraw.Draw(image)
    black = (0, 0, 0)
    for rect in censor_rects:
        draw.rectangle(rect, fill=black)

    image.save(output, format='JPEG')
    self.buffer.save(output)
```

#### 5. Fuzzy Matching for Guesses

The fuzzy matching logic is implemented in `bmg/matcher.py`:

```python
class Match:
    @staticmethod
    def clean(string: str) -> str:
        """
        Cleans a string before their matching.
        """
        cleaned = string.strip()
        cleaned = ''.join(c for c in cleaned if c.isalnum() or c.isspace())
        cleaned = cleaned.lower().split()
        return ' '.join(cleaned)

    @staticmethod
    def str(a: str, b: str) -> int:
        """
        Matches two strings and returns a score between 0 and 100 based on their
        similarity.
        """
        return fuzz.ratio(a, b)
```

#### 6. Calculating Results

The result calculation is implemented in `bmg/game/game.py`:

```python
def calculate_correctness_percentage(self):
    self.attempts = 0
    self.correct_attempts = 0

    thread_res = self.bsky.get_thread(self.posts.round)
    thread = thread_res.thread

    if not len(thread.replies):
        self.logger.info("No players participated in this round. Skipping")
        return False

    self.logger.info(f'Matching {len(thread.replies)} comments')
    start = datetime.now()

    for reply in thread.replies:
        score = self.get_reply_score(reply.post.record.text)

        if score >= self.threshold:
            self.correct_attempts += 1
            self.bsky.client.like(reply.post.uri, reply.post.cid)

        self.attempts += 1

    end = datetime.now()
    self.logger.info(f'Matching took {(end - start).total_seconds()} seconds')

    self.percent = round(self.correct_attempts / self.attempts * 100)
    self.logger.info(f'Correctness: {self.percent}% ({self.correct_attempts}/{self.attempts})')

    return True
```

#### 7. BlueSky API Integration

The BlueSky API client is implemented in `bmg/bsky.py`:

```python
class BskyClient:
    def __init__(self, handle: str, password: str, logger: Logger):
        self.client = Client()
        self.logger = logger

        self.client.login(handle, password)
        self.logger.info(f'Bsky client logged in as @{self.client.me.handle}')

    def post(self, content: str):
        return self.client.send_post(content)

    def post_images(self, content: str, images: list[bytes]):
        return self.client.send_images(content, images=images)

    def get_thread(self, uri: str):
        return self.client.get_post_thread(uri, 1)

    def delete_post(self, uri: str):
        return self.client.delete_post(uri)
```

#### 8. TMDB API Integration

The TMDB API client is implemented in `bmg/tmdb.py`:

```python
class TmdbClient:
    def __init__(self, access_token: str):
        self.access_token = access_token

    def request(self, url: str, params: dict = None):
        if params is None:
            params = {}

        headers = {
            'Authorization': 'Bearer ' + self.access_token
        }

        return get(url, params, headers=headers)

    def get_random_movie(self) -> Movie:
        page = randint(1, 1000) // 20
        url = f'https://api.themoviedb.org/3/discover/movie'
        params = {
            'include_adult': 'false',
            'sort_by':       'popularity.desc',
            'page':          page
        }
        response = self.request(url, params)
        results = response.json()['results']
        chosen = choice(results)

        return Movie(
                chosen['id'],
                chosen['title'],
                Match.clean(chosen['title']),
                None
        )
```

## Future Implementation Ideas

1. **Multiple Question Sources**

   - Custom trivia questions
   - Integration with other APIs
   - Different difficulty levels

2. **Player Tracking**

   - Individual player scores
   - Leaderboards and statistics
   - Player profiles

3. **Tournament System**

   - Scheduled tournaments with multiple rounds
   - Special themes and categories
   - Prizes and recognition

4. **Web Interface**
   - Statistics dashboard
   - Leaderboard display
   - Admin controls

## Contributing

The door is always open for contributions! Send a pull request with your modifications or improvements. You can also fork this repository and work on another version, but always remember that this code is under the GPLv3 license.

## License

[GNU General Public License v3.0](LICENSE)
