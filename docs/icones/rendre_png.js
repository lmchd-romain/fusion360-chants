// Rend chaque SVG de docs/icones/svg/<dossier>/ en PNG (taille exacte et @2x, fond transparent)
// dans EdgeBanding/ressources/<dossier>/, puis copie -dark en -dark_blue et -dark_gray.
// Usage (racine du dépôt) : node docs/icones/rendre_png.js
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const SVG = path.join(__dirname, 'svg');
const RES = path.join(__dirname, '..', '..', 'EdgeBanding', 'ressources');

function dossiers(d, rel = '') {
  let r = [];
  for (const n of fs.readdirSync(d)) {
    const p = path.join(d, n);
    if (fs.statSync(p).isDirectory()) {
      const sous = path.join(rel, n);
      if (fs.readdirSync(p).some(f => f.endsWith('.svg'))) r.push(sous);
      r = r.concat(dossiers(p, sous));
    }
  }
  return r;
}

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  for (const rel of dossiers(SVG)) {
    const src = path.join(SVG, rel), dst = path.join(RES, rel);
    fs.mkdirSync(dst, { recursive: true });
    for (const f of fs.readdirSync(src).filter(n => n.endsWith('.svg'))) {
      const taille = parseInt(f, 10);
      const svg = fs.readFileSync(path.join(src, f), 'utf8');
      for (const echelle of [1, 2]) {
        const px = taille * echelle;
        await page.setViewportSize({ width: px, height: px });
        await page.setContent(`<html><body style="margin:0;background:transparent">${svg.replace('<svg ', `<svg width="${px}" height="${px}" style="display:block" `)}</body></html>`);
        const base = f.replace('.svg', '');
        const nom = echelle === 1 ? base : base.replace(/^(\d+x\d+)/, '$1@2x');
        const sortie = path.join(dst, nom + '.png');
        await page.screenshot({ path: sortie, omitBackground: true, clip: { x: 0, y: 0, width: px, height: px } });
        if (nom.endsWith('-dark')) {
          for (const th of ['-dark_blue', '-dark_gray']) fs.copyFileSync(sortie, sortie.replace(/-dark\.png$/, th + '.png'));
        }
      }
    }
  }
  await browser.close();
  console.log('PNG rendus');
})();
