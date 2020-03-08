import json
import os
import tarfile
import tempfile
from pathlib import Path

import pytest
from fastapi import HTTPException

from api.main import (
    app, bundles_by_state, list_bundles, BundleConfig, BundleState,
    delete_bundles, create_bundle,
)
from api.core.generate_data import get_bundle_path
from starlette.testclient import TestClient


client = TestClient(app)


@pytest.fixture()
def create_bundle_fix():
    f = get_bundle_path('foo')
    Path(f).touch()
    yield
    os.remove(f)
    if os.path.exists(f + '.done'):
        os.remove(f + '.done')


def test_get_bundle_not_exist():
    response = client.get("/bundles/foo")
    assert response.status_code == 404


def test_get_bundle(create_bundle_fix):
    response = client.get("/bundles/foo?done=False")
    assert response.status_code == 200
    assert not os.path.exists(get_bundle_path('foo') + '.done')


def test_get_bundle_done(create_bundle_fix):
    response = client.get("/bundles/foo?done=True")
    assert response.status_code == 200
    assert os.path.exists(get_bundle_path('foo') + '.done')


UUIDs = [
    '0' * 32,
    '1' * 32,
    '2' * 32,
]


def test_bundles_by_state(mocker):
    file_list = [
        UUIDs[0] + '.tar.gz.done',
        UUIDs[1] + '.tar.gz',
        UUIDs[1] + '.tar.gz.done',
        UUIDs[2] + '.tar.gz',
    ]
    mocker.patch('api.main.listdir', return_value=file_list)
    tars, done, purge = bundles_by_state()
    assert purge == [UUIDs[1]]
    assert done == [UUIDs[0], UUIDs[1]]
    assert tars == [UUIDs[2]]


def test_list_bundles(mocker):
    tars = [UUIDs[2]]
    done = [UUIDs[0], UUIDs[1]]
    purge = [UUIDs[1]]
    mocker.patch('api.main.bundles_by_state', return_value=[tars, done, purge])
    out = list_bundles().sort(key=lambda x: x.uuid)
    expected = [
        BundleState(uuid=UUIDs[0], processed=True),
        BundleState(uuid=UUIDs[1], processed=True),
        BundleState(uuid=UUIDs[2], processed=False),
    ].sort(key=lambda x: x.uuid)
    assert out == expected


def test_create_bundle_and_process(mocker):
    notify_upload = mocker.patch('api.main.notify_upload')
    mocker.patch('api.main.TestDataGenerator')
    create_bundle(BundleConfig())
    notify_upload.assert_called_once()


def test_create_bundle_no_processing(mocker):
    notify_upload = mocker.patch('api.main.notify_upload')
    mocker.patch('api.main.TestDataGenerator')
    create_bundle(BundleConfig(), process=False)
    notify_upload.assert_not_called()


def test_create_bundle(mocker):
    bundle_config = BundleConfig(
        install_uuid='install_1234',
        tower_url_base='base_url_is_this',
        instance_uuid='instance_12345',
    )
    config = create_bundle(bundle_config, process=False)
    temp_dir = tempfile.mkdtemp()
    bundle_file = get_bundle_path(config.bundle_uuid)
    tar = tarfile.open(bundle_file)
    tar.extractall(path=temp_dir)
    tar.close()
    with open(os.path.join(temp_dir, 'config.json')) as f:
        config_json_data = json.loads(f.read())
        assert config_json_data['install_uuid'] == 'install_1234'
        assert config_json_data['tower_url_base'] == 'base_url_is_this'
        assert config_json_data['instance_uuid'] == 'instance_12345'
    os.remove(bundle_file)


def test_delete_processed_bundles(mocker):
    tars = [UUIDs[2]]
    done = [UUIDs[0], UUIDs[1]]
    purge = [UUIDs[1]]
    bundles_by_state = mocker.patch(
        'api.main.bundles_by_state',
        return_value=[tars, done, purge])
    remove_processed_bundles = mocker.patch(
        'api.main.remove_processed_bundles')
    background_tasks = mocker.MagicMock()
    delete_bundles(background_tasks)
    bundles_by_state.assert_called_once()
    background_tasks.add_task.assert_called_once_with(
        remove_processed_bundles, purge)


def test_delete_a_non_existing_bundle(mocker):
    mocker.patch('os.path.isfile', return_value=False)
    background_tasks = mocker.MagicMock()
    with pytest.raises(HTTPException):
        delete_bundles(background_tasks, UUIDs[0])
    background_tasks.add_task.assert_not_called()


def test_delete_a_bundle(mocker):
    mocker.patch('os.path.isfile', return_value=True)
    remove_processed_bundles = mocker.patch(
        'api.main.remove_processed_bundles')
    background_tasks = mocker.MagicMock()
    delete_bundles(background_tasks, UUIDs[0])
    background_tasks.add_task.assert_called_once_with(
        remove_processed_bundles,
        [UUIDs[0]])
