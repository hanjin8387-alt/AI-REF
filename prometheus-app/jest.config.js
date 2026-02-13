module.exports = {
  preset: "jest-expo",
  setupFilesAfterEnv: ["<rootDir>/__tests__/setup.ts"],
  testMatch: ["**/__tests__/**/*.(test|spec).(ts|tsx|js)"],
};
