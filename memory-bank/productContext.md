# Product Context: BlueTrivia

## Why This Project Exists

The BlueTrivia bot creates an engaging, interactive experience for BlueSky users by providing a fun, low-barrier game that anyone can participate in. The project aims to:

1. Foster community engagement on the BlueSky platform
2. Provide entertainment through various trivia categories
3. Create a recurring activity that users look forward to
4. Demonstrate creative bot usage in the BlueSky ecosystem

## Problems It Solves

- Lack of interactive games native to BlueSky
- Limited automated content on BlueSky compared to other platforms
- Need for accessible community activities that don't require special knowledge
- Desire for engaging content that's both visual and intellectual

## How It Should Work

From the user perspective:

1. Users discover a post with a trivia question (either text-based or images)
2. The post indicates a time window to submit guesses (currently 1 minute for testing)
3. Users reply with their guess
4. After the time window, users see a follow-up post showing:
   - The correct answer
   - Success percentage (% of correct guesses)
   - Total number of attempts
   - Top performers who answered correctly first
5. A new round begins automatically

From the bot perspective:

1. Select a random question source (movie or trivia)
2. Get a question from the selected source
3. Process any media if needed (optimize, censor, watermark)
4. Create post with the question and any processed media
5. Monitor replies for the time window
6. Evaluate guesses using fuzzy matching
7. Calculate and post results, highlighting fastest correct answers
8. Begin next round

## User Experience Goals

- **Accessibility**: Easy to understand and participate
- **Fairness**: Reasonable difficulty level and proper evaluation of answers
- **Consistency**: Regular posting schedule and reliable evaluation
- **Engagement**: Visually appealing posts that attract participation
- **Community**: Foster friendly competition and knowledge sharing
- **Recognition**: Acknowledge fast and accurate responders
- **Satisfaction**: Clear feedback on results

## Target Audience

- BlueSky users with interest in trivia and games
- Casual gamers looking for quick, easy-to-join activities
- Movie enthusiasts who enjoy testing their knowledge
- General BlueSky community looking for interactive content
