#!/usr/bin/env node
const { request: playwrightRequest } = require('playwright');
const fs = require('fs/promises');
const path = require('path');

async function main() {
  const [, , url, outputPath, referer = '', acceptLanguage = ''] = process.argv;

  if (!url || !outputPath) {
    console.error(
      'Usage: node scripts/download_sds_with_playwright.js <url> <outputPath> [referer] [acceptLanguage]'
    );
    process.exit(1);
  }

  const context = await playwrightRequest.newContext({
    ignoreHTTPSErrors: true,
  });

  const headers = {
    Accept: 'application/pdf,application/octet-stream;q=0.9,*/*;q=0.8',
  };

  if (referer) {
    headers.Referer = referer;
  }

  if (acceptLanguage) {
    headers['Accept-Language'] = acceptLanguage;
  }

  const response = await context.get(url, {
    maxRedirects: 10,
    headers,
    timeout: 120000,
  });

  const status = response.status();
  const responseHeaders = response.headers();
  const contentType = responseHeaders['content-type'] || '';
  const isPdf = contentType.toLowerCase().includes('pdf');
  const shouldSave = status === 200 && isPdf;

  let body;
  if (shouldSave) {
    body = await response.body();
  }

  await context.dispose();

  if (shouldSave && body) {
    await fs.mkdir(path.dirname(outputPath), { recursive: true });
    await fs.writeFile(outputPath, body);
  }

  console.log(
    JSON.stringify(
      {
        status,
        headers: responseHeaders,
        outputPath: path.resolve(outputPath),
      },
      null,
      2
    )
  );
}

main().catch((error) => {
  console.error(error && error.stack ? error.stack : String(error));
  process.exit(1);
});
