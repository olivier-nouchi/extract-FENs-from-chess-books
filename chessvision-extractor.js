const puppeteer = require('puppeteer');
const fs = require('fs');
const os = require('os');
const path = require('path');

// Find diagram positions by looking for specific patterns in the PDF
async function findDiagramsOnPage(iframeContent, pageNumber) {
  console.log(`🔍 Looking for diagrams on page ${pageNumber}...`);

  const diagrams = await iframeContent.evaluate((pageNum) => {
    const diagramData = [];
    const textLayer = document.querySelector('.textLayer');
    if (textLayer) {
      const textDivs = textLayer.querySelectorAll('div');
      textDivs.forEach(div => {
        const text = div.textContent.trim();
        if (/^\d{1,3}$/.test(text)) {
          const diagramNumber = parseInt(text);
          if (diagramNumber >= 1 && diagramNumber <= 999) {
            const rect = div.getBoundingClientRect();
            const diagramRect = {
              x: rect.x + 100,
              y: rect.y + 100,
              width: 200,
              height: 200,
              diagramNumber: diagramNumber
            };
            console.log(`Found potential diagram ${diagramNumber} at (${diagramRect.x}, ${diagramRect.y})`);
            diagramData.push(diagramRect);
          }
        }
      });
    }
    return diagramData;
  }, pageNumber);

  console.log(`📊 Found ${diagrams.length} potential diagram positions`);
  return diagrams;
}

// Click and extract FEN from diagram
async function extractFENFromDiagram(page, iframeContent, diagram) {
  try {
    console.log(`🎯 Clicking on diagram ${diagram.diagramNumber} at (${diagram.x}, ${diagram.y})`);

    const canvasWrapper = await page.$('.canvasWrapper');
    if (!canvasWrapper) throw new Error('canvasWrapper not found');

    const box = await canvasWrapper.boundingBox();
    if (!box) throw new Error('Bounding box for canvasWrapper not available');

    const clickX = box.x + diagram.x;
    const clickY = box.y + diagram.y;

    await page.mouse.click(clickX, clickY, { clickCount: 2 });
    console.log(`🖱️ Clicked at (${clickX}, ${clickY})`);

    await new Promise(resolve => setTimeout(resolve, 3000));

    const copyFenButton = await page.waitForSelector('button[title="Copy FEN"]', { timeout: 5000 }).catch(() => null);
    if (!copyFenButton) {
      console.log('❌ Copy FEN button not found - diagram might not have loaded');
      return null;
    }

    console.log('✅ Found Copy FEN button, clicking...');
    await copyFenButton.click();
    await new Promise(resolve => setTimeout(resolve, 1000));

    const fen = await page.evaluate(async () => {
      try {
        return await navigator.clipboard.readText();
      } catch (error) {
        console.log('Clipboard access failed:', error.message);
        return null;
      }
    });

    if (fen && fen.includes('/') && fen.length > 20) {
      console.log(`✅ Successfully extracted FEN: ${fen}`);
      return fen;
    } else {
      console.log(`❌ Invalid FEN received: "${fen}"`);
      return null;
    }
  } catch (error) {
    console.log(`❌ Error extracting FEN from diagram ${diagram.diagramNumber}: ${error.message}`);
    return null;
  }
}

async function findDifficultyBubbles(iframeContent, diagram) {
  return await iframeContent.evaluate((diagramInfo) => {
    const bubbles = [];
    const searchArea = {
      left: diagramInfo.x - 50,
      right: diagramInfo.x + 250,
      top: diagramInfo.y - 50,
      bottom: diagramInfo.y + 250
    };
    const textElements = document.querySelectorAll('.textLayer div');
    textElements.forEach(div => {
      const text = div.textContent.trim();
      const rect = div.getBoundingClientRect();
      if (rect.x >= searchArea.left && rect.x <= searchArea.right &&
          rect.y >= searchArea.top && rect.y <= searchArea.bottom &&
          /^[1-9]$/.test(text)) {
        const difficulty = parseInt(text);
        const styles = window.getComputedStyle(div);
        let bubbleType = 'unknown';
        const backgroundColor = styles.backgroundColor;
        const color = styles.color;
        if (backgroundColor === 'rgb(255, 255, 255)' || color === 'rgb(0, 0, 0)') {
          bubbleType = 'white';
        } else if (backgroundColor === 'rgb(0, 0, 0)' || color === 'rgb(255, 255, 255)') {
          bubbleType = 'black';
        }
        bubbles.push({ difficulty, bubbleType });
      }
    });
    if (bubbles.length === 0) {
      bubbles.push(
        { difficulty: 0, bubbleType: 'white' },
        { difficulty: 0, bubbleType: 'black' }
      );
    }
    return bubbles;
  }, diagram);
}

async function extractChessvisionFENsWorking(maxPositions = 50, startPage = 18, endPage = 20) {
  const targetUrl = 'https://ebook.chessvision.ai/documents/9ba30414043abe70c24a55ddfbcdbf69';
  const homeDir = os.homedir();
  const puppeteerProfileDir = path.join(homeDir, '.puppeteer_chrome_profile');
  if (!fs.existsSync(puppeteerProfileDir)) fs.mkdirSync(puppeteerProfileDir, { recursive: true });

  const browser = await puppeteer.launch({
    headless: false,
    defaultViewport: null,
    userDataDir: puppeteerProfileDir,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--start-maximized']
  });

  const page = await browser.newPage();
  try {
    await page.goto(targetUrl, { waitUntil: 'networkidle2' });
    await new Promise(resolve => setTimeout(resolve, 3000));

    const needsLogin = await page.evaluate(() => {
      return document.body.textContent.includes('Sign in') ||
             document.body.textContent.includes('Log in') ||
             document.querySelector('input[type="email"]') !== null;
    });

    if (needsLogin) {
      console.log('🔑 Please log in manually, then press Enter...');
      await new Promise(resolve => {
        process.stdin.once('data', async () => {
          await page.goto(targetUrl, { waitUntil: 'networkidle2' });
          await new Promise(resolve => setTimeout(resolve, 3000));
          resolve();
        });
      });
    }

    const context = browser.defaultBrowserContext();
    await context.overridePermissions(targetUrl, ['clipboard-read', 'clipboard-write']);

    const results = [];
    let processedDiagrams = new Set();

    for (let currentPage = startPage; currentPage <= endPage && results.length < maxPositions; currentPage++) {
      const iframe = await page.$('#iframe');
      if (!iframe) continue;

      const iframeContent = await iframe.contentFrame();
      if (!iframeContent) continue;

      const pageSet = await iframeContent.evaluate((pageNum) => {
        const pageInput = document.querySelector('input#pageNumber');
        if (pageInput) {
          pageInput.focus();
          pageInput.select();
          pageInput.value = pageNum.toString();
          pageInput.dispatchEvent(new Event('input', { bubbles: true }));
          pageInput.dispatchEvent(new Event('change', { bubbles: true }));
          pageInput.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
          return true;
        }
        return false;
      }, currentPage);

      if (!pageSet) continue;
      await new Promise(resolve => setTimeout(resolve, 4000));

      const freshIframe = await page.$('#iframe');
      if (!freshIframe) continue;
      const freshContent = await freshIframe.contentFrame();
      if (!freshContent) continue;

      const diagrams = await findDiagramsOnPage(freshContent, currentPage);

      for (const diagram of diagrams.slice(0, 4)) {
        if (results.length >= maxPositions) break;
        const diagramKey = `${currentPage}-${diagram.diagramNumber}`;
        if (processedDiagrams.has(diagramKey)) continue;

        const fen = await extractFENFromDiagram(page, freshContent, diagram);
        if (fen) {
          const bubbles = await findDifficultyBubbles(freshContent, diagram);
          bubbles.forEach(bubble => {
            const turn = bubble.bubbleType === 'white' ? 'white' : 'black';
            const finalFen = turn === 'white' ? fen.replace(/ [wb] /, ' w ') : fen.replace(/ [wb] /, ' b ');
            results.push({ diagramNumber: diagram.diagramNumber, fen: finalFen, turn, difficulty: bubble.difficulty, page: currentPage, method: 'visual_click' });
          });
          processedDiagrams.add(diagramKey);
        }
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
    }

    const timestamp = Date.now();
    const csvContent = [
      'diagram,FEN,turn,difficulty,page,method',
      ...results.map(r => `${r.diagramNumber},"${r.fen}",${r.turn},${r.difficulty},${r.page},${r.method}`)
    ].join('\n');
    const csvFilename = `chessvision_fens_working_${timestamp}.csv`;
    fs.writeFileSync(csvFilename, csvContent);
    console.log(`\n🎉 Extraction complete. File saved: ${csvFilename}`);
  } catch (error) {
    console.error('💥 Error:', error);
  } finally {
    await browser.close();
  }
}

(async () => {
  const start = Date.now();
  const results = await extractChessvisionFENsWorking(50, 18, 20);
  const duration = (Date.now() - start) / 1000;
  console.log(`⏱️  Total time: ${duration}s`);
})();
