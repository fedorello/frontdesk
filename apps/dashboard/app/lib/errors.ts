import { ApiError } from "./api";
import type { MessageKey } from "./i18n";

// Map any thrown error to a localized message key — auth failures get friendly,
// localized copy; we never surface raw backend strings or JSON to the user.
export function errorMessageKey(error: unknown): MessageKey {
  if (error instanceof ApiError) {
    if (error.status === 401) return "auth.invalidCredentials";
    if (error.status === 409) return "auth.emailTaken";
    if (error.status === 422) return "auth.invalidInput";
  }
  return "common.error";
}
