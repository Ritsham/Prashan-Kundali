import { useEffect } from 'react';

const HomePage = () => {
  useEffect(() => {
    const legacyUrl = window.location.port === '5173'
      ? 'http://127.0.0.1:8000/index.html'
      : '/index.html';

    window.location.replace(legacyUrl);
  }, []);

  return null;
};

export default HomePage;
