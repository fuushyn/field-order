const { createWorker } = require('tesseract.js');
const path = require('path');

async function main() {
  const imagePath = process.argv[2];
  if (!imagePath) {
    console.error('Usage: node ocr_service.js <image_path>');
    process.exit(1);
  }

  const worker = await createWorker('eng', 1, {
    cachePath: '/tmp/tessdata',
    langPath: '/tmp/tessdata',
    logger: () => {}
  });

  try {
    const { data: { text, confidence } } = await worker.recognize(imagePath);
    console.log(JSON.stringify({ text: text.trim(), confidence }));
  } finally {
    await worker.terminate();
  }
}

main().catch(err => {
  console.error(JSON.stringify({ error: err.message }));
  process.exit(1);
});
