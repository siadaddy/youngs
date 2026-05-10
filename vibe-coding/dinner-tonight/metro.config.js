const { getDefaultConfig } = require('expo/metro-config');

const config = getDefaultConfig(__dirname);

// Zustand v5 uses import.meta.env which Metro web can't handle as ESM.
// Disabling package exports forces Metro to use the CJS build instead.
config.resolver.unstable_enablePackageExports = false;

module.exports = config;
