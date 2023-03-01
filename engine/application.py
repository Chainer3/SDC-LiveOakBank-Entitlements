"""Python Flask WebApp Auth0 integration example
"""

import json
import http.client
from os import environ as env
from urllib.parse import quote_plus, urlencode
from opa_client.opa import OpaClient
from authlib.integrations.flask_client import OAuth
from dotenv import find_dotenv, load_dotenv
from flask import Flask, redirect, render_template, session, url_for

# Get AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET, AUTH0_DOMAIN, APP_SECRET_KEY from .env file
ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)

application = Flask(__name__)
application.secret_key = env.get("APP_SECRET_KEY")

oauth = OAuth(application)

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

        # Connect to Auth0 management API to get a token
        conn = http.client.HTTPSConnection(env.get("AUTH0_DOMAIN"))
        payload = json.dumps({
            "client_id": env.get("AUTH0_CLIENT_ID"),
            "client_secret": env.get("AUTH0_CLIENT_SECRET"),
            "audience": "https://" + env.get("AUTH0_DOMAIN") + "/api/v2/",
            "grant_type": "client_credentials",
        })
        headers = {'content-type': "application/json"}
        conn.request("POST", "/oauth/token", payload, headers)

        # Retrieve the token
        token_res = json.loads(
            conn.getresponse().read().decode("utf-8"))
        client_token = token_res["access_token"]

        # Get the user's roles from Auth0 using their ID
        headers = {'Authorization': "Bearer " + client_token}
        conn.request("GET", f"/api/v2/users/{user_id}/roles", headers=headers)

        roles = conn.getresponse().read().decode("utf-8")

        print("User roles: " + roles)

        roles = [{"name": role["name"], "description": role["description"]}
                 for role in json.loads(roles)]

        # Return the user's roles
        return json.dumps(roles)
    except Exception as e:
        return "An error occurred when retrieving roles: " + str(e)


@application.route("/opa")
# Connect to OPA and make some example decisions
def opa():

    try:
        response = ''

        # Connect to locally running OPA server on port 8181
        client = OpaClient()  # default host='localhost', port=8181, version='v1'

        # Load a policy from the local file policy.rego
        client.update_opa_policy_fromfile("policy.rego", "testpolicy")

        # Example requests
        inputs = [
            {
                "input": {
                    "method": "POST",
                    "roles": ["owner"],
                    "params": {
                        "amount": 15000
                    }
                }
            },
            {
                "input": {
                    "method": "POST",
                    "roles": ["beneficial_owner"],
                    "params": {
                        "amount": 10000
                    }
                }
            },
            {
                "input": {
                    "method": "POST",
                    "roles": ["power_of_attorney"],
                    "params": {
                        "amount": 5001
                    }
                }
            }
        ]

        # Make requests to OPA and return the decisions
        for i in inputs:
            response += json.dumps(i) + " ==> " + str(client.check_permission(
                input_data=i, policy_name="testpolicy", rule_name="transfers")) + '<br/>'

        return response

    except Exception as e:
        return str(e)


if __name__ == "__main__":
    application.run()
