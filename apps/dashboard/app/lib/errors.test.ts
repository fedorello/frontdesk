import { describe, expect, it } from "vitest";

import { ApiError } from "./api";
import { errorMessageKey } from "./errors";

describe("errorMessageKey", () => {
  it("maps auth statuses to localized keys", () => {
    expect(errorMessageKey(new ApiError(401, "x"))).toBe("auth.invalidCredentials");
    expect(errorMessageKey(new ApiError(409, "x"))).toBe("auth.emailTaken");
    expect(errorMessageKey(new ApiError(422, "x"))).toBe("auth.invalidInput");
  });

  it("falls back to a generic key for other errors", () => {
    expect(errorMessageKey(new ApiError(500, "x"))).toBe("common.error");
    expect(errorMessageKey(new Error("network"))).toBe("common.error");
  });
});
