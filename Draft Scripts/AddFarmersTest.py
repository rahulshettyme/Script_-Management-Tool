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

    # Ensure the necessary columns exist
    columns_to_check = ["Status", "Response", "user_response", "farmer_response"]
    for col in columns_to_check:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].astype(str)

    for index, row in df.iterrows():
        print(f"🔄 Processing row {index + 1}...")

        # Extract firstName and validate
        first_name = get_value(row.iloc[0])
        if not first_name:
            print(f"⚠️ Row {index + 1} skipped due to invalid farmer name.")
            df.at[index, 'Response'] = "invalid farmer name and creation is skipped"
            df.at[index, 'Status'] = "⚠️ Skipped"
            continue

        # Set headers for API requests
        headers = {'Authorization': f'Bearer {token}'}

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

        # Fetch user details if IDs exist
        if userIds:
            print("🌍 Fetching user details...")
            for user in userIds:
                user = user.strip()
                if user:
                    try:
                        response = requests.get(f"{user_api_url}/{user}", headers=headers)
                        if response.status_code == 200:
                            user_data_list.append(response.json())
                        else:
                            print(f"⚠️ Failed to fetch user {user}: {response.status_code} - {response.text}")
                            user_api_failed = True
                    except Exception as e:
                        print(f"❌ Error fetching user {user}: {str(e)}")
                        user_api_failed = True

        df.at[index, 'user_response'] = json.dumps(user_data_list)
        time.sleep(0.2)

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

        # Send POST request to farmer API
        print(f"🚀 Sending POST request to farmer API for {row.iloc[0]}...")
        try:
            response = requests.post(farmer_api_url, headers=headers, files=multipart_data)
            if response.status_code == 201:
                print(f"✅ Farmer created successfully: {row.iloc[0]}")
                df.at[index, 'Status'] = '✅ Success'
                df.at[index, 'farmer_response'] = response.text
            else:
                print(f"⚠️ Farmer creation failed: {response.status_code} - {response.text}")
                df.at[index, 'Status'] = f"❌ Failed: {response.status_code}"
                farmer_api_failed = True
        except Exception as e:
            print(f"❌ Error during farmer creation: {str(e)}")
            df.at[index, 'Status'] = "Error"
            farmer_api_failed = True

        # Store response only if an API call failed
        if user_api_failed or farmer_api_failed:
            df.at[index, 'Response'] = response.text if farmer_api_failed else "User API failed"

        # Wait for 0.5 seconds for next iteration
        time.sleep(5)

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