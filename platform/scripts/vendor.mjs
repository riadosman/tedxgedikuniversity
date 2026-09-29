import {copyFile,mkdir} from 'node:fs/promises';
await mkdir('static/vendor',{recursive:true});
await copyFile('node_modules/jsqr/dist/jsQR.js','static/vendor/jsQR.js');
await copyFile('node_modules/jsqr/LICENSE','static/vendor/jsQR.LICENSE');
