const staticConfig = require("./app.json");

const expo = staticConfig.expo || {};
const extra = expo.extra || {};

module.exports = () => ({
  ...staticConfig,
  expo: {
    ...expo,
    extra: {
      ...extra,
      apiUrl: process.env.EXPO_PUBLIC_API_URL || extra.apiUrl,
      appId: process.env.EXPO_PUBLIC_APP_ID || extra.appId || "prometheus-app",
    },
  },
});
