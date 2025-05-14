# Project Brief: BlueTrivia

## Overview
BlueTrivia (formerly Bsky Movie Guesser) is a BlueSky social media bot that runs an automated trivia game with multiple question types. The bot posts questions (including partially censored movie images), allows users to guess the answers, and then reports the results.

## Core Requirements

### Game Mechanics
- Provide questions from multiple sources (movies, custom trivia, etc.)
- For movies: Post 4 partially censored images from the movie
- For trivia: Post text-based questions with optional images
- Allow 30-minute window for users to guess via replies
- Evaluate guesses using fuzzy string matching with configurable threshold
- Report success percentage and total attempt statistics
- Automatically start new rounds after completion

### Technical Requirements
- Integrate with TMDB API for movie data and images
- Integrate with BlueSky API for social posting and interaction
- Process images (optimize, censor parts, add watermarks)
- Store game data and player statistics in SQLite database
- Run continuously and autonomously

## Future Expansion
- Player scorecards and statistics tracking
- Tournament functionality with scheduled rounds
- Web interface for leaderboards and game statistics
