// All real IANA zones from the platform. A free-text field let "UTC-3" through and
// crashed availability math, so the timezone is a closed list everywhere it's entered.
export const TIME_ZONES: string[] =
  typeof Intl.supportedValuesOf === "function" ? Intl.supportedValuesOf("timeZone") : ["UTC"];

// The zone's current UTC offset as "UTC-3" / "UTC+5:30" — shown so the IANA name isn't cryptic.
function utcOffset(timeZone: string): string {
  try {
    const parts = new Intl.DateTimeFormat("en-US", {
      timeZone,
      timeZoneName: "shortOffset",
    }).formatToParts(new Date());
    const name = parts.find((part) => part.type === "timeZoneName")?.value ?? "";
    return name.replace("GMT", "UTC") || "UTC";
  } catch {
    return "UTC";
  }
}

export interface TimeZoneOption {
  value: string;
  label: string;
}

// e.g. { value: "America/Montevideo", label: "America/Montevideo (UTC-3)" }
export const TIME_ZONE_OPTIONS: TimeZoneOption[] = TIME_ZONES.map((zone) => ({
  value: zone,
  label: `${zone} (${utcOffset(zone)})`,
}));
