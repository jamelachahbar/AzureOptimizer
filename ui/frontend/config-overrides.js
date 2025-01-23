const path = require('path');

module.exports = function override(config) {
  config.resolve.alias = {
    ...(config.resolve.alias || {}),
    '#minpath': path.resolve(__dirname, 'node_modules/minpath'),
  };
  return config;
};
