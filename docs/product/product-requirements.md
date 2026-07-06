# Product Requirements Document (PRD)

# Project

FinSight AI

---

# Executive Summary

FinSight AI is an AI-powered investment intelligence platform designed to help retail investors make informed decisions using real-time financial data, machine learning predictions, explainable AI, and natural language insights.

Rather than acting as a financial advisor, FinSight AI serves as an intelligent decision-support system by combining quantitative analysis with qualitative market information.

---

# Problem Statement

Retail investors often rely on fragmented sources of information:

- Stock market websites
- Financial news
- YouTube
- Reddit
- Technical indicators
- Company reports

This creates information overload and makes investment decisions difficult.

Existing platforms rarely combine:

- portfolio management
- AI explanations
- machine learning predictions
- sentiment analysis
- financial news

into one unified experience.

---

# Vision

Provide institutional-quality investment intelligence to everyday investors through transparent AI-powered analytics.

---

# Target Users

## Primary

Retail investors

Age: 18–45

Interested in:

- Stock investing
- ETFs
- Long-term investing
- Portfolio management

---

## Secondary

Students

Finance enthusiasts

Data scientists

Researchers

Machine learning practitioners

---

# Goals

- Simplify investment research
- Improve financial literacy
- Explain predictions instead of treating AI as a black box
- Centralize financial information
- Build trust through transparency

---

# Non-Goals

FinSight AI will NOT

- execute trades
- guarantee profits
- provide legal financial advice
- replace licensed investment advisors

---

# Functional Requirements

## Authentication

- User registration
- Login
- JWT authentication
- Password hashing
- Profile management

---

## Portfolio

Users can

- create portfolios
- add holdings
- edit holdings
- remove holdings
- calculate gains/losses

---

## Watchlist

Users can

- follow stocks
- remove stocks
- receive market summaries

---

## Market Data

Display

- stock prices
- historical prices
- daily movement
- volume
- market capitalization

---

## News

Display

- company news
- market news
- AI-generated summaries

---

## Sentiment Analysis

Analyze

- news
- financial headlines

Display

- Bullish
- Neutral
- Bearish

---

## Machine Learning

Predict

- short-term movement
- confidence score

Explain

- feature importance
- prediction reasoning

---

## AI Assistant

Users can ask questions like

"What happened to NVIDIA today?"

"Should I add Apple to my watchlist?"

The assistant should answer using available platform data and clearly state when it is expressing an analysis rather than a factual event.

---

# Non-Functional Requirements

- Responsive UI
- Secure authentication
- Fast API response
- Scalable architecture
- Modular design
- Test coverage
- Docker support
- Cloud deployment

---

# Success Metrics

- API latency under 300 ms for common requests
- 90%+ backend test coverage goal
- Responsive dashboard
- Stable deployment
- Clear AI explanations

---

# MVP Scope

Version 1 includes

- Authentication
- Portfolio
- Watchlist
- Market data
- News
- Sentiment
- ML predictions
- AI assistant

Everything else is future work.