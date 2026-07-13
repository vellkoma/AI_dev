"""統計APIルーターの単体テスト。

GET /api/stats, GET /api/stats/by-model, GET /api/stats/timeline の正当性を検証する。
"""

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.dependencies import get_stats_service
from backend.app.routers.stats import router
from backend.app.schemas.stats import RequestRecord
from backend.app.services.stats_service import StatsService


def _create_test_app(service: StatsService) -> FastAPI:
    """テスト用のFastAPIアプリを作成する。"""
    test_app = FastAPI()
    test_app.include_router(router)
    test_app.dependency_overrides[get_stats_service] = lambda: service
    return test_app


@pytest.fixture
def stats_service(tmp_path):
    """テスト用のStatsServiceインスタンスを提供する。"""
    return StatsService(storage_path=tmp_path / "test_stats.json")


@pytest.fixture
def stats_service_with_data(stats_service):
    """サンプルデータ入りのStatsServiceインスタンスを提供する。"""
    records = [
        RequestRecord(
            timestamp=1704067200.0,  # 2024-01-01 00:00:00 UTC
            model_name="gpt-4",
            prompt_tokens=100,
            completion_tokens=50,
            response_time=1.5,
        ),
        RequestRecord(
            timestamp=1704153600.0,  # 2024-01-02 00:00:00 UTC
            model_name="gpt-3.5-turbo",
            prompt_tokens=80,
            completion_tokens=40,
            response_time=0.8,
        ),
        RequestRecord(
            timestamp=1704240000.0,  # 2024-01-03 00:00:00 UTC
            model_name="gpt-4",
            prompt_tokens=120,
            completion_tokens=60,
            response_time=2.0,
        ),
    ]
    for record in records:
        stats_service.record_request(record)
    return stats_service


@pytest.fixture
def client(stats_service_with_data):
    """テスト用のFastAPI TestClientを提供する。"""
    test_app = _create_test_app(stats_service_with_data)
    return TestClient(test_app)


@pytest.fixture
def empty_client(stats_service):
    """データなしのStatsServiceを使用するTestClientを提供する。"""
    test_app = _create_test_app(stats_service)
    return TestClient(test_app)


class TestGetStats:
    """GET /api/stats のテスト。"""

    def test_returns_cumulative_stats(self, client):
        """累積統計を正しく返す。"""
        response = client.get("/api/stats")

        assert response.status_code == 200
        data = response.json()
        assert "stats" in data
        stats = data["stats"]
        assert stats["total_requests"] == 3
        assert stats["total_tokens"] == 450
        assert stats["estimated_cost"] > 0

    def test_empty_stats(self, empty_client):
        """データなしの場合はゼロの統計を返す。"""
        response = empty_client.get("/api/stats")

        assert response.status_code == 200
        data = response.json()
        stats = data["stats"]
        assert stats["total_requests"] == 0
        assert stats["total_tokens"] == 0
        assert stats["average_response_time"] == 0.0
        assert stats["estimated_cost"] == 0.0


class TestGetStatsByModel:
    """GET /api/stats/by-model のテスト。"""

    def test_returns_model_stats(self, client):
        """モデル別統計を正しく返す。"""
        response = client.get("/api/stats/by-model")

        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        models = data["models"]
        assert len(models) == 2

        # モデル名でソートして検証
        models_by_name = {m["model_name"]: m for m in models}
        assert "gpt-4" in models_by_name
        assert "gpt-3.5-turbo" in models_by_name
        assert models_by_name["gpt-4"]["request_count"] == 2
        assert models_by_name["gpt-3.5-turbo"]["request_count"] == 1

    def test_empty_returns_empty_list(self, empty_client):
        """データなしの場合は空リストを返す。"""
        response = empty_client.get("/api/stats/by-model")

        assert response.status_code == 200
        data = response.json()
        assert data["models"] == []


class TestGetStatsTimeline:
    """GET /api/stats/timeline のテスト。"""

    def test_default_period_is_daily(self, client):
        """デフォルトのperiodはdailyである。"""
        response = client.get("/api/stats/timeline")

        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "daily"
        assert len(data["timeline"]) == 3

    def test_daily_period(self, client):
        """period=dailyで日別統計を返す。"""
        response = client.get("/api/stats/timeline?period=daily")

        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "daily"
        timeline = data["timeline"]
        assert len(timeline) == 3
        assert timeline[0]["period"] == "2024-01-01"
        assert timeline[1]["period"] == "2024-01-02"
        assert timeline[2]["period"] == "2024-01-03"

    def test_weekly_period(self, client):
        """period=weeklyで週別統計を返す。"""
        response = client.get("/api/stats/timeline?period=weekly")

        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "weekly"
        timeline = data["timeline"]
        assert len(timeline) == 1
        assert timeline[0]["period"] == "2024-W01"
        assert timeline[0]["request_count"] == 3

    def test_monthly_period(self, client):
        """period=monthlyで月別統計を返す。"""
        response = client.get("/api/stats/timeline?period=monthly")

        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "monthly"
        timeline = data["timeline"]
        assert len(timeline) == 1
        assert timeline[0]["period"] == "2024-01"
        assert timeline[0]["request_count"] == 3

    def test_invalid_period_returns_400(self, client):
        """無効なperiodでHTTP 400を返す。"""
        response = client.get("/api/stats/timeline?period=yearly")

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    def test_empty_timeline(self, empty_client):
        """データなしの場合は空のtimelineを返す。"""
        response = empty_client.get("/api/stats/timeline")

        assert response.status_code == 200
        data = response.json()
        assert data["timeline"] == []
        assert data["period"] == "daily"
