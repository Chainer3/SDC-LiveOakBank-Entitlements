"""Python Flask WebApp Auth0 integration example
"""

import json
import http.client
from os import environ as env
from urllib.parse import quote_plus, urlencode
from opa_client.opa import OpaClient
from authlib.integrations.flask_client import OAuth
from dotenv import find_dotenv, load_dotenv
from flask import Flask, redirect, render_template, session, url_for, request
from forms import CreateAccountForm
import jwt

# Get AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET, AUTH0_DOMAIN, APP_SECRET_KEY from .env file
ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)

application = Flask(__name__)
application.secret_key = env.get("APP_SECRET_KEY")

oauth = OAuth(application)

API_DOMAIN = "dit8joi4pa.execute-api.us-east-1.amazonaws.com"
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
        print("User roles: " + roles)

        roles = [
            {"name": role["name"], "description": role["description"]}
            for role in json.loads(roles)
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
        client.update_opa_policy_fromfile("policy.rego", "testpolicy")

        # Example requests
        inputs = [
            {
                "input": {
                    "method": "POST",
                    "roles": ["Owner"],
                    "params": {"amount": 15000},
                }
            },
            {
                "input": {
                    "method": "POST",
                    "roles": ["Beneficial Owner"],
                    "params": {"amount": 10000},
                }
            },
            {
                "input": {
                    "method": "POST",
                    "roles": ["Power of Attorney"],
                    "params": {"amount": 5001},
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
                        input_data=i, policy_name="testpolicy", rule_name="transfers"
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
            client.update_opa_policy_fromfile("test.rego", "testpolicy")

            # construct input to OPA
            input = {"input": request_body}
            id_token = input["input"]["payload"]["idToken"]
            id_data = jwt.decode(
                id_token, algorithms=["RS256"], options={"verify_signature": False}
            )
            user_id = id_data["sub"]

            # Make requests to OPA and return the decisions
            roles = get_roles(user_id, input["input"]["payload"]["accessToken"])

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


@application.route("/<path:path>", methods=["GET", "POST"])
def entitlement(path):
    """Forward a request to the API Gateway after checking the user's entitlements"""

    if session.get("user") is None:
        return redirect("/login")

    try:
        # Connect to locally running OPA server on port 8181
        client = OpaClient()
        client.update_opa_policy_fromfile("policy.rego", "testpolicy")
        input_data = {
            "input": {
                "method": request.method,
                "roles": [role["name"] for role in json.loads(roles())],
                "params": request.get_json(),
            }
        }

        # Check entitlement based on the request info
        if not client.check_permission(
            input_data=input_data, policy_name="testpolicy", rule_name=path
        ):
            return "Forbidden", 403

        # Forward the request to the API Gateway
        api_req = request.get_json()
        api_req["idToken"] = session.get("user")["id_token"]
        api_req["accessToken"] = get_token()

        conn = http.client.HTTPSConnection(env.get("API_DOMAIN"))
        endpoint = f"/test/bankdatamanager/{path}"
        payload = json.dumps(api_req)
        headers = {"content-type": "application/json"}
        conn.request(request.method, endpoint, payload, headers)

        api_response = json.loads(conn.getresponse().read().decode("utf-8"))
        return api_response

    except Exception as e:
        return str(e)


@application.route("/banking/createaccount", methods=("GET", "POST"))
def createAccount():
    # Redirect to login if user is not logged in
    if session.get("user") is None:
        return redirect("/login")

    messages = []
    if request.method == "POST":
        request_dict = request.form.to_dict(flat=True)

        id_token = session.get("user")["id_token"]
        access_token = get_token()

        req = {
            "accountId": request_dict["accountId"],
            "balance": int(request_dict["balance"]),
            "idToken": id_token,
            "accessToken": access_token,
        }

        conn = http.client.HTTPSConnection(API_DOMAIN)
        payload = json.dumps(req)
        headers = {"content-type": "application/json"}
        conn.request("POST", ACCOUNT_ENDPOINT, payload, headers)

        # Retrieve the response
        api_response = json.loads(conn.getresponse().read().decode("utf-8"))
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

        id_token = session.get("user")["id_token"]
        access_token = get_token()

        req = {
            "idToken": id_token,
            "accessToken": access_token,
        }

        conn = http.client.HTTPSConnection(API_DOMAIN)
        payload = json.dumps(req)
        headers = {"content-type": "application/json"}
        conn.request(
            "GET", f"{ACCOUNT_ENDPOINT}/{request_dict['accountId']}", payload, headers
        )

        # Retrieve the response
        api_response = json.loads(conn.getresponse().read().decode("utf-8"))
        # return json.dumps(api_response)
        messages = [api_response]

    # re-render the form
    form = CreateAccountForm()
    return render_template("getAccountForm.html", form=form, messages=messages)


@application.route("/banking/deleteaccount", methods=("GET", "POST"))
def deleteAccount():
    # Redirect to login if user is not logged in
    if session.get("user") is None:
        return redirect("/login")

    messages = []
    if request.method == "POST":
        request_dict = request.form.to_dict(flat=True)

        id_token = session.get("user")["id_token"]
        access_token = get_token()

        req = {
            "idToken": id_token,
            "accessToken": access_token,
        }

        conn = http.client.HTTPSConnection(API_DOMAIN)
        payload = json.dumps(req)
        headers = {"content-type": "application/json"}
        conn.request(
            "DELETE",
            f"{ACCOUNT_ENDPOINT}/{request_dict['accountId']}",
            payload,
            headers,
        )

        # Retrieve the response
        api_response = json.loads(conn.getresponse().read().decode("utf-8"))
        # return json.dumps(api_response)
        messages = [api_response]

    # re-render the form
    form = CreateAccountForm()
    return render_template("deleteAccountForm.html", form=form, messages=messages)


if __name__ == "__main__":
    application.run()
