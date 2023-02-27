"""Python Flask WebApp Auth0 integration example
"""

import json
import time
import http.client
from os import environ as env
from urllib.parse import quote_plus, urlencode
from opa_client.opa import OpaClient
from authlib.integrations.flask_client import OAuth
from dotenv import find_dotenv, load_dotenv
from flask import Flask, redirect, render_template, session, url_for

ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)

application = Flask(__name__)
application.secret_key = env.get("APP_SECRET_KEY")

oauth = OAuth(application)

oauth.register(
    "auth0",
    client_id=env.get("AUTH0_CLIENT_ID"),
    client_secret=env.get("AUTH0_CLIENT_SECRET"),
    client_kwargs={
        "scope": "openid profile email",
    },
    server_metadata_url=f'https://{env.get("AUTH0_DOMAIN")}/.well-known/openid-configuration',
)


# Controllers API
@application.route("/")
def home():
    return render_template(
        "home.html",
        session=session.get("user"),
        pretty=json.dumps(session.get("user"), indent=4),
    )


@application.route("/callback", methods=["GET", "POST"])
def callback():
    token = oauth.auth0.authorize_access_token()
    session["user"] = token
    return redirect("/")


@application.route("/login")
def login():
    return oauth.auth0.authorize_redirect(
        redirect_uri=url_for("callback", _external=True)
    )


@application.route("/logout")
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
def roles():
    try:
        if session.get("user") is None:
            return redirect("/login")

        user_id = session.get("user")["userinfo"]["sub"]

        conn = http.client.HTTPSConnection(env.get("AUTH0_DOMAIN"))
        payload = json.dumps({
            "client_id": env.get("AUTH0_CLIENT_ID"),
            "client_secret": env.get("AUTH0_CLIENT_SECRET"),
            "audience": "https://" + env.get("AUTH0_DOMAIN") + "/api/v2/",
            "grant_type": "client_credentials",
        })
        headers = {'content-type': "application/json"}
        conn.request("POST", "/oauth/token", payload, headers)

        token_res = json.loads(
            conn.getresponse().read().decode("utf-8"))

        client_token = token_res["access_token"]

        headers = {'Authorization': "Bearer " + client_token}
        conn.request("GET", f"/api/v2/users/{user_id}/roles", headers=headers)

        roles = conn.getresponse().read().decode("utf-8")

        print("User roles: " + roles)

        roles = [{"name": role["name"], "description": role["description"]}
                 for role in json.loads(roles)]

        return json.dumps(roles)
    except Exception as e:
        return "An error occurred when retrieving roles: " + str(e)


@application.route("/opa")
def opa():

    try:
        response = ''


        client = OpaClient()  # default host='localhost', port=8181, version='v1'

        client.update_opa_policy_fromfile("policy.rego", "testpolicy")

        inputs = [
            {
                "input": {
                    "method": "GET",
                    "roles": ["owner"],
                    "params": {
                        "amount": 500
                    }
                }
            },
            {
                "input": {
                    "method": "POST",
                    "roles": ["owner"],
                    "params": {
                        "amount": 501
                    }
                }
            },
            {
                "input": {
                    "method": "POST",
                    "roles": ["owner"],
                    "params": {
                        "amount": 500
                    }
                }
            }
        ]

        for i in inputs:
            response += json.dumps(i) + " ==> " + str(client.check_permission(
                input_data=i, policy_name="testpolicy", rule_name="transfers")) + '<br/>'

        return response

    except Exception as e:
        return str(e)


if __name__ == "__main__":
    application.run()
