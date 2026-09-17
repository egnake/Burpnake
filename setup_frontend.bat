@echo off
set "NODE_PATH=C:\Program Files\nodejs"
set "PATH=%NODE_PATH%;%PATH%"

echo Node.js sürümü:
"%NODE_PATH%\node.exe" -v

echo React (Vite) projesi oluşturuluyor...
call "%NODE_PATH%\npm.cmd" create vite@latest frontend -- --template react

echo Klasöre giriliyor ve bağımlılıklar kuruluyor...
cd frontend
call "%NODE_PATH%\npm.cmd" install

echo TailwindCSS kuruluyor...
call "%NODE_PATH%\npm.cmd" install -D tailwindcss postcss autoprefixer
call "%NODE_PATH%\npx.cmd" tailwindcss init -p

echo Ekstra paketler kuruluyor (axios, react-router, lucide vb.)...
call "%NODE_PATH%\npm.cmd" install axios react-router-dom lucide-react clsx tailwind-merge

echo İşlem tamamlandı!
