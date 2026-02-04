# EXPECTED_INPUT_COLUMNS: Status, Response, user_response, farmer_response, first_name, farmerCode, countryCode, mobileNumber, userIds, languagePreference, country, formattedAddress, administrativeAreaLevel1, administrativeAreaLevel2, sublocalityLevel1, postalCode, latitude, longitude, gender

# AI Updated Script - 2026-01-22 11:26:08 IST
import pandas as pd
import requests
import json
import time
from GetAuthtoken import get_access_token


# Function to process data and make API requests
def post_data_to_api(user_api_url, farmer_api_url, token, excel_sheet, sheet_name):
    print("📂 Loading input Excel file...")
    df = pd.read_excel(excel_sheet, sheet_name=sheet_name)

    def get_value(cell):
        """Returns None if the cell is empty or NaN, otherwise returns the string value."""
        return None if pd.isna(cell) or str(cell).strip() == "" else cell

    # Step 1 [LOGIC]: Loads Excel data, defines helper function, and ensures output columns exist in DataFrame.
    # Ensure the necessary columns exist
    columns_to_check = ["Status", "Response", "user_response", "farmer_response"]
    for col in columns_to_check:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].astype(str)

    for index, row in df.iterrows():
        print(f"🔄 Processing row {index + 1}...")

        # Step 2 [LOGIC]: Checks if 'first_name' (row.iloc[0]) is valid; skips row if invalid.
        # Extract firstName and validate
        first_name = get_value(row.iloc[0])
        if not first_name:
            print(f"⚠️ Row {index + 1} skipped due to invalid farmer name.")
            df.at[index, 'Response'] = "invalid farmer name and creation is skipped"
            df.at[index, 'Status'] = "⚠️ Skipped"
            continue

        # Set headers for API requests
        headers = {'Authorization': f'Bearer {token}'}

        # Step 3 [LOGIC]: Extracts and cleans 'userIds' (row.iloc[4]), splits into a list, and skips row if empty.
        # Extract user IDs and clean up data
        userIds = str(row.iloc[4]).strip()
        user_data_list = []

        if pd.notna(row.iloc[4]) and userIds:
            userIds = userIds.split(',')
        else:
            userIds = []

        # Skip row execution if user list is empty
        if not userIds:
            print(f"⚠️ Row {index + 1} skipped due to empty user list.")
            df.at[index, 'Response'] = "Skipped due to empty user list"
            df.at[index, 'Status'] = "⚠️ Skipped"
            continue

        user_api_failed = False
        farmer_api_failed = False
        response = None

        # Step 4 [API]: Fetch User Details
        # Fetch user details if IDs exist
        if userIds:
            print("🌍 Fetching user details...")
            for user in userIds:
                user = user.strip()
                if user:
                    try:
                        # Call GET /services/user/api/users/{userId}
                        response = requests.get(f"{user_api_url}/{user}", headers=headers)
                        if response.status_code == 200:
                            # user_data_list.append(response.json())
                            user_data_list.append(response.json())
                        else:
                            print(f"⚠️ Failed to fetch user {user}: {response.status_code} - {response.text}")
                            user_api_failed = True
                    except Exception as e:
                        print(f"❌ Error fetching user {user}: {str(e)}")
                        user_api_failed = True

        # Updates df.at[index, 'user_response'].
        df.at[index, 'user_response'] = json.dumps(user_data_list)
        time.sleep(0.2)

        # Step 5 [LOGIC]: Constructs the farmer API payload using data from Excel row and fetched user details.
        # Prepare payload for farmer API
        print("📦 Preparing farmer API payload...")
        farmer_payload = {
            "status": "DISABLE",
            "data": {
                "mobileNumber": get_value(row.iloc[3]),
                "countryCode": f"+{str(row.iloc[2]).strip()}",
                "languagePreference": get_value(row.iloc[5]),
                "farmeradditionl3": "A",
                "farmeradditionl4": "A",
                "farmeradditionl2": "A",
                # "registrationDate": get_value(row.iloc[16]),
                # "gdprConsent": get_value(row.iloc[17]),
                # "ageRange": get_value(row.iloc[15])
            },
            "images": {},
            "declaredArea": {
                "enableConversion": "true",
                "unit": "HECTARE"
            },
            "firstName": first_name,
            "farmerCode": get_value(row.iloc[1]),
            "assignedTo": user_data_list,
            "gender": get_value(row.iloc[14]),
            "address": {
                "country": get_value(row.iloc[6]),
                "formattedAddress": get_value(row.iloc[7]),
                "houseNo": None,
                "buildingName": None,
                "administrativeAreaLevel1": get_value(row.iloc[8]),
                "locality": None,
                "administrativeAreaLevel2": get_value(row.iloc[9]),
                "sublocalityLevel1": get_value(row.iloc[10]),
                "sublocalityLevel2": None,
                "landmark": None,
                "postalCode": get_value(row.iloc[11]),
                "placeId": "ChIJ6Yuupv8VphkRB5evs7ThIW0",
                "latitude": get_value(row.iloc[12]),
                "longitude": get_value(row.iloc[13])
            },
            # "isGDPRCompliant": "true"
        }

        # Converting farmer_payload to multipart dto
        multipart_data = {"dto": (None, json.dumps(farmer_payload), "application/json")}

        # Step 6 [API]: Create Farmer Record
        # Send POST request to farmer API
        print(f"🚀 Sending POST request to farmer API for {row.iloc[0]}...")
        try:
            # Call POST /services/farm/api/farmers
            response = requests.post(farmer_api_url, headers=headers, files=multipart_data)
            
            # Instructions: Updates df.at[index, 'farmer_response'] and df.at[index, 'Status'] based on API outcome.
            if response.status_code == 201:
                print(f"✅ Farmer created successfully: {row.iloc[0]}")
                df.at[index, 'Status'] = '✅ Success'
                df.at[index, 'farmer_response'] = response.text
            else:
                print(f"⚠️ Farmer creation failed: {response.status_code} - {response.text}")
                df.at[index, 'Status'] = f"❌ Failed: {response.status_code}"
                farmer_api_failed = True
                df.at[index, 'farmer_response'] = response.text # Store response on failure
        except Exception as e:
            print(f"❌ Error during farmer creation: {str(e)}")
            df.at[index, 'Status'] = "Error"
            farmer_api_failed = True
            # Note: response might be None here if request failed immediately

        # Store general response only if user API failed (farmer API response already captured above)
        if user_api_failed and not farmer_api_failed:
            df.at[index, 'Response'] = "User API failed"
        elif farmer_api_failed:
            df.at[index, 'Response'] = df.at[index, 'farmer_response']


        # Wait for 0.5 seconds for next iteration (Existing implementation uses 5 seconds)
        time.sleep(5)

    # Step 7 [LOGIC]: Saves the DataFrame back to the Excel file, including retry mechanism for file access issues.
    # Function to save Excel file safely
    def save_output_file(df, excel_sheet, attempt=1):
        try:
            df.to_excel(excel_sheet, index=False)
            print(f"💾 Output file saved successfully at attempt {attempt}")
        except Exception as err:
            if attempt < 3:  # Retry up to 3 times
                print(f"⚠️ Error saving output file: Please close any open instances of the file {err}. Retrying in 30 seconds...")
                time.sleep(30)
                save_output_file(df, excel_sheet, attempt + 1)
            else:
                print(f"❌ Failed to save output file after 3 attempts. Please close any open instances of the file.")

    # Save to Excel file
    print("💾 Saving Excel file...")
    save_output_file(df, excel_sheet)
    print("✅ Process completed! Output saved.")

# Inputs and configurations
farmer_api_url = "https://cloud.cropin.in/services/farm/api/farmers"
user_api_url = "https://cloud.cropin.in/services/user/api/users"
excel_sheet = "C:\\Users\\rajasekhar.palleti\\Downloads\\agraTenantsFarmerUploadTemplate.xlsx"
sheet_name = "Sheet1"
tenant_code = "asp"
environment = "prod1"

# Get authentication token
print("🌍 Fetching Auth_Token......")
token = get_access_token(tenant_code, "9649964096", "123456", environment)
if token:
    post_data_to_api(user_api_url, farmer_api_url, token, excel_sheet, sheet_name)
else:
    print("❌ Failed to retrieve access token. Process terminated.")