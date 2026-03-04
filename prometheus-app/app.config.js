const staticConfig = require("./app.json");

const expo = staticConfig.expo || {};
const extra = expo.extra || {};

function parseBoolean(value) {
  if (typeof value === "boolean") return value;
  if (typeof value !== "string") return null;

  const normalized = value.trim().toLowerCase();
  if (["1", "true", "yes", "on"].includes(normalized)) return true;
  if (["0", "false", "no", "off"].includes(normalized)) return false;
  return null;
}

module.exports = () => ({
  ...staticConfig,
  expo: {
    ...expo,
    extra: {
      ...extra,
      apiUrl: process.env.EXPO_PUBLIC_API_URL || extra.apiUrl,
      appId: process.env.EXPO_PUBLIC_APP_ID || extra.appId || "prometheus-app",
      enableLegacyAppToken:
        parseBoolean(process.env.EXPO_PUBLIC_ENABLE_LEGACY_APP_TOKEN) ??
        parseBoolean(extra.enableLegacyAppToken) ??
        false,
      legacyAppToken: process.env.EXPO_PUBLIC_APP_TOKEN || extra.legacyAppToken || "",
    },
  },
});
