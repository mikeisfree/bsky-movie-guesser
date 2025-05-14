# Active Context: BlueTrivia

## Current Work Focus

We are currently testing the implementation of BlueTrivia with multiple question sources (movie trivia and general trivia) and player response tracking. The testing phase uses a shortened round time of 1 minute instead of the planned 30 minutes.

## Recent Changes

- Renamed project from "Bsky Movie Guesser" to "BlueTrivia" to reflect multiple question types
- Implemented multiple question sources using abstract interface:
  - MovieQuestionSource for movie guessing
  - TriviaQuestionSource for general knowledge questions
- Added a database initializer with 25 sample trivia questions across various categories
- Implemented player response tracking (who answered, when, and if correct)
- Created database schema for tournaments and player statistics
- Fixed post character limit issues to stay under BlueSky's 300-character limit
- Updated the result post format to highlight fastest correct answers
- Handled backward compatibility with existing database schemas

## Next Steps

### Short-term Goals

1. Complete testing of multiple question sources and response tracking

   - Verify correct handling of different question types
   - Ensure player statistics are properly recorded
   - Test edge cases like empty responses or all correct/incorrect answers

2. Refine player tracking and leaderboard functionality

   - Implement proper tournament creation and management
   - Add commands for players to view their stats
   - Create tournament leaderboard functionality

3. Improve error handling and recovery
   - Better handling of API failures
   - Add more detailed logging for troubleshooting
   - Implement backup question sources if primary sources fail

### Medium-term Goals

1. Extend the round time back to 30 minutes for production
2. Add more trivia categories and question sources
3. Develop a web interface for leaderboards and statistics

## Active Decisions and Considerations

- Using modular question sources to easily add new question types
- Database schema designed to support both current features and future expansions
- Currently facing challenges with BlueSky's character limit for result posts
- Need to ensure all database operations are transactional to prevent data loss
- Planning to balance difficulty levels across different question sources

## Important Patterns and Preferences

- All question sources follow the common `QuestionSource` interface
- Database migrations should maintain backward compatibility
- Player response tracking must be position-based to identify fastest answers
- Post content must be managed carefully to avoid exceeding BlueSky's limits
- Defensive coding required around API calls to handle failures gracefully

## Learnings and Project Insights

- The abstract question source interface makes adding new question types straightforward
- SQLite provides sufficient performance for the expected workload
- BlueSky's character limit requires careful post content management
- Fuzzy matching works well across different question types with configurable thresholds
- Testing with shortened time windows (1 minute) is useful for rapid development
