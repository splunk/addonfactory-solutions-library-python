#
# Copyright 2024 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import uuid
from collections import namedtuple

from splunklib.binding import HTTPError

import context
import pytest
from solnlib.alerts_rest_client import (
    AlertsRestClient,
    AlertType,
    AlertComparator,
    AlertSeverity,
)


@pytest.fixture
def client(session_key) -> AlertsRestClient:
    return AlertsRestClient(
        session_key,
        "search",
        owner=context.owner,
        scheme=context.scheme,
        host=context.host,
        port=context.port,
    )


@pytest.fixture
def example_name():
    return f"solnlib_test_alert_{uuid.uuid4().hex}"


AlertDetails = namedtuple(
    "AlertDetails", ["name", "search", "description", "cron_schedule"]
)


@pytest.fixture
def example_alert(client, example_name):
    details = AlertDetails(
        example_name,
        f"index=main some_search_{uuid.uuid4().hex}",
        "Test alert",
        "* * * * *",
    )
    client.create_search_alert(
        details.name,
        details.search,
        description=details.description,
        cron_schedule=details.cron_schedule,
    )
    yield details
    client.delete_search_alert(details.name)


def test_delete_nonexistent_alert(client, example_name):
    with pytest.raises(HTTPError) as err:
        client.delete_search_alert(example_name)

    assert err.value.status == 404
    assert f"Could not find object id={example_name}" in err.value.body.decode()


def test_get_nonexistent_alert(client, example_name):
    with pytest.raises(HTTPError) as err:
        client.get_search_alert(example_name)

    assert err.value.status == 404
    assert f"Could not find object id={example_name}" in err.value.body.decode()


def test_create_duplicate_alert_error(client, example_alert):
    name = example_alert.name
    search = f"index=main some_search_{uuid.uuid4().hex}"

    with pytest.raises(HTTPError) as err:
        client.create_search_alert(
            name,
            search,
        )

    assert err.value.status == 409
    assert (
        f"Unable to create saved search with name '{name}'. A saved search with that name already exists."
        in err.value.body.decode()
    )


def test_update_alert(client, example_alert):
    name = example_alert.name
    description = "Updated test alert"
    cron_schedule = "*/5 * * * *"

    client.update_search_alert(
        name,
        description=description,
        cron_schedule=cron_schedule,
    )

    alert = client.get_search_alert(name)["entry"][0]
    assert alert["name"] == name
    assert alert["content"]["description"] == description
    assert alert["content"]["cron_schedule"] == cron_schedule

    # Assert that the search and other details have not changed
    assert alert["content"]["search"] == example_alert.search
    assert alert["content"]["alert_type"] == AlertType.NUMBER_OF_EVENTS.value

    other_search = f"index=main other_search_{uuid.uuid4().hex}"
    client.update_search_alert(
        name,
        search=other_search,
        description="Updated test alert",
        alert_type=AlertType.NUMBER_OF_HOSTS,
        alert_comparator=AlertComparator.LESS_THAN,
        alert_threshold=10,
        time_window=("-2h", "now"),
        alert_severity=AlertSeverity.SEVERE,
        cron_schedule="*/10 * * * *",
        expires="3d",
        disabled=False,
    )

    alert = client.get_search_alert(name)["entry"][0]
    assert alert["name"] == name
    assert alert["content"]["search"] == other_search
    assert alert["content"]["description"] == description
    assert alert["content"]["alert_type"] == AlertType.NUMBER_OF_HOSTS.value
    assert alert["content"]["alert_comparator"] == AlertComparator.LESS_THAN.value
    assert alert["content"]["alert_threshold"] == "10"
    assert alert["content"]["dispatch.earliest_time"] == "-2h"
    assert alert["content"]["dispatch.latest_time"] == "now"
    assert alert["content"]["alert.severity"] == AlertSeverity.SEVERE.value
    assert alert["content"]["cron_schedule"] == "*/10 * * * *"
    assert alert["content"]["alert.expires"] == "3d"
    assert not alert["content"]["disabled"]


def test_create_get_list_and_delete_alerts(client, example_name):
    def get_alert_names_set():
        response = client.get_all_search_alerts()
        return {alert["name"] for alert in response["entry"]}

    initial_alerts = get_alert_names_set()

    search = f"index=main some_search_{uuid.uuid4().hex}"

    # Alert has not been created yet so getting it should raise an error
    def assert_alert_not_found():
        with pytest.raises(HTTPError) as err:
            client.get_search_alert(example_name)

        assert err.value.status == 404
        assert f"Could not find object id={example_name}" in err.value.body.decode()

    assert_alert_not_found()

    # Create alert
    client.create_search_alert(
        example_name,
        search,
    )

    # Get alert
    alert = client.get_search_alert(example_name)["entry"][0]
    assert alert["name"] == example_name
    assert alert["content"]["search"] == search

    # Check default permissions
    assert alert["acl"]["sharing"] == "app"

    # Get all alerts
    alerts = get_alert_names_set()
    assert alerts - initial_alerts == {example_name}

    # Delete alert
    client.delete_search_alert(example_name)

    # Alert has been deleted so getting it should raise an error
    assert_alert_not_found()

    # Try to delete the same alert again
    with pytest.raises(HTTPError):
        client.delete_search_alert(example_name)
