# StudySearch Frontend
Next.js frontend for the Kafka System study-group experience.
## Run
npm install
cp .env.example .env.local
npm run dev
Open http://localhost:3000.
Set NEXT_PUBLIC_GOOGLE_CLIENT_ID to the same Google web client ID accepted by FastAPI and NEXT_PUBLIC_API_URL to the API root.
## Surfaces
- 3D landing page
- Google-only authentication
- Study-group creation
- WebSocket group chat
- Media uploads
- AI companion surface
- Logout/account session flow