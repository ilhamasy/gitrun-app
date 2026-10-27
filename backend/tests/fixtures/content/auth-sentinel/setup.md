# Setup & Configuration

## Local Environment

```bash
# 1. Install dependencies
npm install

# 2. Generate local RS256 keypair
npm run keys:gen

# 3. Start Redis dependency
docker run -d -p 6379:6379 redis:7-alpine

# 4. Run development server
npm run dev
```

Listening on `http://localhost:4000`.
