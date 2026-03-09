module.exports = function (api) {
  const isProduction = api.env('production');
  api.cache(true);

  return {
    presets: ['babel-preset-expo'],
    plugins: [
      'expo-router/babel',
      isProduction && ['transform-remove-console', { exclude: ['warn', 'error'] }],
      'react-native-reanimated/plugin',
    ].filter(Boolean),
  };
};
