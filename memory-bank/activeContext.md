# Active Context: BlueTrivia

## Current Work Focus
We are currently implementing the core architecture for BlueTrivia (formerly Bsky Movie Guesser) with a focus on supporting multiple question types and player tracking.

## Recent Changes
- Renamed project from "Bsky Movie Guesser" to "BlueTrivia" to better reflect the expanded scope
- Created abstract `QuestionSource` interface to support multiple question types
- Implemented two sources: `MovieQuestionSource` and `TriviaQuestionSource`
- Enhanced database schema to support player tracking and tournaments
- Updated game controller to randomly select question sources

## Next Steps

### Short-term Goals
1. Implement tournament functionality
   - Complete tournament management in database
   - Add tournament status to posts
   - Create tournament leaderboards

2. Enhance player experience
   - Add player stats commands (users can request their stats)
   - Implement streak bonuses for consecutive correct answers
   - Add difficulty levels to questions

3. Improve error handling
   - Add comprehensive logging
   - Implement graceful recovery from API failures
   - Add monitoring for round timing issues

### Medium-term Goals
1. Develop web interface for leaderboards and stats
2. Add more question sources (TV Shows, Music, etc.)
3. Implement adaptive difficulty based on player performance

## Active Decisions and Considerations
- Using a common interface (`QuestionSource`) for all question types to ensure consistent handling
- Player tracking is automatic but doesn't require registration
- Tournament participation happens automatically when players answer during a tournament
- Database schema designed to support analytics and future web interface

## Important Patterns and Preferences
- All image processing flows through the `ImagePreparer` regardless of source
- Question sources determine if their media requires processing
- Player identification is based on BlueSky handles
- Database operations use context managers to ensure proper connection handling

## Learnings and Project Insights
- Abstract interfaces make adding new question types straightforward
- The random selection between question sources keeps the game fresh
- SQLite provides sufficient performance for expected usage levels
- Fuzzy matching with configurable thresholds works well across different question types
