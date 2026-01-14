#!/bin/sh
# Environment configuration script for frontend
# Injects runtime environment variables into the built app

# Create env-config.js with runtime environment variables
cat <<EOF > /usr/share/nginx/html/env-config.js
window._env_ = {
  VITE_API_URL: "${VITE_API_URL:-http://localhost:5000}",
  VITE_APP_TITLE: "${VITE_APP_TITLE:-Azure Cost Optimizer}",
  VITE_ENABLE_ANALYTICS: "${VITE_ENABLE_ANALYTICS:-false}"
};
EOF

echo "Environment configuration complete:"
cat /usr/share/nginx/html/env-config.js
