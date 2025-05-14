# Product Context: Bsky Movie Guesser

## Why This Project Exists

The Bsky Movie Guesser bot creates an engaging, interactive experience for BlueSky users by providing a fun, low-barrier game that anyone can participate in. The project aims to:

1. Foster community engagement on the BlueSky platform
2. Provide entertainment through movie trivia
3. Create a recurring activity that users look forward to
4. Demonstrate creative bot usage in the BlueSky ecosystem

## Problems It Solves

- Lack of interactive games native to BlueSky
- Limited automated content on BlueSky compared to other platforms
- Need for accessible community activities that don't require special knowledge
- Desire for engaging content that's both visual and intellectual

## How It Should Work

From the user perspective:

1. Users discover a post with four partially censored movie images
2. The post indicates a 30-minute window to submit guesses
3. Users reply with their guess of the movie title
4. After 30 minutes, users see a follow-up post showing:
   - The correct movie title
   - Success percentage (% of correct guesses)
   - Total number of attempts
5. A new round begins automatically

From the bot perspective:

1. Select a random movie with sufficient images
2. Process images (optimize, censor, watermark)
3. Create post with the processed images
4. Monitor replies for the time window
5. Evaluate guesses using fuzzy matching
6. Calculate and post results
7. Begin next round

## User Experience Goals

- **Accessibility**: Easy to understand and participate
- **Fairness**: Reasonable difficulty level and proper evaluation of answers
- **Consistency**: Regular posting schedule and reliable evaluation
- **Engagement**: Visually appealing posts that attract participation
- **Community**: Foster friendly competition and movie discussions
- **Satisfaction**: Clear feedback on results and acknowledgment of participation

## Target Audience

- BlueSky users with interest in movies
- Casual gamers looking for quick, easy-to-join activities
- Movie enthusiasts who enjoy testing their knowledge
- General BlueSky community looking for interactive content
