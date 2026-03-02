import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('rep');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

export async function parseOrderImage(imageFile) {
  const formData = new FormData();
  formData.append('image', imageFile);
  const token = localStorage.getItem('token');
  const response = await fetch('/api/ocr/parse-order', {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`OCR request failed: ${response.status} ${text}`);
  }
  return response.json();
}

export default api;
