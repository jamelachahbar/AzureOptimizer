// API Configuration
// In production, uses the same origin (backend is on same domain via Container Apps)
// In development, uses localhost:5000

const isDevelopment = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';

// For Container Apps deployment, the backend URL follows a predictable pattern
// Frontend: ca-frontend-xxx.domain.azurecontainerapps.io
// Backend: ca-backend-xxx.domain.azurecontainerapps.io
const getBackendUrl = (): string => {
  if (isDevelopment) {
    return 'http://localhost:5000';
  }
  
  // Replace 'frontend' with 'backend' in the current hostname
  const currentHost = window.location.hostname;
  const backendHost = currentHost.replace('ca-frontend-', 'ca-backend-');
  return `https://${backendHost}`;
};

export const API_BASE_URL = getBackendUrl();

export default API_BASE_URL;
