# Project Rules

## Testing and Verification
- **No Automation Testing after Fixing Code:** Do not perform any browser-based or feature-level automation testing (such as using the browser subagent) after code fixes are implemented.
- **Automatic Review & Backend Testing:** Always perform a code review and run existing backend test suites automatically to verify changes.
- **Manual Verification:** Inform the user to test the feature/code changes manually. No feature automation testing is required or should be run by the agent.

## Script Failures and Modification Rules
- **Tool Updates Over Direct Script Fixes:** Any script failures or bugs in generated/converted scripts must be treated as a tool failure (e.g., in `script_generator.py`). Scripts must not be modified directly unless the user explicitly and specifically requests it.
- **Regeneration Workflow:** Always fix the underlying generator tool first, then let the user recreate/regenerate the failed script using the updated tool.

## Geocoding and API Key Rules
- **Geocoding Key Standardization:** The application must strictly use the official `Geocoding_api_key` key (loaded from `env_config.get('Geocoding_api_key')`) for all geocoding, address, and geolocation tasks.
- **GOOGLE_API_KEY Restriction:** The `GOOGLE_API_KEY` (loaded from the user's personal config/environment) is restricted ONLY for script creation/onboarding (calling Gemini API to generate scripts).
- **Backend Key Injection:** The Node.js backend must always inject `Geocoding_api_key` (obtained via `getGeocodingApiKey()`) into the `envConfig` payload before spawning or testing any Python scripts.
