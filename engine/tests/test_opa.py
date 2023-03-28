from opa_client.opa import OpaClient
import os

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
