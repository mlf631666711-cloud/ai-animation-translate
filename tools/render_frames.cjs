/* render_frames.cjs —— 通用逐帧渲染（HTML → PNG 序列）
 *
 * 用法：
 *   node tools/render_frames.cjs --page work/shot1_en.html --out work/frames --dur 17.16 --dpr 2
 *   node tools/render_frames.cjs --page http://127.0.0.1:8100/x.html --out frames --dur 12.3 --fps 30
 *
 * 约定（页面必须做到其中一条）：
 *   window.__renderAt(t)   —— 推荐，确定性逐帧
 *   window.seek(t)         —— 老页面兼容
 *
 * 依赖：npm i puppeteer-core
 */
const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');
const puppeteer = require('puppeteer-core');

function arg(name, def) {
  const i = process.argv.indexOf('--' + name);
  return i > 0 ? process.argv[i + 1] : def;
}
const PAGE = arg('page');
const OUT = arg('out', 'frames');
const DUR = parseFloat(arg('dur', '0'));
const FPS = parseFloat(arg('fps', '30'));
const DPR = parseFloat(arg('dpr', '2'));
const W = parseInt(arg('w', '1920'), 10);
const H = parseInt(arg('h', '1080'), 10);
const READY = arg('ready', '');
const HOOK = arg('hook', '');
const CHROME = arg('chrome', 'C:/Program Files/Google/Chrome/Application/chrome.exe');

if (!PAGE) { console.error('缺 --page'); process.exit(2); }
if (!(DUR > 0)) { console.error('缺 --dur（秒）'); process.exit(2); }

(async () => {
  const t0 = Date.now();
  const N = Math.round(DUR * FPS);
  fs.mkdirSync(OUT, { recursive: true });

  const browser = await puppeteer.launch({
    executablePath: CHROME,
    headless: 'new',
    args: ['--no-sandbox', '--disable-dev-shm-usage', '--hide-scrollbars',
           '--force-color-profile=srgb', '--font-render-hinting=none', '--allow-file-access-from-files']
  });
  const page = await browser.newPage();
  await page.setViewport({ width: W, height: H, deviceScaleFactor: DPR });

  const errs = [];
  page.on('pageerror', e => errs.push('PAGEERROR: ' + e.message));
  page.on('requestfailed', r => errs.push('REQFAIL: ' + r.url().slice(-70)));
  page.on('response', r => { if (r.status() >= 400 && !/favicon/.test(r.url())) errs.push('HTTP' + r.status() + ': ' + r.url().slice(-70)); });

  const url = /^https?:/.test(PAGE) ? PAGE : pathToFileURL(path.resolve(PAGE)).href;
  await page.goto(url, { waitUntil: 'networkidle0', timeout: 120000 });
  await page.evaluate(() => document.fonts && document.fonts.ready);
  if (READY) {
    await page.waitForFunction(`window[${JSON.stringify(READY)}] === true`, { timeout: 120000 })
      .catch(() => errs.push('READY 超时：' + READY));
  }

  // 用哪个驱动函数
  const hook = await page.evaluate(h => {
    if (h && typeof window[h] === 'function') return h;
    if (typeof window.__renderAt === 'function') return '__renderAt';
    if (typeof window.seek === 'function') return 'seek';
    return '';
  }, HOOK);
  if (!hook) { console.error('页面既没有 __renderAt(t) 也没有 seek(t)'); await browser.close(); process.exit(2); }

  // 规格自检：dpr / 画布尺寸（这段专治"忘了 dpr=2 却以为出了 4K"）
  const info = await page.evaluate(() => {
    const el = document.querySelector('#stage') || document.body;
    return { dpr: window.devicePixelRatio, w: el.getBoundingClientRect().width, h: el.getBoundingClientRect().height };
  });
  console.log(`页面 ${info.w}×${info.h} · dpr=${info.dpr} · 输出 ${Math.round(info.w * info.dpr)}×${Math.round(info.h * info.dpr)}`);
  console.log(`逐帧：${N} 帧（${DUR}s × ${FPS}fps）→ ${OUT}`);
  if (Math.abs(info.w - W) > 1) { console.error('✗ 页面宽度与 --w 不符'); await browser.close(); process.exit(2); }

  let n = 0;
  for (let f = 0; f < N; f++) {
    await page.evaluate((h, t) => window[h](t), hook, f / FPS);
    await page.screenshot({
      path: path.join(OUT, 'f' + String(++n).padStart(4, '0') + '.png'),
      clip: { x: 0, y: 0, width: W, height: H }
    });
    if (n % 100 === 0) console.log(`  ${n}/${N}  ${((Date.now() - t0) / 1000).toFixed(0)}s`);
  }
  await browser.close();
  if (errs.length) { console.log('⚠ 页面告警 ' + errs.length + ' 条：'); errs.slice(0, 5).forEach(e => console.log('   ' + e)); }
  const sec = (Date.now() - t0) / 1000;
  console.log(`完成 ${n} 帧 · ${sec.toFixed(1)}s · ${(sec / n).toFixed(3)}s/帧`);
})();
