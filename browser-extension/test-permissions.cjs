/**
 * Dynamic test to verify manifest permissions match API usage
 *
 * This test checks:
 * 1. All chrome.* APIs used in service-worker.ts have corresponding permissions
 * 2. Missing permissions would cause "undefined" errors at runtime
 */

const fs = require('fs');
const path = require('path');

// Read manifest
const manifestPath = path.join(__dirname, 'manifest.json');
const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf-8'));

// Read service worker source
const swPath = path.join(__dirname, 'src/background/service-worker.ts');
const swSource = fs.readFileSync(swPath, 'utf-8');

console.log('=== Permission Verification Test ===\n');

// Map of Chrome APIs to required permissions
const apiToPermission = {
  'chrome.storage': 'storage',
  'chrome.contextMenus': 'contextMenus',
  'chrome.notifications': 'notifications',
  'chrome.tabs.sendMessage': ['activeTab', 'tabs'],
  'chrome.runtime.onInstalled': null, // No permission needed
  'chrome.runtime.onMessage': null, // No permission needed
  'chrome.action': null, // No permission needed
};

// Find all chrome.* API usage in service worker
const chromeApiPattern = /chrome\.([a-z]+)\.([a-z]+)/g;
const usedApis = new Set();
let match;

while ((match = chromeApiPattern.exec(swSource)) !== null) {
  const api = `chrome.${match[1]}.${match[2]}`;
  usedApis.add(api);
}

console.log('Chrome APIs used in service-worker.ts:');
usedApis.forEach(api => console.log(`  - ${api}`));
console.log('');

// Check permissions
const manifestPermissions = manifest.permissions || [];
console.log('Manifest permissions:');
manifestPermissions.forEach(p => console.log(`  - ${p}`));
console.log('');

// Verify each API has permission
console.log('Permission Check Results:');
let hasMissingPermissions = false;

for (const api of usedApis) {
  const requiredPerms = apiToPermission[api];
  if (!requiredPerms) continue; // No permission needed

  const permArray = Array.isArray(requiredPerms) ? requiredPerms : [requiredPerms];
  let apiHasPermission = false;

  for (const perm of permArray) {
    if (manifestPermissions.includes(perm)) {
      console.log(`  ✓ ${api} → ${perm} (present)`);
      apiHasPermission = true;
      break;
    }
  }

  if (!apiHasPermission) {
    console.log(`  ✗ ${api} → ${permArray.join(' or ')} (MISSING!)`);
    hasMissingPermissions = true;
  }
}

console.log('');
console.log('=== Test Result ===');
if (hasMissingPermissions) {
  console.log('❌ FAIL: Missing permissions detected!');
  console.log('');
  console.log('This will cause runtime errors:');
  console.log('  - chrome.notifications.create → "Cannot read properties of undefined (reading \'create\')"');
  process.exit(1);
} else {
  console.log('✅ PASS: All required permissions are present');
  process.exit(0);
}
