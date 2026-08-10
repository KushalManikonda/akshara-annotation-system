import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_audio_stream_no_gzip():
    # We will mock the database dependency to avoid needing a real task and audio file
    # Or, wait, we can just send a request to a non-existent task and check if it handles it.
    # Actually, if we send a request for a non-existent task, it will return 404, which is not what we want to test for gzip.
    # We want to test a 206 response.
    # Let's mock `stream_audio` endpoint or just check the gzip middleware behavior directly.
    # Better to mock the endpoint.
    from fastapi import APIRouter
    from fastapi.responses import Response

    test_app = app
    
    @test_app.get("/api/test_audio/stream")
    def dummy_stream():
        # simulate a 206 response with content length > 1024
        content = b"a" * 2048
        return Response(content, status_code=206, headers={"Content-Type": "audio/wav", "Content-Length": "2048"})
    
    test_client = TestClient(test_app)
    
    response = test_client.get("/api/test_audio/stream", headers={"Accept-Encoding": "gzip"})
    
    # It should NOT be gzipped
    assert response.status_code == 206
    assert response.headers.get("Content-Encoding") != "gzip"
    assert response.headers.get("Content-Length") == "2048"

def test_other_endpoint_has_gzip():
    test_app = app
    
    @test_app.get("/api/test_json")
    def dummy_json():
        return {"data": "a" * 2048}
    
    test_client = TestClient(test_app)
    
    response = test_client.get("/api/test_json", headers={"Accept-Encoding": "gzip"})
    
    # It SHOULD be gzipped
    assert response.status_code == 200
    assert response.headers.get("Content-Encoding") == "gzip"
