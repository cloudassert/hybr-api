import base64
import urllib.request
import urllib.error
import json
import urllib.parse
import argparse
import getpass

# --------------------------------
# 🔧 CONFIGURATION
# --------------------------------
parser = argparse.ArgumentParser()
parser.add_argument('--base-url', help='Base URL for the API')
parser.add_argument('--app-id', help='Application ID')
parser.add_argument('--username', help='Username')
parser.add_argument('--password', help='Password')
parser.add_argument('--tenant-subscription-id', help='Default tenant subscription ID')
parser.add_argument('--customer-id', help='Default customer ID')
args = parser.parse_args()

BASE_URL = args.base_url if args.base_url else input("Enter base URL (e.g. https://portal.hybr.cloudassert.com): ").strip()
APP_ID = args.app_id if args.app_id else input("Enter application ID: ").strip()
USERNAME = args.username if args.username else input("Enter username: ").strip()
PASSWORD = args.password if args.password else getpass.getpass("Enter password: ").strip()

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
    "App Services","Specialized Compute Azure VMware Solution","Azure Data Explorer","Azure Files Reserved Capacity",
    "Backup","Azure storage reserved capacity","Azure Cosmos DB","Databricks","Data Factory","Dedicated Host",
    "FabricCapacity","Azure Managed Disks","MDC","Azure Database for MySql","Nutanix","OpenAIPTU",
    "Azure Database for PostgreSql","Azure Redis Cache - Premium","SapHana","Sql Databases",
    "Azure Sql Data Warehouse","Synapse","Virtual Machines"
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

def print_context():
    print("\n📌 Current Context:")
    for k, v in remembered_values.items():
        print(f"   {k}: {v}")
    print()


# ✅ INITIALIZATION CONTEXT USING TWO APIs
def initialize_subscription_context():
    print("\n🔹 Initializing subscription context...")

    # Step 1: Call "List Subscriptions"
##    list_url = build_url("/api/integrations/{{appId}}/admin/service/core/subscriptions")
##    subscriptions = make_request(list_url)
##
##    if not subscriptions or not isinstance(subscriptions, list):
##        print("❌ No subscriptions found or API error.")
##        return
##
##    print("\nAvailable Subscriptions:")
##    for idx, sub in enumerate(subscriptions, start=1):
##        print(f"{idx}. {sub.get('name', 'Unnamed')} | ID: {sub.get('SubscriptionId')}")
##
##    # Choose subscription
##    choice = input("\nEnter the number of subscription to select: ").strip()
##    if not choice.isdigit() or not (1 <= int(choice) <= len(subscriptions)):
##        print("❌ Invalid choice.")
##        return
##
##    selected = subscriptions[int(choice) - 1]
##    subscription_id = selected.get("SubscriptionId")
##    remembered_values["tenant_subscription_id"] = subscription_id
##    print(f"\n✅ Selected Subscription ID: {subscription_id}")

    # Step 2: Call "Get Subscription Relationships"
    rel_url = build_url(
        "/api/integrations/{{appId}}/admin/service/core/subscriptions/subscriptionRelationships"
    )
    
    print("\nAvailable Subscriptions:")
    relationships = make_request(rel_url)
    print(relationships)
    
    if not relationships or not isinstance(relationships, list):
        print("❌ No subscriptions found or API error.")
        return

    parent_subscription_id = None
    if isinstance(relationships, list) and len(relationships) > 0:
        subscription_id = relationships[0].get("SubscriptionId")
        parent_subscription_id = relationships[0].get("ParentSubscriptionId")
    elif isinstance(relationships, dict):
        subscription_id = relationships.get("SubscriptionId")
        parent_subscription_id = relationships.get("ParentSubscriptionId")

    remembered_values["customerSubscriptionId"] = subscription_id or "null"
    remembered_values["parentSubscriptionId"] = parent_subscription_id or "null"

    print("\nDefault Subscriptions:\n")
    print(f"\n✅ Selected Subscription ID: {subscription_id}")
    print(f"\n✅ Parent Subscription ID: {parent_subscription_id or 'null'}")

    print("\n✅ Subscription Context Initialized Successfully.\n")


# ========== EXECUTE API ==========
def execute_api(api):
    print(f"\n➡️  Executing API: {api['name']}")
    print_context()

    # Fill required inputs
    for inp_name, inp_key in api.get("required_inputs", []):
        if inp_key not in api["inputs"] or inp_key in api["inputs"]:
            remembered_val = remembered_values.get(inp_key)
            prompt = f"Enter {inp_name}"
            if remembered_val:
                prompt += f" (default: {remembered_val})"
            prompt += " (or 'skip'): "
            val = input(prompt).strip()

            if val.lower() == "skip":
                print("⏭️ Skipped this API.")
                return
            if not val and remembered_val:
                val = remembered_val

            if not val:
                print(f"❌ {inp_name} is required.")
                return

            api["inputs"][inp_key] = val
            remembered_values[inp_key] = val

    # Prompt for optional params
    params = prompt_optional_params(api.get("optional_params", []))

    # Build URL and add query params
    url = build_url(api["path"], api["inputs"])
    for k, v in api["inputs"].items():
        if f"{{{k}}}" not in api["path"] and k not in params:
            params[k] = v

    result = make_request(url, params=params)
    print(f"\n📘 Result:\n", json.dumps(result, indent=2))

##def execute_api(api):
##    print(f"\n➡️  {api['name']}")
##    while True:
##        # Collect required inputs
##        for inp_name, inp_key in api.get("required_inputs", []):
##            if inp_key not in api["inputs"]:
##                default_val = None
##                if inp_key == "tenant_subscription_id":
##                    default_val = remembered_values.get("tenant_subscription_id") or DEFAULT_TENANT_SUB_ID
##                elif inp_key == "customer_id":
##                    default_val = remembered_values.get("customer_id") or DEFAULT_CUSTOMER_ID
##
##                prompt = f"Enter {inp_name}"
##                if default_val:
##                    prompt += f" (default: {default_val})"
##                prompt += " (or 'skip'): "
##                inp_val = input(prompt).strip()
##
##                if inp_val.lower() == "skip":
##                    print("⏭️ Skipped this API.")
##                    return
##
##                if not inp_val and default_val:
##                    inp_val = default_val
##                if not inp_val:
##                    print(f"❌ {inp_name} is required.")
##                    continue
##
##                # Remember tenant or customer IDs
##                if inp_key in ["tenant_subscription_id", "customer_id"]:
##                    remembered_values[inp_key] = inp_val
##
##                api["inputs"][inp_key] = urllib.parse.quote_plus(inp_val)
##
##        # Special case handling for subscription-type API
##        if api["name"] == "getCspCustomerSubscriptionsByType":
##            print("\nSelect subscription type:")
##            print("1️⃣ Azure Subscriptions")
##            print("2️⃣ Azure Reservations")
##            print("3️⃣ CSP Subscriptions like NCE, Software and Other SaaS products..")
##            choice = input("Enter your choice (1/2/3): ").strip()
##            if choice == "1":
##                api["inputs"]["sub_path"] = "/api/integrations/{{appId}}/admin/service/billing/csp/companies/getCspCustomerAzureSubscriptions/{{tenant_subscription_id}}/{{customer_id}}"
##            elif choice == "2":
##                api["inputs"]["sub_path"] = "/api/integrations/{{appId}}/admin/service/billing/csp/companies/getAzureReservations/{{tenant_subscription_id}}/{{customer_id}}"
##            elif choice == "3":
##                api["inputs"]["sub_path"] = "/api/integrations/{{appId}}/admin/service/billing/csp/companies/getCspCustomerSubscriptions/{{tenant_subscription_id}}/{{customer_id}}"
##            else:
##                print("❌ Invalid choice. Skipping API.")
##                return
##
##        # Collect optional params
##        params = prompt_optional_params(
##            api.get("optional_params", []),
##            reference_dict=api.get("reference_values"),
##            product_type=api["inputs"].get("productTypes")
##        )
##
##        # Determine final path
##        final_path = api["inputs"].get("sub_path", api["path"])
##
##        try:
##            url = build_url(final_path, api["inputs"])
##        except KeyError as e:
##            print(f"❌ Missing required input for URL: {e}")
##            return
##
##        # ✅ Add required inputs that are NOT part of the path as query params
##        for key, val in api["inputs"].items():
##            if val and f"{{{{{key}}}}}" not in final_path and key not in params:
##                params[key] = val
##
##        # Make request
##        res = make_request(url, params=params)
##
##        print(f"\n📘 {api['name']} Result:\n", json.dumps(res, indent=2))
##
##        retry = input("\nRun this API again with different inputs? (y/n): ").strip().lower()
##        if retry != "y":
##            break
##        api["inputs"] = {}
# ========== API GROUPS ==========

MS_CSP_APIS = [
    {"name": "Get CSP Mapped Companies HYBR Tenant Subscriptions",
     "path": "/api/integrations/{{appId}}/admin/service/billing/csp/companies/getCspMappedCompanies",
     "required_inputs": [], "optional_params": ["connectionId"], "inputs": {}},

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
     "optional_params": ["page", "page_Size"], "inputs": {}},

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

REPORT_APIS = [
    #{"name": "List Subscriptions", "path": "/api/integrations/{{appId}}/admin/service/core/subscriptions", "inputs": {}},
    {"name": "Get Subscriptions and their Relationships",
     "path": "/api/integrations/{{appId}}/admin/service/core/subscriptions/subscriptionRelationships",
     "inputs": {}},
    {"name": "List Available Currency Codes", "path": "/api/integrations/{{appId}}/admin/service/billing/csp/reports/availableCurrencySymbols",
     "required_inputs": [("Month", "month"), ("Year", "year")],
     "optional_params": ["parentSubscriptionId"], "inputs": {}},

    {"name": "Top Products By Revenue",
     "path": "/api/integrations/{{appId}}/admin/service/billing/csp/reports/topProductsByRevenue",
     "required_inputs": [("Month", "month"), ("Year", "year"), ("Number Of Items", "numberOfItems"), ("Currency", "currency")],
     "optional_params": ["parentSubscriptionId"], "inputs": {}},

    {"name": "Top Customers By Revenue",
     "path": "/api/integrations/{{appId}}/admin/service/billing/csp/reports/topCustomersByRevenue",
     "required_inputs": [("Month", "month"), ("Year", "year"), ("Number Of Items", "numberOfItems"), ("Currency", "currency")],
     "optional_params": ["parentSubscriptionId"], "inputs": {}},
    {"name": "Monthly Reseller Margin",
     "path": "/api/integrations/{{appId}}/admin/service/billing/csp/reports/monthlyResellerMargin",
     "required_inputs": [("Month", "month"), ("Year", "year"), ("Currency", "currency")],
     "optional_params": ["parentSubscriptionId"], "inputs": {}},

    {"name": "Monthly Reseller Margin Per Resource",
     "path": "/api/integrations/{{appId}}/admin/service/billing/csp/reports/monthlyResellerMarginPerResource",
     "required_inputs": [("Month", "month"), ("Year", "year"), ("Currency", "currency")],
     "optional_params": ["parentSubscriptionId"], "inputs": {}},

    {"name": "Monthly Reseller Margin Per Subscription",
     "path": "/api/integrations/{{appId}}/admin/service/billing/csp/reports/monthlyResellerMarginPerSubscription",
     "required_inputs": [("Month", "month"), ("Year", "year"), ("Currency", "currency")],
     "optional_params": ["parentSubscriptionId"], "inputs": {}},

    {"name": "Monthly Products Reseller Margin By Subscription",
     "path": "/api/integrations/{{appId}}/admin/service/billing/csp/reports/monthlyProductsResellerMarginBySubscription",
     "required_inputs": [("Tenant Subscription ID", "customerSubscriptionId"), ("Month", "month"), ("Year", "year")],
     "inputs": {}},

     #{"name": "Monthly Subscription Reseller Margin By Product",
     #"path": "/api/integrations/{{appId}}/admin/service/billing/csp/reports/monthlySubscriptionResellerMarginByProduct",
     #"required_inputs": [("Month", "month"), ("Year", "year"), ("Metered Resource Name", "meteredResourceName"), ("Currency", "currency")],
     #"optional_params": ["parentSubscriptionId"], "inputs": {}},
    
    {"name": "Current Month Estimate",
     "path": "/api/integrations/{{appId}}/admin/service/billing/csp/reports/estimatedCostByServiceTypePerCustomer",
     "required_inputs": [("Tenant Subscription ID", "customerSubscriptionId"), ("Month", "month"), ("Year", "year")],
     "inputs": {}}
]

# ========== MAIN MENU ==========
print("\n🔹 CSP API Interactive CLI\n")
print("Select API Group:")
print("1️⃣ Microsoft CSP APIs")
print("2️⃣ Reports APIs")
group_choice = input("Enter choice (1/2): ").strip()

if group_choice == "1":
    selected_apis = MS_CSP_APIS
    print("\n🟦 Selected Group: Microsoft CSP APIs")
elif group_choice == "2":
    selected_apis = REPORT_APIS
    print("\n🟨 Selected Group: Reports APIs")
    # Step 1: Initialize subscription context (only once)
    initialize_subscription_context()
else:
    print("❌ Invalid choice.")
    exit()

mode = input("\nChoose mode: 1️⃣ Sequential flow, 2️⃣ Jump to any API: ").strip()
if mode == "1":
    for api in selected_apis:
        execute_api(api)
elif mode == "2":
    while True:
        print("\nAvailable APIs:")
        for idx, api in enumerate(selected_apis, start=1):
            print(f"{idx}. {api['name']}")
        choice = input("Enter API number to run (or 'exit' to quit): ").strip()
        if choice.lower() == "exit":
            break
        if choice.isdigit() and 1 <= int(choice) <= len(selected_apis):
##            if remembered_values:
##                if remembered_values.get("tenant_subscription_id"):
##                    api["inputs"]["tenant_subscription_id"] = remembered_values["tenant_subscription_id"]
##                if remembered_values.get("parentSubscriptionId"):
##                    api["inputs"]["parentSubscriptionId"] = remembered_values["parentSubscriptionId"]

            execute_api(selected_apis[int(choice) - 1])
        else:
            print("Invalid choice.")
else:
    print("Invalid mode selected.")

print("\n✅ Flow completed. Thank you!")
