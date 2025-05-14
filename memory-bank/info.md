## Bsky Movie Guesser

A BlueSky social media bot that runs a movie guessing game where:

The bot selects a random movie and posts 4 partially censored images
Users have 30 minutes to guess the movie title in replies
The bot calculates correctness using fuzzy matching (with a configurable threshold)
Results are posted showing success percentage and total attempts

## Key components:

-TMDB API integration for movie data and images
-BlueSky API for posting and interaction
-Image processing (optimization, censoring, watermarking)
-SQLite database for tracking rounds and posts
-The bot is designed to run continuously, starting new rounds -automatically after each completed round.

### IDEAS TO IMPLEMENT

- BOT will randomly select question source each time he posts question

sources:
a) (implemented) - movies (TMDB database)
b) (to implement)- custom trivia (fetch random question predefined in backend DB)
c) other sources APIS/custom

- Scorecards and winners logged to DB (rounds, points, time, bsky handle, tournaent name)
- Tournaments (X rounds during X days before annoucing a victor)
- Website with leaderboard and game stats

### 1. How does the movie guessing game work and what are the main components?

Bsky Movie Guesser Game Flow
The game is a movie guessing bot for BlueSky that works in continuous rounds:

Game Flow
Movie Selection: Bot randomly selects a movie from TMDB with at least 4 backdrop images
Image Processing: 4 random backdrops are:
Optimized (resized, compressed)
Censored (only small portions visible)
Watermarked
Round Start: Bot posts images with a 30-minute timer
Guessing Period: Users reply with their guesses
Calculation: Bot analyzes all replies using fuzzy matching
Results: Bot posts success rate (% correct guesses)
Next Round: After 30 minutes, a new round begins
Main Components
bmg/game

```python
def **init**(self, config: GameConfig):
self.bsky: BskyClient = config.bsky
self.tmdb: TmdbClient = config.tmdb
self.imgp: ImagePreparer = config.imgp
self.db: Database = config.db # ...
```

TMDB Client: Fetches movie data and images
BlueSky Client: Handles social media interaction
Image Preparer: Processes images for the game
Database: Tracks rounds, posts, and results
Matcher: Determines if guesses are correct using fuzzy matching
The game runs continuously, with configurable settings like matching threshold and wait times between rounds

2)How does the bot handle image processing for the movie guessing game?

Image Processing in Bsky Movie Guesser
The bot processes images through three main steps using the ImagePreparer class:

bmg/image

```python
def prepare(self, image_bytes: bytes) -> bytes:
    """
    Optimizes, censors and watermarks an image bytes objects automatically.
    """
    image = MovieImage(image_bytes)
    image.optimize(self.quality)
    image.censor()
```

1. Optimization
   Resizes images to max 1280x720
   Compresses to JPEG with configurable quality
   Quality set via TMDB_IMAGE_QUALITY (default: 75)
   bmg/image

   ```python
   def optimize(self, quality: int) -> None:
    image, output = self.buffer.create_pair()

    # Images bigger than 1280x720 should always be avoided.
    if image.size[0] > 1280 or image.size[1] > 720:
        image.thumbnail((1280, 720), Image.Resampling.BILINEAR)

    image.save(output, format='JPEG', quality=quality,
     optimize=True)
   ```

2. Censoring
   Creates a random visible window on the image
   Draws black rectangles over the rest
   Increases challenge difficulty
   bmg/image

   ```python
   def censor(self) -> None:
    image, output = self.buffer.create_pair()

    visible_rect = CensorUtils.create_visible_window(image.size)
    censor_rects = CensorUtils.create_censor_rects(image.size, visible_rect)

    draw = ImageDraw.Draw(image)
    black = (0, 0, 0)
    for rect in censor_rects:
        draw.rectangle(rect, fill=black)
   ```

3. Watermarking
   Adds TMDB logo for proper attribution
   Placed at bottom of image
   bmg/image

````python
def watermark(self) -> None:
  image, output = self.buffer.create_pair()
  image = image.convert('RGBA')

  img_height = image.size[1]
  mark_height = TMDB_SVG.size[1]
  mark_offset = 50

  watermark_pos = (mark_offset, img_height - mark_height - mark_offset)

  image.paste(TMDB_SVG, watermark_pos, TMDB_SVG)

  ```

 All image operations use a Buffer class to manage in-memory image data efficiently.
````

## Scoring System for Correct Guesses

The bot uses fuzzy string matching to determine if a user's guess is correct:

String Cleaning: Both the movie title and user's guess are "cleaned" before comparison:

bmg

```python
@staticmethod
def clean(string: str) -> str:
"""
Cleans a string before their matching.
"""
cleaned = string.strip()
cleaned = ''.join(c for c in cleaned if c.isalnum() or c.isspace())
```

Similarity Calculation: The fuzzywuzzy library calculates a similarity score (0-100):
bmg

```python
@staticmethod
def str(a: str, b: str) -> int:
"""
Matches two strings and returns a score between 0 and 100 based on their
similarity.
"""

return fuzz.ratio(a, b)
```

Threshold Comparison: A guess is considered correct if its score meets/exceeds the threshold:
bmg/game

```python
def calculate_correctness_percentage(self): # ...
for reply in thread.replies:
score = self.get_reply_score(reply.post.record.text)

        if score >= self.threshold:
```

Results Calculation: The overall success rate is calculated as a percentage:
bmg/game

```python
self.percent = round(self.correct_attempts / self.attempts * 100)
```

The threshold is configurable through the BOT_THRESHOLD environment variable (default: 80).
