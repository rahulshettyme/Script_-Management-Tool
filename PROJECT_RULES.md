# Project Rules for Changes

For every change implemented in this codebase, the developer/agent MUST provide a response containing the following five items:

1. **New files created** — A list of any new files added to the codebase.
2. **Files modified** — A list of existing files that were updated.
3. **Why each file modification was needed** — A brief, technical rationale for each change.
4. **Risk to be taken care of during testing** — Potential pitfalls, edge cases, or issues to monitor during QA/verification.
5. **Probable impact areas** — Areas of the application that might be affected by the changes.

## Testing Rules
- **No Feature Automation Testing:** Do not perform browser-based or feature automation testing after code changes/fixes are made.
- **Backend Testing & Code Review:** Always perform code reviews and run backend tests automatically.
- **Manual User Testing:** Inform the user to perform manual testing for verification of feature changes.

## Script Failures and Modification Rules
- **Tool Updates Over Direct Script Fixes:** Any script failures or bugs in generated/converted scripts must be treated as a tool failure (e.g., in `script_generator.py`). Scripts must not be modified directly unless the user explicitly and specifically requests it.
- **Regeneration Workflow:** Always fix the underlying generator tool first, then let the user recreate/regenerate the failed script using the updated tool.

## Geocoding and API Key Rules
- **Geocoding Key Standardization:** The application must strictly use the official `Geocoding_api_key` key (loaded from `env_config.get('Geocoding_api_key')`) for all geocoding, address, and geolocation tasks.
- **GOOGLE_API_KEY Restriction:** The `GOOGLE_API_KEY` (loaded from the user's personal config/environment) is restricted ONLY for script creation/onboarding (calling Gemini API to generate scripts).
- **Backend Key Injection:** The Node.js backend must always inject `Geocoding_api_key` (obtained via `getGeocodingApiKey()`) into the `envConfig` payload before spawning or testing any Python scripts.
