const fs = require('fs');
const { createCanvas } = require('canvas');

const sizes = [16, 32, 48, 64, 128, 256];

function drawIcon(ctx, size) {
  const gradient = ctx.createRadialGradient(size/2, size/2, 0, size/2, size/2, size/2);
  gradient.addColorStop(0, '#ff1a00');
  gradient.addColorStop(1, '#0a0000');
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, size, size);

  const fontSize = Math.floor(size * 0.39);
  ctx.font = `bold ${fontSize}px "Arial Black", sans-serif`;
  ctx.fillStyle = '#ff1a00';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.shadowColor = '#ff1a00';
  ctx.shadowBlur = Math.floor(size * 0.08);
  ctx.fillText('U', size/2, size/2 + fontSize * 0.1);
}

function main() {
  // Generate PNG for each size
  for (const size of sizes) {
    const canvas = createCanvas(size, size);
    const ctx = canvas.getContext('2d');
    drawIcon(ctx, size);
    const buffer = canvas.toBuffer('image/png');
    fs.writeFileSync(`C:/ultron/ultron/public/icon-${size}.png`, buffer);
    console.log(`Generated icon-${size}.png`);
  }

  // Generate 256x256 as main icon.png
  const mainCanvas = createCanvas(256, 256);
  const mainCtx = mainCanvas.getContext('2d');
  drawIcon(mainCtx, 256);
  const mainBuffer = mainCanvas.toBuffer('image/png');
  fs.writeFileSync('C:/ultron/ultron/public/icon.png', mainBuffer);
  console.log('Generated icon.png (256x256)');

  // Generate ICO file with multiple sizes
  const icoBuffers = [];
  let icoOffset = 6 + sizes.length * 16;
  
  for (const size of sizes) {
    const canvas = createCanvas(size, size);
    const ctx = canvas.getContext('2d');
    drawIcon(ctx, size);
    const buffer = canvas.toBuffer('image/png');
    icoBuffers.push(buffer);
  }

  // Write ICO file
  const icoHeader = Buffer.alloc(6);
  icoHeader.writeUInt16LE(0, 0); // Reserved
  icoHeader.writeUInt16LE(1, 2); // Type 1 = ICO
  icoHeader.writeUInt16LE(sizes.length, 4); // Number of images

  const entries = [];
  for (let i = 0; i < sizes.length; i++) {
    const size = sizes[i];
    const buffer = icoBuffers[i];
    const entry = Buffer.alloc(16);
    entry.writeUInt8(size === 256 ? 0 : size, 0);
    entry.writeUInt8(size === 256 ? 0 : size, 1);
    entry.writeUInt8(0, 2); // Color count
    entry.writeUInt8(0, 3); // Reserved
    entry.writeUInt16LE(1, 4); // Planes
    entry.writeUInt16LE(32, 6); // Bit count
    entry.writeUInt32LE(buffer.length, 8);
    entry.writeUInt32LE(6 + sizes.length * 16 + icoBuffers.slice(0, i).reduce((a, b) => a + b.length, 0), 12);
    entries.push(entry);
  }

  const icoFile = Buffer.concat([icoHeader, ...entries, ...icoBuffers]);
  fs.writeFileSync('C:/ultron/ultron/public/icon.ico', icoFile);
  console.log('Generated icon.ico');
  console.log('All icons generated successfully!');
}

main();