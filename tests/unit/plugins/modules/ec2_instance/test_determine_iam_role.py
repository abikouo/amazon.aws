# (c) 2022 Red Hat Inc.
#
# This file is part of Ansible
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import sys
from unittest.mock import MagicMock
from unittest.mock import sentinel

import pytest

import ansible_collections.amazon.aws.plugins.module_utils.arn as utils_arn
import ansible_collections.amazon.aws.plugins.modules.ec2_instance as ec2_instance_module
from ansible_collections.amazon.aws.plugins.module_utils.botocore import HAS_BOTO3

try:
    import botocore
except ImportError:
    pass

pytest.mark.skipif(
    not HAS_BOTO3, reason="test_determine_iam_role.py requires the python modules 'boto3' and 'botocore'"
)


def _client_error(code="GenericError"):
    return botocore.exceptions.ClientError(
        {
            "Error": {"Code": code, "Message": "Something went wrong"},
            "ResponseMetadata": {"RequestId": "01234567-89ab-cdef-0123-456789abcdef"},
        },
        "some_called_method",
    )


class FailJsonException(Exception):
    def __init__(self):
        pass


@pytest.fixture
def ec2_instance(monkeypatch):
    monkeypatch.setattr(ec2_instance_module, "validate_aws_arn", lambda arn, service, resource_type: None)
    return ec2_instance_module


@pytest.fixture
def ansible_module():
    module = MagicMock()
    module.fail_json.side_effect = FailJsonException()
    module.fail_json_aws.side_effect = FailJsonException()
    return module


def test_determine_iam_role_arn(ec2_instance, ansible_module, monkeypatch):
    # Revert the default monkey patch to make it simple to try passing a valid ARNs
    monkeypatch.setattr(ec2_instance, "validate_aws_arn", utils_arn.validate_aws_arn)

    # Simplest example, someone passes a valid instance profile ARN
    arn = ec2_instance.determine_iam_role(ansible_module, "arn:aws:iam::123456789012:instance-profile/myprofile")
    assert arn == "arn:aws:iam::123456789012:instance-profile/myprofile"


def test_determine_iam_role_name(ec2_instance, ansible_module):
    profile_description = {"InstanceProfile": {"Arn": sentinel.IAM_PROFILE_ARN}}
    iam_client = MagicMock(**{"get_instance_profile.return_value": profile_description})
    ansible_module.client.return_value = iam_client

    arn = ec2_instance.determine_iam_role(ansible_module, sentinel.IAM_PROFILE_NAME)
    assert arn == sentinel.IAM_PROFILE_ARN


def test_determine_iam_role_missing(ec2_instance, ansible_module):
    missing_exception = _client_error("NoSuchEntity")
    iam_client = MagicMock(**{"get_instance_profile.side_effect": missing_exception})
    ansible_module.client.return_value = iam_client

    with pytest.raises(FailJsonException):
        ec2_instance.determine_iam_role(ansible_module, sentinel.IAM_PROFILE_NAME)

    assert ansible_module.fail_json_aws.call_count == 1
    assert ansible_module.fail_json_aws.call_args.args[0] is missing_exception
    assert "Could not find" in ansible_module.fail_json_aws.call_args.kwargs["msg"]


@pytest.mark.skipif(sys.version_info < (3, 8), reason="call_args behaviour changed in Python 3.8")
def test_determine_iam_role_missing(ec2_instance, ansible_module):
    missing_exception = _client_error()
    iam_client = MagicMock(**{"get_instance_profile.side_effect": missing_exception})
    ansible_module.client.return_value = iam_client

    with pytest.raises(FailJsonException):
        ec2_instance.determine_iam_role(ansible_module, sentinel.IAM_PROFILE_NAME)

    assert ansible_module.fail_json_aws.call_count == 1
    assert ansible_module.fail_json_aws.call_args.args[0] is missing_exception
    assert "An error occurred while searching" in ansible_module.fail_json_aws.call_args.kwargs["msg"]
    assert "Please try supplying the full ARN" in ansible_module.fail_json_aws.call_args.kwargs["msg"]
