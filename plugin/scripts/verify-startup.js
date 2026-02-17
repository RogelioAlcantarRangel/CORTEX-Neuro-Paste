#!/usr/bin/env node

function verifyDependency(name) {
  try {
    const resolvedPath = require.resolve(name);
    console.log(`[OK] ${name} resolved at: ${resolvedPath}`);
    return true;
  } catch (err) {
    console.error(`[ERROR] Unable to resolve dependency '${name}': ${err.message}`);
    return false;
  }
}

const checks = ['ws', 'robotjs'].map(verifyDependency);

if (checks.every(Boolean)) {
  console.log('Plugin startup dependency verification passed.');
  process.exit(0);
}

console.error('Plugin startup dependency verification failed.');
process.exit(1);
