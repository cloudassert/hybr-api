import base64
import urllib.request
import urllib.error
import json
import urllib.parse

# --------------------------------
# 🔧 CONFIGURATION
# --------------------------------
import argparse
import getpass

# Parse command line arguments
parser = argparse.ArgumentParser()
parser.add_argument('--base-url', help='Base URL for the API')
parser.add_argument('--app-id', help='Application ID')
parser.add_argument('--username', help='Username')
parser.add_argument('--password', help='Password')
parser.add_argument('--tenant-subscription-id', help='Default tenant subscription ID')
parser.add_argument('--customer-id', help='Default customer ID')
args = parser.parse_args()

# Get values from command line or prompt user
BASE_URL = args.base_url if args.base_url else input("Enter base URL (e.g. https://portal.hybr.cloudassert.com): ").strip()
APP_ID = args.app_id if args.app_id else input("Enter application ID: ").strip()
USERNAME = args.username if args.username else input("Enter username: ").strip()
PASSWORD = args.password if args.password else getpass.getpass("Enter password: ").strip()

# Default values and memory
DEFAULT_TENANT_SUB_ID = getattr(args, 'tenant_subscription_id', None)
DEFAULT_CUSTOMER_ID = getattr(args, 'customer_id', None)
remembered_values = {}

# -------------------------
# Reference product types
# -------------------------
SOFTWARE_PRODUCT_TYPES = ["Software Subscription", "SUSE Linux", "Perpetual Software", "Red Hat Plans"]
NCE_PRODUCT_TYPES = ["License", "OnlineServicesNCE"]
AZURE_RESERVATION_PRODUCT_TYPES = ["Azure Reservation"]

NCE_CATEGORIES = [
    "Microsoft Entra","Dynamics 365","Enterprise","Exchange","Microsoft 365","Microsoft Defender",
    "Microsoft Intune","Microsoft Teams","Office 365","OneDrive","Power Apps","Power Automate",
    "Power BI","Project","Share Point","Visio","Windows","Others"
]

OFFER_CATEGORIES = ["Small business","Enterprise","Trial","Government","None"]

OFFER_TYPE = ["Baseoffer","Addon"]

OFFER_SEGMENTS = ["Commercial","GovernmentCommunityCloud","Education","Nonprofit"]

AZURE_RESERVATION_TYPES = [
    "App Services", "Specialized Compute Azure VMware Solution", "Azure Data Explorer", "Azure Files Reserved Capacity",
    "Backup", "Azure storage reserved capacity", "Azure Cosmos DB", "Databricks", "Data Factory", "Dedicated Host",
    "FabricCapacity", "Azure Managed Disks", "MDC", "Azure Database for MySql", "Nutanix", "OpenAIPTU",
    "Azure Database for PostgreSql", "Azure Redis Cache - Premium", "SapHana", "Sql Databases",
    "Azure Sql Data Warehouse", "Synapse", "Virtual Machines"
]


# ======== HELPER FUNCTIONS =========
def make_request(url, method="GET", params=None):
    auth_string = f"{USERNAME}:{PASSWORD}"
    auth_b64 = base64.b64encode(auth_string.encode()).decode()
    headers = {"Authorization": f"Basic {auth_b64}", "Content-Type": "application/json"}

    if params:
        url += "?" + urllib.parse.urlencode(params)

    req = urllib.request.Request(url, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as res:
            data = res.read().decode("utf-8")
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return data
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP Error {e.code}: {e.reason}")
        print(e.read().decode())
    except urllib.error.URLError as e:
        print(f"❌ URL Error: {e.reason}")
    return None

def build_url(path, inputs=None):
    if inputs is None:
        inputs = {}
    all_inputs = {"appId": APP_ID, **inputs}
    path = path.replace("{{", "{").replace("}}", "}")
    return f"{BASE_URL}{path.format(**all_inputs)}"

def prompt_optional_params(param_names, reference_dict=None, product_type=None):
    params = {}
    for name in param_names:
        if reference_dict and name in reference_dict:
            if name == "offerType" and product_type not in ["OnlineServicesNCE"]:
                continue
            elif name == "reservationProductTypes" and product_type not in ["Azure Reservation"]:
                continue
            print(f"\nReference values for {name}:")
            for val in reference_dict[name]:
                print(f" - {val}")
        val = input(f"Enter optional '{name}' (or press Enter to skip): ").strip()
        if val:
            params[name] = val
    return params

def execute_api(api):
    print(f"\n➡️  {api['name']}")
    while True:
        # Prompt required inputs
        for inp_name, inp_key in api.get("required_inputs", []):
            if inp_key not in api["inputs"]:
                # Check for default or remembered values
                default_val = None
                if inp_key == "tenant_subscription_id":
                    default_val = remembered_values.get("tenant_subscription_id") or DEFAULT_TENANT_SUB_ID
                elif inp_key == "customer_id":
                    default_val = remembered_values.get("customer_id") or DEFAULT_CUSTOMER_ID
                
                prompt = f"Enter {inp_name}"
                if default_val:
                    prompt += f" (default: {default_val})"
                prompt += " (or 'skip'): "
                
                inp_val = input(prompt).strip()
                if inp_val.lower() == "skip":
                    print("⏭️ Skipped this API.")
                    return
                
                # Use default if no input provided
                if not inp_val and default_val:
                    inp_val = default_val
                
                if not inp_val:
                    print(f"❌ {inp_name} is required.")
                    continue
                
                # Remember the value for future use
                if inp_key in ["tenant_subscription_id", "customer_id"]:
                    remembered_values[inp_key] = inp_val
                
                api["inputs"][inp_key] = urllib.parse.quote_plus(inp_val)

        # Handle dynamic sub_path
        if api["name"] == "getCspCustomerSubscriptionsByType":
            print("\nSelect subscription type:")
            print("1️⃣ Azure Subscriptions")
            print("2️⃣ Azure Reservations")
            print("3️⃣ CSP Subscriptions like NCE, Software and Other SaaS products..")
##            print("4️⃣ Software Subscriptions")
##            print("5️⃣ SaaS Marketplace Offers")
            choice = input("Enter your choice (1/2/3/4/5): ").strip()
            if choice == "1":
                api["inputs"]["sub_path"] = "/api/integrations/{{appId}}/admin/service/billing/csp/companies/getCspCustomerAzureSubscriptions/{{tenant_subscription_id}}/{{customer_id}}"
            elif choice == "2":
                api["inputs"]["sub_path"] = "/api/integrations/{{appId}}/admin/service/billing/csp/companies/getAzureReservations/{{tenant_subscription_id}}/{{customer_id}}"
            elif choice == "3":
                api["inputs"]["sub_path"] = "/api/integrations/{{appId}}/admin/service/billing/csp/companies/getCspCustomerSubscriptions/{{tenant_subscription_id}}/{{customer_id}}"
##            elif choice == "4":
##                api["inputs"]["sub_path"] = "/api/integrations/{{appId}}/admin/service/billing/csp/companies/getCspCustomerSoftwareSubscriptions/{{tenant_subscription_id}}/{{customer_id}}"
##            elif choice == "5":
##                api["inputs"]["sub_path"] = "/api/integrations/{{appId}}/admin/service/billing/csp/companies/getCspCustomerSubscriptionsForMarketplace/{{tenant_subscription_id}}/{{customer_id}}"
            else:
                print("❌ Invalid choice. Skipping API.")
                return

        # Prompt optional params
        params = prompt_optional_params(api.get("optional_params", []),
                                        reference_dict=api.get("reference_values"),
                                        product_type=api["inputs"].get("productTypes"))

        # Build correct URL (handle dynamic sub_path)
        final_path = api["inputs"].get("sub_path", api["path"])
        try:
            url = build_url(final_path, api["inputs"])
        except KeyError as e:
            print(f"❌ Missing required input for URL: {e}")
            return

        # Execute
        res = make_request(url, params=params)
        print(f"\n📘 {api['name']} Result:\n", json.dumps(res, indent=2))

        retry = input("\nRun this API again with different inputs? (y/n): ").strip().lower()
        if retry != "y":
            break

        api["inputs"] = {}

# ========== API FLOW ==========
apis = [

    # {"name": "Get ALL CSP Companies",
    #  "path": "/api/integrations/{{appId}}/admin/service/billing/csp/companies",
    #  "required_inputs": [], "optional_params": ["connectionId"], "inputs": {}},

    {"name": "Get CSP Mapped Companies HYBR Tenant Subscriptions",
     "path": "/api/integrations/{{appId}}/admin/service/billing/csp/companies/getCspMappedCompanies",
     "required_inputs": [], "optional_params": ["connectionId"], "inputs": {}},

    # {"name": "AdminHybrCompanySubscriptions",
    #  "path": "/api/integrations/{{appId}}/admin/service/core/companies/{{companyId}}/subscriptions",
    #  "required_inputs": [("Company ID", "companyId")],
    #  "optional_params": ["connectionId"], "inputs": {}},

    {"name": "Get CSP Customer Profile By HYBR Subscription ID",
     "path": "/api/integrations/{{appId}}/admin/service/billing/csp/companies/getCspCustomerProfileBySubscriptionId/{{tenant_subscription_id}}",
     "required_inputs": [("Tenant Subscription ID", "tenant_subscription_id")],
     "optional_params": ["connectionId"], "inputs": {}},

    {"name": "getCspCustomerSubscriptionsByType",
     "path": "{sub_path}",
     "required_inputs": [("Tenant Subscription ID", "tenant_subscription_id"), ("Customer ID", "customer_id")],
     "optional_params": ["subscriptionType", "status"],
     "reference_values": {
         "subscriptionType": ["ServiceProvider", "Reseller", "Customer"],
         "status": ["1 - Active", "2 - Suspended", "3 - Deleted", "6 - Disabled"]
     }, "inputs": {}},

    {"name": "Get CSP Customer Licenses By CSP Customer ID",
     "path": "/api/integrations/{{appId}}/admin/service/billing/csp/licenses/getCustomerLicenses/{{customer_id}}",
     "required_inputs": [("Customer ID", "customer_id")],
     "optional_params": ["page", "page_Size"],
     "inputs": {}},

    {"name": "Get CSP Product Types By HYBR Tenant Subscription ID",
     "path": "/api/integrations/{{appId}}/admin/service/billing/csp/companies/cspProductTypes/{{tenant_subscription_id}}",
     "required_inputs": [("Tenant Subscription ID", "tenant_subscription_id")],
     "optional_params": ["connectionId"], "inputs": {}},

    {"name": "Get CSP Categories By HYBR Tenant Subscription ID",
     "path": "/api/integrations/{{appId}}/admin/service/billing/csp/companies/getCspCategories/{{tenant_subscription_id}}",
     "required_inputs": [("Tenant Subscription ID", "tenant_subscription_id")],
     "optional_params": ["connectionId"], "inputs": {}},

    {"name": "Get CSP Offers By HYBR Tenant Subscription ID",
     "path": "/api/integrations/{{appId}}/admin/service/billing/csp/companies/getCspOffersBySubscriptionIdFromDb/{{tenant_subscription_id}}/{{customer_id}}",
     "required_inputs": [("Tenant Subscription ID", "tenant_subscription_id"), ("Customer ID", "customer_id")],
     "optional_params": ["connectionId", "productTypes", "reservationProductTypes", "cspOfferCategories", "offerType", "segments", "search", "skip", "take"],
     "reference_values": {
         "productTypes": SOFTWARE_PRODUCT_TYPES + NCE_PRODUCT_TYPES + AZURE_RESERVATION_PRODUCT_TYPES,
         "reservationProductTypes": AZURE_RESERVATION_TYPES,
         "cspOfferCategories": OFFER_CATEGORIES,
         "offerType": OFFER_TYPE,
         "segments": OFFER_SEGMENTS
     }, "inputs": {}}
]

# ========== MAIN MENU ==========
print("\n🔹 CSP API Interactive Flow\n")
mode = input("Choose mode: 1️⃣ Sequential flow, 2️⃣ Jump to any API: ").strip()
if mode == "1":
    for api in apis:
        execute_api(api)
elif mode == "2":
    while True:
        print("\nAvailable APIs:")
        for idx, api in enumerate(apis, start=1):
            print(f"{idx}. {api['name']}")
        choice = input("Enter API number to run (or 'exit' to quit): ").strip()
        if choice.lower() == "exit":
            break
        if choice.isdigit() and 1 <= int(choice) <= len(apis):
            execute_api(apis[int(choice) - 1])
        else:
            print("Invalid choice.")
else:
    print("Invalid mode selected.")

print("\n✅ Flow completed. Thank you!")
