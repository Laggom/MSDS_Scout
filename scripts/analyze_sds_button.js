#!/usr/bin/env node
/**
 * Analyze SDS download mechanism on Sigma-Aldrich product page
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

async function analyzePage(url) {
  console.log(`\n${'='.repeat(70)}`);
  console.log(`Analyzing: ${url}`);
  console.log('='.repeat(70));

  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext({
    locale: 'ko-KR',
  });

  const page = await context.newPage();

  // Capture network requests
  const sdsRequests = [];
  page.on('request', request => {
    const url = request.url();
    if (url.includes('sds') || url.includes('SDS') || url.includes('.pdf')) {
      sdsRequests.push({
        url: url,
        method: request.method(),
        postData: request.postData()
      });
      console.log(`📤 SDS REQUEST: ${request.method()} ${url}`);
    }
  });

  page.on('response', async response => {
    const url = response.url();
    if (url.includes('sds') || url.includes('SDS') || url.includes('.pdf')) {
      console.log(`📥 SDS RESPONSE: ${response.status()} ${url}`);

      if (response.status() === 200 && response.headers()['content-type']?.includes('pdf')) {
        try {
          const buffer = await response.body();
          const filename = `sds_${Date.now()}.pdf`;
          const filepath = path.join(__dirname, '..', 'data', 'sds_aldrich', filename);
          fs.mkdirSync(path.dirname(filepath), { recursive: true });
          fs.writeFileSync(filepath, buffer);
          console.log(`💾 Saved PDF: ${filepath}`);
        } catch (e) {
          console.log(`❌ Could not save PDF: ${e.message}`);
        }
      }
    }
  });

  try {
    await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
    console.log('✓ Page loaded');

    // Wait for page to fully render
    await page.waitForTimeout(3000);

    // Find all SDS-related elements
    const sdsElements = await page.evaluate(() => {
      const elements = [];

      // Search for elements containing 'SDS' text
      const allElements = Array.from(document.querySelectorAll('*'));
      for (const el of allElements) {
        const text = el.textContent || '';
        const ariaLabel = el.getAttribute('aria-label') || '';

        if ((text.match(/SDS|safety.*data/i) || ariaLabel.match(/SDS|safety.*data/i)) && el.offsetParent !== null) {
          elements.push({
            tag: el.tagName,
            text: text.substring(0, 100),
            href: el.href || el.getAttribute('href'),
            'aria-label': ariaLabel,
            id: el.id,
            className: el.className,
            'data-testid': el.getAttribute('data-testid')
          });
        }
      }

      return elements.slice(0, 20);
    });

    console.log(`\\n📋 Found ${sdsElements.length} SDS-related elements:`);
    sdsElements.forEach((el, i) => {
      console.log(`\\n[${i + 1}] ${el.tag}`);
      console.log(`  Text: ${el.text}`);
      console.log(`  Href: ${el.href}`);
      console.log(`  ID: ${el.id}`);
      console.log(`  Aria-label: ${el['aria-label']}`);
      console.log(`  Data-testid: ${el['data-testid']}`);
    });

    // Try to click SDS download button
    console.log('\\n🖱️  Attempting to click SDS button...');

    const selectors = [
      'a[href*="/sds/"]',
      'button[aria-label*="SDS"]',
      '[data-testid*="sds"]',
      'a:has-text("SDS")',
      'button:has-text("SDS")',
    ];

    for (const selector of selectors) {
      try {
        console.log(`  Trying selector: ${selector}`);
        await page.click(selector, { timeout: 2000 });
        console.log(`  ✓ Clicked!`);
        await page.waitForTimeout(3000);
        break;
      } catch (e) {
        console.log(`  ✗ Failed: ${e.message}`);
      }
    }

    console.log(`\\n📊 Total SDS requests captured: ${sdsRequests.length}`);

    // Save results
    const outputPath = path.join(__dirname, '..', 'data', 'sds_analysis.json');
    fs.writeFileSync(outputPath, JSON.stringify({
      url,
      elements: sdsElements,
      requests: sdsRequests
    }, null, 2));
    console.log(`\\n💾 Analysis saved to: ${outputPath}`);

    await page.waitForTimeout(5000);

  } catch (error) {
    console.log(`❌ Error: ${error.message}`);
  } finally {
    await browser.close();
  }
}

async function main() {
  const urls = [
    'https://www.sigmaaldrich.com/KR/ko/product/sigald/34873', // Success
  ];

  for (const url of urls) {
    await analyzePage(url);
  }
}

main().catch(error => {
  console.error(error);
  process.exit(1);
});
