const AdmZip = require('adm-zip');
const path = require('path');
const fs = require('fs');

const src = path.join(__dirname, '..', 'examples', 'test_sample', 'test_sample');
const out = path.join(__dirname, '..', 'examples', 'test_sample.zip');

if (!fs.existsSync(src)) {
  console.error('Source not found:', src);
  process.exit(1);
}

function addDir(zip, dir, prefix = '') {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const e of entries) {
    const full = path.join(dir, e.name);
    const name = prefix ? `${prefix}/${e.name}` : e.name;
    if (e.isDirectory()) {
      addDir(zip, full, name);
    } else {
      const data = fs.readFileSync(full);
      const entryName = name.replace(/\\/g, '/');
      zip.addFile(entryName, data);
    }
  }
}

const zip = new AdmZip();
addDir(zip, src);
zip.writeZip(out);
console.log('Created', out);
