import { ScrollViewStyleReset } from 'expo-router/html';

const APP_NAME = 'PROMETHEUS';
const THEME_COLOR = '#F5F8F7';
const SERVICE_WORKER_BOOTSTRAP = `
if ('serviceWorker' in navigator) {
  window.addEventListener('load', function () {
    navigator.serviceWorker
      .register('/sw.js', { scope: '/' })
      .then(function (registration) {
        registration.update().catch(function () {
          return undefined;
        });
      })
      .catch(function (error) {
        console.warn('Service worker registration failed:', error);
      });
  });
}
`;

export default function Root({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <head>
        <meta charSet="utf-8" />
        <meta httpEquiv="X-UA-Compatible" content="IE=edge" />
        <meta
          name="viewport"
          content="width=device-width, initial-scale=1, viewport-fit=cover, shrink-to-fit=no"
        />
        <meta name="application-name" content={APP_NAME} />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="default" />
        <meta name="apple-mobile-web-app-title" content={APP_NAME} />
        <meta name="mobile-web-app-capable" content="yes" />
        <meta name="theme-color" content={THEME_COLOR} />
        <link rel="manifest" href="/manifest.json" />
        <link rel="apple-touch-icon" href="/icons/apple-touch-icon.png" />
        <link rel="icon" type="image/webp" sizes="192x192" href="/icons/icon-192.webp" />
        <link rel="icon" type="image/webp" sizes="512x512" href="/icons/icon-512.webp" />
        <link rel="icon" type="image/png" sizes="192x192" href="/icons/icon-192.png" />
        <link rel="icon" type="image/png" sizes="512x512" href="/icons/icon-512.png" />

        <ScrollViewStyleReset />
        <style dangerouslySetInnerHTML={{ __html: responsiveBackground }} />
      </head>
      <body>
        {children}
        <script dangerouslySetInnerHTML={{ __html: SERVICE_WORKER_BOOTSTRAP }} />
      </body>
    </html>
  );
}

const responsiveBackground = `
body {
  background-color: #F5F8F7;
}
`;
