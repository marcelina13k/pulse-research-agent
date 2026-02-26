# Architecture Decisions

## NewsAPI removed from retrieval pipeline
NewsAPI free tier restricts the /everything endpoint to paid plans only.
Removed from pipeline. Tavily covers web and news sources sufficiently
for development and testing. NewsAPI can be re-added on a paid plan
as a secondary news source to increase signal volume.