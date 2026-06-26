// All real IANA zones from the platform. A free-text field let "UTC-3" through and
// crashed availability math, so the timezone is a closed list everywhere it's entered.
export const TIME_ZONES: string[] =
  typeof Intl.supportedValuesOf === "function" ? Intl.supportedValuesOf("timeZone") : ["UTC"];
