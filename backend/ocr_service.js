const { createWorker } = require('tesseract.js');
const fs = require('fs');

async function main() {
  const imagePath = process.argv[2];
  if (!imagePath || !fs.existsSync(imagePath)) {
    console.error(JSON.stringify({ error: `File not found: ${imagePath}` }));
    process.exit(1);
  }
  const worker = await createWorker('eng', 1, { cachePath: '/tmp/tessdata', logger: () => {} });
  try {
    const { data: { text, confidence } } = await worker.recognize(imagePath);
    console.log(JSON.stringify({ text: text.trim(), confidence }));
  } catch (err) {
    console.error(JSON.stringify({ error: err.message }));
    process.exit(1);
  } finally {
    await worker.terminate();
  }
}

main().catch(err => { console.error(JSON.stringify({ error: err.message })); process.exit(1); });
