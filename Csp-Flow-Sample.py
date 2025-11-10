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

def collect_csp_data():
    print("\n🔹 Collecting CSP Data for All Mapped Companies...")

    # Step 1: Get all CSP mapped companies
    mapped_companies_url = build_url("/api/integrations/{{appId}}/admin/service/billing/csp/companies/getCspMappedCompanies")
    mapped_companies = make_request(mapped_companies_url)

    if not mapped_companies or not isinstance(mapped_companies, list):
        print("❌ No mapped companies found or API error.")
        return

    all_data = []

    for company in mapped_companies:
        company_data = {"company": company, "customer_profile": None, "licenses": None, "offers": []}
        tenant_subscription_id = company.get("id")

        if not tenant_subscription_id:
            print(f"❌ Skipping company {company.get('Name', 'Unnamed')} due to missing TenantSubscriptionId.")
            continue

        # Step 2: Get customer profile by subscription ID
        customer_profile_url = build_url(
            "/api/integrations/{{appId}}/admin/service/billing/csp/companies/getCspCustomerProfileBySubscriptionId/{{tenant_subscription_id}}",
            {"tenant_subscription_id": tenant_subscription_id}
        )
        customer_profile = make_request(customer_profile_url)
        company_data["customer_profile"] = customer_profile

        customer_id = customer_profile[0].get("Id") if customer_profile else None
        if not customer_id:
            print(f"❌ Skipping company {company.get('Name', 'Unnamed')} due to missing CustomerId.")
            continue

        # Step 3: Get customer licenses by CSP customer ID
        licenses_url = build_url(
            "/api/integrations/{{appId}}/admin/service/billing/csp/licenses/getCustomerLicenses/{{customer_id}}",
            {"customer_id": customer_id}
        )
        licenses = make_request(licenses_url)
        company_data["licenses"] = licenses

        # Step 4: Get product types and categories
        # product_types_url = build_url(
        #     "/api/integrations/{{appId}}/admin/service/billing/csp/companies/cspProductTypes/{{tenant_subscription_id}}",
        #     {"tenant_subscription_id": tenant_subscription_id}
        # )
        # product_types = make_request(product_types_url)

        # push OnlineServicesNCE to product_types
        # if product_types and isinstance(product_types, list):
        #     if "OnlineServicesNCE" not in product_types:
        #         product_types.append("OnlineServicesNCE")

        # categories_url = build_url(
        #     "/api/integrations/{{appId}}/admin/service/billing/csp/companies/getCspCategories/{{tenant_subscription_id}}",
        #     {"tenant_subscription_id": tenant_subscription_id}
        # )
        # categories = make_request(categories_url)

        # Step 5: Get CSP offers for each product type and category
       
        offers_url = build_url(
            "/api/integrations/{{appId}}/admin/service/billing/csp/companies/getCspOffersBySubscriptionIdFromDb/{{tenant_subscription_id}}/{{customer_id}}",
            {
                "tenant_subscription_id": tenant_subscription_id,
                "customer_id": customer_id,
                "productTypes": "OnlineServicesNCE",
            }
        )
        offers = make_request(offers_url)
        company_data["offers"].append({
            "product_type": "OnlineServicesNCE",
            "offers": offers
        })

        all_data.append(company_data)

    # Step 6: Write the collected data to a JSON file
    output_file = "csp_data.json"
    with open(output_file, "w") as f:
        json.dump(all_data, f, indent=2)

    print(f"\n✅ CSP Data collected successfully. Output written to {output_file}")

# ========== EXECUTE API ==========
def execute_api(api):
    import urllib.parse
    print(f"\n➡️  Executing API: {api['name']}")
    print_context()

    if api['name'] == "Get CSP Offers By HYBR Tenant Subscription ID":
        print("\nReference product types:\n", SOFTWARE_PRODUCT_TYPES + NCE_PRODUCT_TYPES + AZURE_RESERVATION_PRODUCT_TYPES)
        print("\n")

    while True:
        # --- Collect required inputs ---
        for inp_name, inp_key in api.get("required_inputs", []):
            if inp_key not in api["inputs"]:
                # Default and remembered values
                default_val = remembered_values.get(inp_key)
                if inp_key == "tenant_subscription_id":
                    default_val = default_val or DEFAULT_TENANT_SUB_ID
                elif inp_key == "customer_id":
                    default_val = default_val or DEFAULT_CUSTOMER_ID

                prompt = f"Enter {inp_name}"
                if default_val:
                    prompt += f" (default: {default_val})"
                prompt += " (or 'skip'): "

                val = input(prompt).strip()

                if val.lower() == "skip":
                    print("⏭️ Skipped this API.")
                    return

                if not val and default_val:
                    val = default_val
                if not val:
                    print(f"❌ {inp_name} is required.")
                    continue

                # Remember and encode inputs
                remembered_values[inp_key] = val
                api["inputs"][inp_key] = urllib.parse.quote_plus(val)

        # --- Handle special sub-path logic ---
        if api["name"] == "getCspCustomerSubscriptionsByType":
            print("\nSelect subscription type:")
            print("1️⃣ Azure Subscriptions")
            print("2️⃣ Azure Reservations")
            print("3️⃣ CSP Subscriptions (NCE/Software/SaaS)")
            choice = input("Enter your choice (1/2/3): ").strip()

            sub_paths = {
                "1": "/api/integrations/{{appId}}/admin/service/billing/csp/companies/getCspCustomerAzureSubscriptions/{{tenant_subscription_id}}/{{customer_id}}",
                "2": "/api/integrations/{{appId}}/admin/service/billing/csp/companies/getAzureReservations/{{tenant_subscription_id}}/{{customer_id}}",
                "3": "/api/integrations/{{appId}}/admin/service/billing/csp/companies/getCspCustomerSubscriptions/{{tenant_subscription_id}}/{{customer_id}}"
            }

            api["inputs"]["sub_path"] = sub_paths.get(choice)
            if not api["inputs"]["sub_path"]:
                print("❌ Invalid choice. Skipping API.")
                return

        # --- Optional parameters ---
        params = prompt_optional_params(
            api.get("optional_params", []),
            reference_dict=api.get("reference_values"),
            product_type=api["inputs"].get("productTypes")
        )

        # --- Build final URL ---
        final_path = api["inputs"].get("sub_path", api["path"])
        try:
            url = build_url(final_path, api["inputs"])
        except KeyError as e:
            print(f"❌ Missing required input for URL: {e}")
            return

        # --- Add remaining inputs as query params ---
        for key, val in api["inputs"].items():
            if val and f"{{{{{key}}}}}" not in final_path and key not in params:
                params[key] = val

        # --- Execute API request ---
        res = make_request(url, params=params)
        print(f"\n📘 {api['name']} Result:\n", json.dumps(res, indent=2))

        retry = input("\nRun this API again with different inputs? (y/n): ").strip().lower()
        if retry != "y":
            break
        api["inputs"] = {}

##def execute_api(api):
##    print(f"\n➡️  Executing API: {api['name']}")
##    print_context()
##
##    # Fill required inputs
##    for inp_name, inp_key in api.get("required_inputs", []):
##        if inp_key not in api["inputs"] or inp_key in api["inputs"]:
##            remembered_val = remembered_values.get(inp_key)
##            prompt = f"Enter {inp_name}"
##            if remembered_val:
##                prompt += f" (default: {remembered_val})"
##            prompt += " (or 'skip'): "
##            val = input(prompt).strip()
##
##            if val.lower() == "skip":
##                print("⏭️ Skipped this API.")
##                return
##            if not val and remembered_val:
##                val = remembered_val
##
##            if not val:
##                print(f"❌ {inp_name} is required.")
##                return
##
##            api["inputs"][inp_key] = val
##            remembered_values[inp_key] = val
##
##    # Special case handling for subscription-type API
##    if api["name"] == "getCspCustomerSubscriptionsByType":
##        print("\nSelect subscription type:")
##        print("1️⃣ Azure Subscriptions")
##        print("2️⃣ Azure Reservations")
##        print("3️⃣ CSP Subscriptions like NCE, Software and Other SaaS products..")
##        choice = input("Enter your choice (1/2/3): ").strip()
##        if choice == "1":
##            api["inputs"]["sub_path"] = "/api/integrations/{{appId}}/admin/service/billing/csp/companies/getCspCustomerAzureSubscriptions/{{tenant_subscription_id}}/{{customer_id}}"
##        elif choice == "2":
##            api["inputs"]["sub_path"] = "/api/integrations/{{appId}}/admin/service/billing/csp/companies/getAzureReservations/{{tenant_subscription_id}}/{{customer_id}}"
##        elif choice == "3":
##            api["inputs"]["sub_path"] = "/api/integrations/{{appId}}/admin/service/billing/csp/companies/getCspCustomerSubscriptions/{{tenant_subscription_id}}/{{customer_id}}"
##        else:
##            print("❌ Invalid choice. Skipping API.")
##            return
##    # Prompt for optional params
##    params = prompt_optional_params(api.get("optional_params", []))
##    # Collect optional params
##    params = prompt_optional_params(
##        api.get("optional_params", []),
##        reference_dict=api.get("reference_values", []))
##
##    # Build URL and add query params
##    url = build_url(api["path"], api["inputs"])
##    print(url)
##    for k, v in api["inputs"].items():
##        if f"{{{k}}}" not in api["path"] and k not in params:
##            params[k] = v
##
##    print(params)
##    print(url)
##    result = make_request(url, params=params)
##    print(f"\n📘 Result:\n", json.dumps(result, indent=2))

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
     "path": "{{sub_path}}",
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
     "required_inputs": [("Tenant Subscription ID", "tenant_subscription_id"), ("Customer ID", "customer_id"), ("productTypes", "productTypes")],
     "optional_params": ["connectionId", "reservationProductTypes", "cspOfferCategories", "offerType", "segments", "search", "skip", "take"],
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
     "required_inputs": [("Month", "month"), ("Year", "year"), ("Tenant Subscription ID", "customerSubscriptionId"), ("Currency", "currency")],
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
print("3️⃣ Collect CSP Data for All Mapped Companies")
group_choice = input("Enter choice (1/2/3): ").strip()

if group_choice == "1":
    selected_apis = MS_CSP_APIS
    print("\n🟦 Selected Group: Microsoft CSP APIs")
elif group_choice == "2":
    selected_apis = REPORT_APIS
    print("\n🟨 Selected Group: Reports APIs")
    # Step 1: Initialize subscription context (only once)
    initialize_subscription_context()
elif group_choice == "3":
    collect_csp_data()
    exit()
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
