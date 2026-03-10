const fs = require('fs');
const path = require('path');

const PUBLIC = path.join(__dirname, 'public');

// Clean and create output dir
if (fs.existsSync(PUBLIC)) fs.rmSync(PUBLIC, { recursive: true });
fs.mkdirSync(PUBLIC, { recursive: true });

// Copy images
const imgSrc = path.join(__dirname, 'images');
const imgDest = path.join(PUBLIC, 'images');
fs.mkdirSync(imgDest, { recursive: true });
for (const file of fs.readdirSync(imgSrc)) {
  fs.copyFileSync(path.join(imgSrc, file), path.join(imgDest, file));
}

// Copy CNAME
fs.copyFileSync(path.join(__dirname, 'CNAME'), path.join(PUBLIC, 'CNAME'));

// For now, just copy index.html
fs.copyFileSync(path.join(__dirname, 'index.html'), path.join(PUBLIC, 'index.html'));

console.log('Build complete: public/index.html');
