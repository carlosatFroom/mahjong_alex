# Mahjong AI Tutor - Product Requirements Document

## Project Overview

**Product Name:** Mahjong AI Tutor  
**Project Lead:** Carlos  
**Stakeholder:** Alex (Non-profit website owner)  
**Version:** 1.0  
**Date:** June 30, 2025

## Executive Summary

A proof-of-concept AI-powered Mahjong tutor that analyzes board states through images and provides strategic guidance to help players improve their skills. The system will be integrated as a chat interface on Alex's non-profit website, utilizing cost-effective self-hosted LLM solutions.

## Problem Statement

Mahjong players, particularly beginners and intermediate players, struggle to understand optimal strategies and decision-making during gameplay. Traditional learning methods are limited to static resources or expensive human tutoring, creating a gap for accessible, real-time strategic guidance.

## Goals & Objectives

### Primary Goals
- Create an AI tutor that can analyze Mahjong board states from images
- Provide strategic advice and explanations for move recommendations
- Integrate seamlessly into Alex's existing website as a chat interface
- Maintain cost-effectiveness for non-profit operation

### Success Metrics
- Successful image recognition and board state analysis (>90% accuracy)
- Meaningful strategic advice generation
- Smooth chat interface integration
- System operational cost under $50/month

## Target Users

### Primary Users
- **Beginner Mahjong players** who know basic tiles and rules but need strategic guidance
- **Intermediate players** seeking to improve their decision-making skills

### User Personas
- **Learning Lucy**: New to Mahjong, knows tiles but struggles with strategy
- **Improving Ian**: Plays regularly but wants to understand advanced tactics

## Technical Requirements

### Core Features (MVP)

#### 1. Image Analysis System
- **Input**: Player uploads photo of their tiles and visible board state
- **Processing**: LLM with vision capabilities analyzes the image
- **Output**: Structured understanding of current game state

#### 2. Strategic AI Advisor
- **Analysis**: Evaluate current hand and board situation
- **Recommendations**: Suggest optimal moves with clear reasoning
- **Education**: Explain strategic concepts and principles

#### 3. Chat Interface
- **Integration**: Embed chat widget in Alex's website
- **User Experience**: Conversational interface for image upload and advice
- **History**: Maintain session context for follow-up questions

### Technical Architecture

#### Backend Infrastructure
- **LLM Platform**: Ollama (self-hosted on Carlos's server)
- **Model Requirements**: Vision-capable model (e.g., LLaVA, Bakllava)
- **API Framework**: FastAPI or Flask for REST endpoints
- **Image Processing**: PIL/OpenCV for preprocessing

#### Frontend Integration
- **Chat Widget**: Embeddable JavaScript component
- **File Upload**: Drag-and-drop image upload functionality
- **Responsive Design**: Mobile-friendly interface

#### Hosting & Deployment
- **Server**: Carlos's personal server infrastructure
- **Container**: Docker for consistent deployment
- **Reverse Proxy**: Nginx for web serving
- **SSL**: Let's Encrypt for secure connections

### Technical Assumptions & Validations Needed

1. **LLM Mahjong Knowledge**: Assumption that modern LLMs understand Mahjong rules and strategy
   - *Validation Required*: Test selected model's Mahjong knowledge depth
   
2. **Vision Capability**: Assumption that vision models can accurately identify Mahjong tiles
   - *Validation Required*: Test tile recognition accuracy with various lighting/angles

3. **Performance**: Assumption that self-hosted setup can handle expected load
   - *Validation Required*: Load testing with image processing

## Feature Specifications

### Phase 1: Proof of Concept (MVP)
- Basic image upload and analysis
- Simple move recommendations
- Text-based chat interface
- Manual image preprocessing if needed

### Phase 2: Enhancement
- Improved tile recognition accuracy
- Advanced strategic explanations
- Game state tracking across multiple images
- Better UI/UX for chat integration

### Phase 3: Future Expansion
- **Voice Interaction**: Add VAD (Voice Activity Detection) for spoken queries
- **Real-time Analysis**: Live video feed analysis during games
- **Learning Paths**: Structured tutorials based on player progress
- **Multi-language Support**: Expand beyond English

## Non-Functional Requirements

### Performance
- Image analysis response time: <30 seconds
- Chat response time: <5 seconds for text-only queries
- Uptime: 95% availability during peak hours

### Security
- Secure image upload handling
- No persistent storage of user images
- HTTPS encryption for all communications

### Scalability
- Initial support for 10-20 concurrent users
- Horizontal scaling capability for future growth

### Cost Constraints
- Monthly operational cost: <$50
- Leverage existing server infrastructure
- Minimize third-party service dependencies

## Risk Assessment

### Technical Risks
- **LLM Accuracy**: Model may provide incorrect Mahjong advice
  - *Mitigation*: Extensive testing and model fine-tuning if needed
  
- **Image Recognition**: Poor tile identification in various conditions
  - *Mitigation*: Implement image preprocessing and user feedback loop

### Operational Risks
- **Server Reliability**: Single point of failure on personal server
  - *Mitigation*: Implement monitoring and backup deployment options

- **Cost Overrun**: Unexpected resource consumption
  - *Mitigation*: Implement usage monitoring and rate limiting

## Success Criteria

### MVP Success
- [ ] Successfully analyze uploaded Mahjong board images
- [ ] Provide relevant strategic advice with explanations
- [ ] Integrate chat widget into Alex's website
- [ ] Achieve <$25/month operational cost

### Long-term Success
- [ ] Positive user feedback on advice quality
- [ ] Demonstrated player improvement metrics
- [ ] Stable system operation (>95% uptime)
- [ ] Successful voice integration (Phase 3)

## Timeline

### Phase 1 (MVP): 4-6 weeks
- Week 1-2: LLM setup and Mahjong knowledge validation
- Week 3-4: Image analysis pipeline development
- Week 5-6: Chat interface and website integration

### Phase 2 (Enhancement): 2-3 weeks
- UI/UX improvements and advanced features

### Phase 3 (Voice): 3-4 weeks
- VAD implementation and voice interaction

## Resource Requirements

### Development Resources
- Carlos: Full-stack development and DevOps
- Alex: Requirements feedback and website integration testing

### Infrastructure
- Server capacity for LLM hosting
- Domain and SSL certificate costs
- Basic monitoring tools

## Appendix

### Technical Research Items
1. Evaluate Ollama-compatible vision models for Mahjong tile recognition
2. Research Mahjong strategy databases for training/validation
3. Investigate WebRTC for future voice integration
4. Assess chat widget frameworks for easy website integration

### Open Questions
1. What specific Mahjong variant should be prioritized? (Riichi, American, etc.)
2. What is Alex's current website technology stack?
3. Are there any content filtering requirements for the non-profit context?
4. What analytics/usage tracking is desired?