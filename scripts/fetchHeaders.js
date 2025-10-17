const { request: playwrightRequest } = require('playwright');

async function run() {
  const url = process.argv[2];
  if (!url) {
    console.error('Usage: node scripts/fetchHeaders.js <url>');
    process.exit(1);
  }

  const context = await playwrightRequest.newContext({
    ignoreHTTPSErrors: true,
    extraHTTPHeaders: {
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
      'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
    }
  });

  const response = await context.get(url);
  const headers = response.headers();
  const cookies = await context.storageState();

  const output = {
    status: response.status(),
    headers,
    cookies
  };

  console.log(JSON.stringify(output, null, 2));
  await context.dispose();
}

run().catch(error => {
  console.error(error);
  process.exit(1);
});
