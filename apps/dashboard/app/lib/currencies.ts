// All ISO 4217 currency codes from the platform — the API validates against the same set.
export const CURRENCIES: string[] =
  typeof Intl.supportedValuesOf === "function"
    ? Intl.supportedValuesOf("currency")
    : ["USD", "EUR", "UYU"];
