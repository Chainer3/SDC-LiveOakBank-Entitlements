from application import application
from opa_client.opa import OpaClient
from unittest.mock import patch

import sys
import os

test_dir = os.path.dirname(os.path.abspath(__file__))
app_dir = os.path.join(test_dir, '..')
sys.path.append(app_dir)

response = ''
# Connect to locally running OPA server on port 8181
client = OpaClient()  # default host='localhost', port=8181, version='v1'
# Load a policy from the local file test-policy.rego
client.update_opa_policy_fromfile(os.path.join(
    os.path.dirname(__file__), "test-policy.rego"), "testpolicy")


def test_transfers1():

    input = {
        "input": {
            "method": "POST",
            "roles": ["Owner"],
            "params": {
                "amount": 15000
            }
        }
    }

    assert client.check_permission(
        input_data=input, policy_name="testpolicy", rule_name="transfers") == {'result': True}

    # Negative amount
    input["input"]["params"]["amount"] = -1

    assert client.check_permission(
        input_data=input, policy_name="testpolicy", rule_name="transfers") == {'result': False}

    # Exceed limit
    input["input"]["params"]["amount"] = 10001
    input["input"]["roles"] = ["Beneficial Owner"]

    assert client.check_permission(
        input_data=input, policy_name="testpolicy", rule_name="transfers") == {'result': False}

    input["input"]["params"]["amount"] = 5001
    input["input"]["roles"] = ["Power of Attorney"]

    assert client.check_permission(
        input_data=input, policy_name="testpolicy", rule_name="transfers") == {'result': False}


def test_transfers2():

    input = {
        "input": {
            "method": "POST",
            "roles": ["Beneficial Owner"],
            "params": {
                "amount": 10000
            }
        }
    }

    assert client.check_permission(
        input_data=input, policy_name="testpolicy", rule_name="transfers") == {'result': True}

    input["input"]["roles"] = ["Owner", "Beneficial Owner"]

    assert client.check_permission(
        input_data=input, policy_name="testpolicy", rule_name="transfers") == {'result': True}

    input["input"]["roles"] = []

    assert client.check_permission(
        input_data=input, policy_name="testpolicy", rule_name="transfers") == {'result': False}

    input["input"]["roles"] = ["something", "Beneficial Owner"]

    assert client.check_permission(
        input_data=input, policy_name="testpolicy", rule_name="transfers") == {'result': True}


def test_transfers3():

    input = {
        "input": {
            "method": "POST",
            "roles": ["Beneficial Owner"],
            "params": {
                "amount": 10000
            }
        }
    }

    assert client.check_permission(
        input_data=input, policy_name="testpolicy", rule_name="transfers") == {'result': True}

    input["input"]["roles"] = ["Owner", "Beneficial Owner"]

    assert client.check_permission(
        input_data=input, policy_name="testpolicy", rule_name="transfers") == {'result': True}

    input["input"]["roles"] = []

    assert client.check_permission(
        input_data=input, policy_name="testpolicy", rule_name="transfers") == {'result': False}

    input["input"]["roles"] = ["something", "Beneficial Owner"]

    assert client.check_permission(
        input_data=input, policy_name="testpolicy", rule_name="transfers") == {'result': True}


def test_accounts1():

    input = {
        "input": {
            "method": "PUT",
            "roles": ["Power of Attorney"],
        }
    }

    assert client.check_permission(
        input_data=input, policy_name="testpolicy", rule_name="accounts") == {'result': False}

    input["input"]["method"] = "GET"

    assert client.check_permission(
        input_data=input, policy_name="testpolicy", rule_name="accounts") == {'result': True}

# Test for the case when the user has multiple roles


def test_accounts2():

    input = {
        "input": {
            "method": "GET",
            "roles": ["Power of Attorney", "Beneficial Owner"],
        }
    }

    assert client.check_permission(
        input_data=input, policy_name="testpolicy", rule_name="accounts") == {'result': True}

    input["input"]["roles"] = [
        "Power of Attorney", "Beneficial Owner", "Owner"]

    assert client.check_permission(
        input_data=input, policy_name="testpolicy", rule_name="accounts") == {'result': True}

    input["input"]["roles"] = ["Power of Attorney",
                               "Beneficial Owner", "Owner", "something"]

    assert client.check_permission(
        input_data=input, policy_name="testpolicy", rule_name="accounts") == {'result': True}


def test_owner():

    input = {
        "input": {
            "method": "POST",
            "roles": ["Power of Attorney", "Owner"],
            "params": {
                "amount": 999999999
            }
        }
    }

    assert client.check_permission(
        input_data=input, policy_name="testpolicy", rule_name="transfers") == {'result': True}

    input["input"]["roles"] = ["Power of Attorney", "Owner", "something"]

    assert client.check_permission(
        input_data=input, policy_name="testpolicy", rule_name="transfers") == {'result': True}

    input["input"]["roles"] = ["Power of Attorney",
                               "something", "something else"]

    assert client.check_permission(
        input_data=input, policy_name="testpolicy", rule_name="transfers") == {'result': False}


# test changing policy file and reloading
def test_reload_policy():

    input = {
        "input": {
            "method": "POST",
            "roles": ["Power of Attorney"],
            "params": {
                "amount": 10000
            }
        }
    }

    assert client.check_permission(
        input_data=input, policy_name="testpolicy", rule_name="transfers") == {'result': False}

    # Update policy file
    client.update_opa_policy_fromfile(os.path.join(
        os.path.dirname(__file__), "test-policy2.rego"), "testpolicy")

    # Check if the policy was updated
    assert client.check_permission(
        input_data=input, policy_name="testpolicy", rule_name="transfers") == {'result': True}

    # Update policy file
    client.update_opa_policy_fromfile(os.path.join(
        os.path.dirname(__file__), "test-policy.rego"), "testpolicy")

    # Check if the policy was updated
    assert client.check_permission(
        input_data=input, policy_name="testpolicy", rule_name="transfers") == {'result': False}


def test_login():
    # the login should redirect to an auth0 url
    response = application.test_client().get('/login')
    assert response.status_code == 302
    assert response.headers['Location'].startswith('https://dev-')


def test_home():
    # going home should render an html page
    response = application.test_client().get('/')
    assert response.status_code == 200
    assert 'html' in response.headers['Content-Type']
    assert b'Welcome' in response.data

# test /banking/{createaccount, getaccount, deleteaccount, deposit, transfer, accounts} endpoints


def logged_out():
    # should all redirect if not logged in (session.get("user") is None)
    response = application.test_client().get('/banking/createaccount')
    assert response.status_code == 302
    response = application.test_client().get('/banking/getaccount')
    assert response.status_code == 302
    response = application.test_client().get('/banking/deleteaccount')
    assert response.status_code == 302
    response = application.test_client().get('/banking/deposit')
    assert response.status_code == 302
    response = application.test_client().get('/banking/transfer')
    assert response.status_code == 302
    response = application.test_client().get('/banking/accounts')
    assert response.status_code == 302


def logged_in():
    with application.test_client() as c:
        with c.session_transaction() as sess:
            sess['user'] = {'name': 'testuser'}
        # should all return 200
        response = c.get('/banking/createaccount')
        assert response.status_code == 200
        response = c.get('/banking/getaccount')
        assert response.status_code == 200
        response = c.get('/banking/deleteaccount')
        assert response.status_code == 200
        response = c.get('/banking/deposit')
        assert response.status_code == 200
        response = c.get('/banking/transfer')
        assert response.status_code == 200
        response = c.get('/banking/accounts')
        assert response.status_code == 200

        # test /admin endpoint
        response = c.get('/admin')
        assert response.status_code == 200
        assert b'Admin access required' in response.data

        # test /admin by overriding is_admin() to return true
        with patch('app.is_admin', return_value=True):
            response = c.get('/admin')
            assert response.status_code == 200
            assert b'Admin' in response.data
