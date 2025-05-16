# Active Context: BlueTrivia

## Current Work Focus

We are currently implementing a web-based frontend for BlueTrivia that provides administrative controls and public statistics interfaces. The frontend is built with FastAPI and connects to the existing SQLite database. Additionally, we are expanding the functionality to support tournaments and comprehensive player statistics.

## Recent Changes

- Developed a FastAPI-based frontend with two main components:
  - Admin interface for managing tournaments and trivia questions
  - Public statistics interface showing leaderboards and game performance
- Enhanced database schema to support:
  - Tournament management (duration, question distribution, bonus points)
  - Player statistics tracking
  - Round results with position-based scoring
- Implemented a main dashboard showing:
  - Overall game statistics (total rounds, player count, success rates)
  - Recent round winners
  - Active tournaments with progress tracking
  - Leaderboards (all-time, tournament-specific, and monthly)
- Added database migration logic to handle missing columns:
  - Added `duration_days`, `questions_per_day`, `source_distribution`, etc. to tournaments table
  - Added `image_url` to trivia_questions table
- Created a simple authentication system for the admin interface

## Next Steps

### Short-term Goals

1. Complete testing of the frontend implementation

   - Test database connection reliability across different environments
   - Verify proper rendering of statistics and leaderboards
   - Ensure tournament creation and management works correctly

2. Fix remaining database schema issues

   - Ensure backward compatibility with existing data
   - Complete implementation of tournament results tracking
   - Optimize database queries for performance

3. Refine the user interface

   - Improve mobile responsiveness
   - Add data visualization for statistics
   - Implement real-time updates for active games

4. Link frontend more tightly with core game functionality
   - Allow tournament parameters to influence game behavior
   - Ensure changes in admin UI properly affect game execution

### Medium-term Goals

1. Extend the round time from test mode (1 minute) to production mode (30 minutes)
2. Complete the tournament functionality implementation
3. Add more comprehensive statistics and player profiles
4. Implement user authentication for player statistics

## Active Decisions and Considerations

- Frontend implementation is separate from core game logic to avoid disruptions
- Admin interface has minimal authentication for testing purposes (will be enhanced later)
- Database schema migrations are designed to be non-destructive to existing data
- Frontend connects directly to the SQLite database rather than through an API layer
- Using Bootstrap for UI to expedite development while maintaining mobile responsiveness

## Important Patterns and Preferences

- FastAPI for the web framework due to its performance and Python compatibility
- Jinja2 templates for server-side rendering of HTML
- Direct database access through SQLite connections
- Tabbed interfaces for different views of the same data (e.g., leaderboards)
- Error handling that gracefully degrades when data is missing

## Learnings and Project Insights

- SQLite's ALTER TABLE limitations require careful database migration planning
- Frontend integration revealed some gaps in the database schema design
- FastAPI's dependency injection system works well for database connections
- Bootstrap provides sufficient styling for admin interfaces with minimal custom CSS
- The dashboard-style main page effectively communicates the game's current status
- Direct database connections work for now but may need an API layer as complexity grows
