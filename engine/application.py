"""Python Flask WebApp Auth0 integration example
"""

import json
import http.client
import os
import datetime
import glob
from os import environ as env
from urllib.parse import quote_plus, urlencode
from opa_client.opa import OpaClient
from authlib.integrations.flask_client import OAuth
from dotenv import find_dotenv, load_dotenv
from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    session,
    url_for,
    request,
    send_from_directory,
)
from forms import CreateAccountForm, AccountForm, DepositAccountForm, TransferForm
import jwt

# Get AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET, AUTH0_DOMAIN, APP_SECRET_KEY from .env file
ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)

application = Flask(__name__)
application.secret_key = env.get("APP_SECRET_KEY")
application.config["RULES_FOLDER"] = "rules_folder"
ALLOWED_EXTENSIONS = {"rego"}

oauth = OAuth(application)

API_DOMAIN = env.get("API_DOMAIN")
ENDPOINT_BASE = "/test/bankdatamanager"
TRANSFER_ENDPOINT = f"{ENDPOINT_BASE}/transfer"
DEPOSIT_ENDPOINT = f"{ENDPOINT_BASE}/deposit"
ACCOUNT_ENDPOINT = f"{ENDPOINT_BASE}/accounts"

# Configure Auth0
oauth.register(
    "auth0",
    client_id=env.get("AUTH0_CLIENT_ID"),
    client_secret=env.get("AUTH0_CLIENT_SECRET"),
    client_kwargs={
        "scope": "openid profile email",
    },
    server_metadata_url=f'https://{env.get("AUTH0_DOMAIN")}/.well-known/openid-configuration',
)


def get_token():
    """Connect to Auth0 management API to get a token"""
    conn = http.client.HTTPSConnection(env.get("AUTH0_DOMAIN"))
    payload = json.dumps(
        {
            "client_id": env.get("AUTH0_CLIENT_ID"),
            "client_secret": env.get("AUTH0_CLIENT_SECRET"),
            "audience": "https://" + env.get("AUTH0_DOMAIN") + "/api/v2/",
            "grant_type": "client_credentials",
        }
    )
    headers = {"content-type": "application/json"}
    conn.request("POST", "/oauth/token", payload, headers)

    # Retrieve the token
    token_res = json.loads(conn.getresponse().read().decode("utf-8"))
    # print(token_res["access_token"])
    return token_res["access_token"]


def get_roles(user_id, client_token):
    """Get the user's roles from Auth0 using their ID"""
    conn = http.client.HTTPSConnection(env.get("AUTH0_DOMAIN"))
    headers = {"Authorization": "Bearer " + client_token}
    conn.request("GET", f"/api/v2/users/{user_id}/roles", headers=headers)

    return json.loads(conn.getresponse().read().decode("utf-8"))


@application.route("/")
# Home page that displays the user's info
def home():
    return render_template(
        "home.html",
        session=session.get("user"),
        pretty=json.dumps(session.get("user"), indent=4),
    )


@application.route("/callback", methods=["GET", "POST"])
# Callback handler for Auth0 that authorizes the user and sets the session
def callback():
    token = oauth.auth0.authorize_access_token()
    session["user"] = token
    return redirect("/")


@application.route("/login")
# Redirect to Auth0 login page
def login():
    return oauth.auth0.authorize_redirect(
        redirect_uri=url_for("callback", _external=True)
    )


@application.route("/logout")
# Redirect to Auth0 logout page
def logout():
    session.clear()
    return redirect(
        "https://"
        + env.get("AUTH0_DOMAIN")
        + "/v2/logout?"
        + urlencode(
            {
                "returnTo": url_for("home", _external=True),
                "client_id": env.get("AUTH0_CLIENT_ID"),
            },
            quote_via=quote_plus,
        )
    )


@application.route("/roles")
# Get the user's roles from Auth0
def roles():
    try:
        # Redirect to login if user is not logged in
        if session.get("user") is None:
            return redirect("/login")

        # Get user ID
        user_id = session.get("user")["userinfo"]["sub"]

        client_token = get_token()
        print(client_token)

        roles = get_roles(user_id, client_token)
        print(roles)

        roles = [
            {"name": role["name"], "description": role["description"]} for role in roles
        ]

        # Return the user's roles
        return json.dumps(roles)
    except Exception as e:
        return "An error occurred when retrieving roles: " + str(e)


@application.route("/opa")
# Connect to OPA and make some example decisions
def opa():

    try:
        response = ""

        # Connect to locally running OPA server on port 8181
        client = OpaClient()  # default host='localhost', port=8181, version='v1'

        # Load a policy from the local file policy.rego
        client.update_opa_policy_fromfile(
            os.path.join(application.config["RULES_FOLDER"], "policy.rego"),
            "testpolicy",
        )

        # Example requests
        inputs = [
            {
                "input": {
                    "method": "POST",
                    "roles": ["owner"],
                    "payload": {"amount": 15000},
                }
            },
            {
                "input": {
                    "method": "POST",
                    "roles": ["beneficial owner"],
                    "payload": {"amount": 10000},
                }
            },
            {
                "input": {
                    "method": "POST",
                    "roles": ["power of attorney"],
                    "payload": {"amount": 5001},
                }
            },
        ]

        # Make requests to OPA and return the decisions
        for i in inputs:
            response += (
                json.dumps(i)
                + " ==> "
                + str(
                    client.check_permission(
                        input_data=i, policy_name="testpolicy", rule_name="transfer"
                    )
                )
                + "<br/>"
            )

        return response

    except Exception as e:
        return str(e)


@application.route("/enginetesting", methods=["GET", "POST"])
# test evaluating a transfer request
def enginetesting():
    PROTECT_ENDPOINTS = ["transfer"]
    if request.method == "POST":
        request_body = json.loads(request.data)
        # {'operation': 'transfer', token: 'xxxxxxx', user_id: 'xxxxxx',  'payload': {'sourceId': '2', 'destId': '1', 'amount': 25}}
        try:
            rule_name = request_body["operation"]
            if not rule_name in PROTECT_ENDPOINTS:
                response = json.dumps({"result": True})
                return response

            # Connect to locally running OPA server on port 8181
            client = OpaClient()  # default host='localhost', port=8181, version='v1'

            # Load a policy from the local file policy.rego
            client.update_opa_policy_fromfile(
                os.path.join(
                    application.config["RULES_FOLDER"], "policy.rego"),
                "testpolicy",
            )

            # construct input to OPA
            input = {"input": request_body}
            id_token = input["input"]["payload"]["idToken"]
            id_data = jwt.decode(
                id_token, algorithms=["RS256"], options={"verify_signature": False}
            )
            user_id = id_data["sub"]

            # Make requests to OPA and return the decisions
            roles = get_roles(
                user_id, input["input"]["payload"]["accessToken"])

            roles = [role["name"].lower() for role in roles]

            input["input"]["roles"] = roles

            decision = client.check_permission(
                input_data=input, policy_name="testpolicy", rule_name=rule_name
            )
            # response = ""
            # response += (
            #     json.dumps(input)
            #     + " ==> "
            #     + str(
            #         client.check_permission(
            #             input_data=input, policy_name="testpolicy", rule_name=rule_name
            #         )
            #     )
            #     + "<br/>"
            # )

            return decision
        except Exception as e:
            response = json.dumps({"result": False, "error": str(e)})
            return response
    elif request.method == "GET":
        # Get user ID
        user_id = session.get("user")["userinfo"]["sub"]
        id_token = session.get("user")["id_token"]
        client_token = get_token()
        # token_data = jwt.decode(
        #     client_token, algorithms=["RS256"], options={"verify_signature": False}
        # )
        # print(f"id token: {id_token}")
        # print(f"access token: {client_token}")

        transfer_req = {
            "sourceId": "2",
            "destId": "1",
            "amount": 25,
            "idToken": id_token,
            "accessToken": client_token,
        }

        conn = http.client.HTTPSConnection(API_DOMAIN)
        payload = json.dumps(transfer_req)
        headers = {"content-type": "application/json"}
        conn.request("POST", TRANSFER_ENDPOINT, payload, headers)

        # Retrieve the token
        api_response = json.loads(conn.getresponse().read().decode("utf-8"))
        return json.dumps(api_response)
        # return json.dumps(transfer_req)


# @application.route("/<path:path>", methods=["GET", "POST"])
# def entitlement(path):
#     """Forward a request to the API Gateway after checking the user's entitlements"""

#     if session.get("user") is None:
#         return redirect("/login")

#     try:
#         # Connect to locally running OPA server on port 8181
#         client = OpaClient()
#         client.update_opa_policy_fromfile("policy.rego", "testpolicy")
#         input_data = {
#             "input": {
#                 "method": request.method,
#                 "roles": [role["name"] for role in json.loads(roles())],
#                 "params": request.get_json(),
#             }
#         }

#         # Check entitlement based on the request info
#         if not client.check_permission(
#             input_data=input_data, policy_name="testpolicy", rule_name=path
#         ):
#             return "Forbidden", 403

#         # Forward the request to the API Gateway
#         api_req = request.get_json()
#         api_req["idToken"] = session.get("user")["id_token"]
#         api_req["accessToken"] = get_token()

#         conn = http.client.HTTPSConnection(env.get("API_DOMAIN"))
#         endpoint = f"/test/bankdatamanager/{path}"
#         payload = json.dumps(api_req)
#         headers = {"content-type": "application/json"}
#         conn.request(request.method, endpoint, payload, headers)

#         api_response = json.loads(conn.getresponse().read().decode("utf-8"))
#         return api_response

#     except Exception as e:
#         return str(e)


def sendAPIRequest(req_dict, endpoint, method, with_tokens=True):
    """Helper function to send API request to the lambda. By default adds
    id and access tokens to the request json. Uses the provided endpoint
    and method in addition to the global API_DOMAIN"""
    id_token = session.get("user")["id_token"]
    access_token = get_token()

    if with_tokens:
        req_dict["idToken"] = id_token
        req_dict["accessToken"] = access_token

    conn = http.client.HTTPSConnection(API_DOMAIN)
    payload = json.dumps(req_dict)
    headers = {"content-type": "application/json"}
    conn.request(
        method,
        endpoint,
        payload,
        headers,
    )

    # Return the response
    return json.loads(conn.getresponse().read().decode("utf-8"))


@application.route("/banking", methods=["GET"])
def bankingFormsHome():
    return render_template("bankingHome.html")


@application.route("/banking/createaccount", methods=("GET", "POST"))
def createAccount():
    # Redirect to login if user is not logged in
    if session.get("user") is None:
        return redirect("/login")

    messages = []
    if request.method == "POST":
        request_dict = request.form.to_dict(flat=True)

        req = {
            "accountId": request_dict["accountId"],
            "balance": int(request_dict["balance"]),
        }

        api_response = sendAPIRequest(
            req, ACCOUNT_ENDPOINT, "POST", with_tokens=True)

        # return json.dumps(api_response)
        messages = [api_response]

    # re-render the form
    form = CreateAccountForm()
    return render_template("createAccountForm.html", form=form, messages=messages)


@application.route("/banking/getaccount", methods=("GET", "POST"))
def getAccount():
    # Redirect to login if user is not logged in
    if session.get("user") is None:
        return redirect("/login")

    messages = []
    if request.method == "POST":
        request_dict = request.form.to_dict(flat=True)

        api_response = sendAPIRequest(
            {},
            f"{ACCOUNT_ENDPOINT}/{request_dict['accountId']}",
            "GET",
            with_tokens=True,
        )
        # return json.dumps(api_response)
        messages = [api_response]

    # re-render the form
    form = AccountForm()
    return render_template(
        "accountForm.html",
        form=form,
        messages=messages,
        title_label="Get Bank Account Info",
    )


@application.route("/banking/deleteaccount", methods=("GET", "POST"))
def deleteAccount():
    # Redirect to login if user is not logged in
    if session.get("user") is None:
        return redirect("/login")

    messages = []
    if request.method == "POST":
        request_dict = request.form.to_dict(flat=True)

        api_response = sendAPIRequest(
            {},
            f"{ACCOUNT_ENDPOINT}/{request_dict['accountId']}",
            "DELETE",
            with_tokens=True,
        )
        # return json.dumps(api_response)
        messages = [api_response]

    # re-render the form
    form = AccountForm()
    return render_template(
        "accountForm.html",
        form=form,
        messages=messages,
        title_label="Delete Bank Account",
    )


@application.route("/banking/deposit", methods=("GET", "POST"))
def deposit():
    # Redirect to login if user is not logged in
    if session.get("user") is None:
        return redirect("/login")

    messages = []
    if request.method == "POST":
        request_dict = request.form.to_dict(flat=True)

        req = {"amount": int(request_dict["amount"])}
        api_response = sendAPIRequest(
            req,
            f"{DEPOSIT_ENDPOINT}/{request_dict['accountId']}",
            "POST",
            with_tokens=True,
        )
        # return json.dumps(api_response)
        messages = [api_response]

    # re-render the form
    form = DepositAccountForm()
    return render_template(
        "depositAccountForm.html",
        form=form,
        messages=messages,
    )


@application.route("/banking/transfer", methods=("GET", "POST"))
def transfer():
    # Redirect to login if user is not logged in
    if session.get("user") is None:
        return redirect("/login")

    messages = []
    if request.method == "POST":
        request_dict = request.form.to_dict(flat=True)

        req = {
            "sourceId": request_dict["sourceId"],
            "destId": request_dict["destId"],
            "amount": int(request_dict["amount"]),
            "memo": request_dict["memo"],
        }
        api_response = sendAPIRequest(
            req,
            TRANSFER_ENDPOINT,
            "POST",
            with_tokens=True,
        )
        # return json.dumps(api_response)
        messages = [api_response]

    # re-render the form
    form = TransferForm()
    return render_template(
        "transferForm.html",
        form=form,
        messages=messages,
    )


@application.route("/banking/accounts")
def accountsHome():
    """Display basic information for all accounts"""
    # Redirect to login if user is not logged in
    if session.get("user") is None:
        return redirect("/login")

    api_response = sendAPIRequest(
        {},
        ACCOUNT_ENDPOINT,
        "GET",
        with_tokens=True,
    )
    accounts = api_response["Items"]
    print(accounts)

    return render_template("accountsHome.html", accounts=accounts)


@application.route("/banking/accounts/<id>")
def accountHistory(id):
    """Show transfer history for the account corresponding with the route param"""
    # Redirect to login if user is not logged in
    if session.get("user") is None:
        return redirect("/login")

    api_response = sendAPIRequest(
        {},
        TRANSFER_ENDPOINT,
        "GET",
        with_tokens=True,
    )
    all_transfers = api_response["Items"]

    transfers = []
    for transfer in all_transfers:
        if transfer["sourceId"] == id: #or transfer["destId"] == id:
            transfers.append((transfer))

    print(transfers)

    return render_template("accountHistory.html", accountId=id, transfers=transfers)


def is_admin():
    if session.get("user") is None:
        return False
    user_id = session.get("user")["userinfo"]["sub"]
    access_token = get_token()
    roles = [role["name"] for role in get_roles(user_id, access_token)]

    if not "Admin" in roles:
        return False
    return True


@application.route("/admin/")
def admin():
    if not is_admin():
        return "Admin access required"

    rule_files = glob.glob(application.config["RULES_FOLDER"] + "/*.rego*")
    rule_files = [
        f.lstrip(application.config["RULES_FOLDER"] + "/") for f in rule_files
    ]
    return render_template("admin.html", rule_files=rule_files)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@application.route("/admin/upload_rules", methods=["POST"])
def upload_rules():
    if not is_admin():
        return redirect(url_for("admin"))
    # check if the post request has the file part
    if "file" not in request.files:
        flash("No file part")
        return redirect(url_for("admin"))
    file = request.files["file"]
    # If the user does not select a file, the browser submits an
    # empty file without a filename.
    if file.filename == "":
        flash("No selected file")
    elif file and allowed_file(file.filename):
        flash(f"Uploaded {file.filename}")
        filename = file.filename
        timestamp = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S.%f]")
        rules_file = os.path.join(
            application.config["RULES_FOLDER"], "policy.rego")

        # Save old rules policy
        os.rename(rules_file, rules_file + timestamp)
        file.save(os.path.join(
            application.config["RULES_FOLDER"], "policy.rego"))
    return redirect(url_for("admin"))


@application.route("/admin/download_rules", methods=["POST"])
def download_rules():
    if not is_admin():
        return redirect(url_for("admin"))
    request_dict = request.form.to_dict(flat=True)
    print(request_dict)
    return send_from_directory(
        application.config["RULES_FOLDER"], request_dict["filename"]
    )


if __name__ == "__main__":
    application.run()
