#!/bin/bash

# 백엔드 실행 (백그라운드)
echo "=> Starting Backend (FastAPI)..."
python3 main.py &
BACKEND_PID=$!

# 프론트엔드 실행 (Vite)
echo "=> Starting Frontend (Vite)..."
# frontend 폴더를 루트로 하여 npx vite 실행
npx -y vite frontend --port 3000

# 종료 시 백엔드 프로세스도 종료
kill $BACKEND_PID
