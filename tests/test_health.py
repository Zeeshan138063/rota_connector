def test_connector_health(connector, httpx_mock):
    httpx_mock.add_response(
        method="GET",
        url=f"{connector._base_client.base_url}/api/v1/health",
        json={"status": "healthy", "version": "1.0.0"}
    )

    result = connector.health()
    assert result["status"] == "healthy"
