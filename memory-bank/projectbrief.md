# Project Brief: BlueTrivia

## Overview

BlueTrivia (formerly Bsky Movie Guesser) is a BlueSky social media bot that runs an automated trivia game with multiple question types. The bot posts questions (including partially censored movie images for movie trivia and text-based questions for general trivia), allows users to guess the answers, and then reports the results. The project now includes a web-based frontend for administration and public statistics.

## Core Requirements

### Game Mechanics

- Provide questions from multiple sources (movies, custom trivia, etc.)
- For movies: Post 4 partially censored images from the movie
- For trivia: Post text-based questions with optional images
- Allow configurable time window for users to guess via replies (currently 1 minute for testing)
- Evaluate guesses using fuzzy string matching with configurable threshold
- Report success percentage and total attempt statistics
- Track fastest correct responders and highlight them in results
- Automatically start new rounds after completion

### Technical Requirements

- Integrate with TMDB API for movie data and images
- Integrate with BlueSky API for social posting and interaction
- Process images (optimize, censor parts, add watermarks)
- Store game data and player statistics in SQLite database
- Run continuously and autonomously
- Respect BlueSky's 300 character post limit

### Frontend Requirements (New)

- Provide admin interface for tournament management
- Display public statistics and leaderboards
- Allow CRUD operations for trivia questions
- Show real-time game status and player rankings
- Connect to the existing SQLite database
- Support responsive design for mobile and desktop

## Future Expansion

- Advanced player scorecards and statistics tracking
- Full tournament functionality with scheduled rounds
- Enhanced web interface with user accounts
- Additional question sources and categories
- API-based integration with other services
