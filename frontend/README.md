# Study AI Frontend
Next.js frontend for the Kafka System study-group experience.
## Run
npm install
cp .env.example .env.local
npm run dev
Open http://localhost:3000.
Set NEXT_PUBLIC_API_URL to the FastAPI API root. The current frontend demo bypasses Google OAuth and creates a local demo session when the Google-style login button is clicked.
## Surfaces
- 3D landing page
- Study AI demo sign-in (Google button UI)
- Study-group creation
- WebSocket group chat
- Media uploads
- AI companion surface
- Logout/account session flow