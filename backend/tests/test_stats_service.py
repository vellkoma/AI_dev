"""StatsServiceの単体テスト。

リクエスト記録、累積統計、モデル別統計、時系列統計の正当性を検証する。
"""

import json
import time
from pathlib import Path

import pytest

from backend.app.schemas.stats import (
    CumulativeStats,
    ModelStats,
    RequestRecord,
    TimelineBucket,
)
from backend.app.services.stats_service import StatsService


@pytest.fixture
def stats_file(tmp_path):
    """テスト用の一時統計ファイルパスを提供する。"""
    return tmp_path / "stats.json"


@pytest.fixture
def service(stats_file):
    """テスト用のStatsServiceインスタンスを提供する。"""
    return StatsService(storage_path=stats_file)


@pytest.fixture
def sample_records():
    """テスト用のサンプルリクエスト記録リストを返す。"""
    return [
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


class TestRecordRequest:
    """record_request() のテスト。"""

    def test_record_appends_to_list(self, service):
        """リクエスト記録がインメモリリストに追加される。"""
        record = RequestRecord(
            timestamp=time.time(),
            model_name="gpt-4",
            prompt_tokens=100,
            completion_tokens=50,
            response_time=1.0,
        )
        service.record_request(record)

        stats = service.get_cumulative_stats()
        assert stats.total_requests == 1

    def test_record_persists_to_file(self, service, stats_file):
        """記録がJSONファイルに永続化される。"""
        record = RequestRecord(
            timestamp=time.time(),
            model_name="gpt-4",
            prompt_tokens=100,
            completion_tokens=50,
            response_time=1.0,
        )
        service.record_request(record)

        assert stats_file.exists()
        with open(stats_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["model_name"] == "gpt-4"

    def test_multiple_records(self, service):
        """複数の記録が正しく追加される。"""
        for i in range(5):
            record = RequestRecord(
                timestamp=time.time(),
                model_name=f"model-{i}",
                prompt_tokens=10 * (i + 1),
                completion_tokens=5 * (i + 1),
                response_time=0.1 * (i + 1),
            )
            service.record_request(record)

        stats = service.get_cumulative_stats()
        assert stats.total_requests == 5


class TestLoadRecords:
    """初期化時のファイル読み込みテスト。"""

    def test_load_existing_records(self, stats_file):
        """既存JSONファイルから記録を読み込む。"""
        records = [
            {
                "timestamp": 1704067200.0,
                "model_name": "gpt-4",
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "response_time": 1.5,
            }
        ]
        stats_file.parent.mkdir(parents=True, exist_ok=True)
        with open(stats_file, "w", encoding="utf-8") as f:
            json.dump(records, f)

        service = StatsService(storage_path=stats_file)
        stats = service.get_cumulative_stats()
        assert stats.total_requests == 1
        assert stats.total_tokens == 150

    def test_load_nonexistent_file(self, tmp_path):
        """ファイルが存在しない場合は空リストで開始する。"""
        service = StatsService(storage_path=tmp_path / "nonexistent.json")
        stats = service.get_cumulative_stats()
        assert stats.total_requests == 0

    def test_load_corrupted_file(self, stats_file):
        """破損ファイルの場合は空リストで開始する。"""
        stats_file.parent.mkdir(parents=True, exist_ok=True)
        with open(stats_file, "w") as f:
            f.write("invalid json content {{{")

        service = StatsService(storage_path=stats_file)
        stats = service.get_cumulative_stats()
        assert stats.total_requests == 0


class TestGetCumulativeStats:
    """get_cumulative_stats() のテスト。"""

    def test_empty_stats(self, service):
        """記録なしの場合は全てゼロの統計を返す。"""
        stats = service.get_cumulative_stats()

        assert stats.total_requests == 0
        assert stats.total_tokens == 0
        assert stats.average_response_time == 0.0
        assert stats.estimated_cost == 0.0

    def test_cumulative_calculation(self, service, sample_records):
        """累積統計が正しく計算される。"""
        for record in sample_records:
            service.record_request(record)

        stats = service.get_cumulative_stats()

        assert stats.total_requests == 3
        # トークン合計: (100+50) + (80+40) + (120+60) = 450
        assert stats.total_tokens == 450
        # 平均応答時間: (1.5 + 0.8 + 2.0) / 3 ≈ 1.4333
        assert abs(stats.average_response_time - (4.3 / 3)) < 0.001
        # 推定コスト: 450 / 1000 * 0.002 = 0.0009
        assert abs(stats.estimated_cost - 0.0009) < 0.0001

    def test_returns_cumulative_stats_type(self, service, sample_records):
        """CumulativeStats型が返される。"""
        for record in sample_records:
            service.record_request(record)

        stats = service.get_cumulative_stats()
        assert isinstance(stats, CumulativeStats)


class TestGetStatsByModel:
    """get_stats_by_model() のテスト。"""

    def test_empty_returns_empty_list(self, service):
        """記録なしの場合は空リストを返す。"""
        result = service.get_stats_by_model()
        assert result == []

    def test_model_grouping(self, service, sample_records):
        """モデルごとに正しくグループ化される。"""
        for record in sample_records:
            service.record_request(record)

        result = service.get_stats_by_model()

        # 2つのモデルがある
        assert len(result) == 2

        # モデル名でソートして検証
        result_by_name = {m.model_name: m for m in result}

        gpt4 = result_by_name["gpt-4"]
        assert gpt4.request_count == 2
        # gpt-4のトークン: (100+50) + (120+60) = 330
        assert gpt4.token_count == 330
        # gpt-4の平均応答時間: (1.5 + 2.0) / 2 = 1.75
        assert abs(gpt4.average_response_time - 1.75) < 0.001

        gpt35 = result_by_name["gpt-3.5-turbo"]
        assert gpt35.request_count == 1
        # gpt-3.5-turboのトークン: 80+40 = 120
        assert gpt35.token_count == 120
        assert abs(gpt35.average_response_time - 0.8) < 0.001

    def test_returns_model_stats_type(self, service, sample_records):
        """ModelStats型のリストが返される。"""
        for record in sample_records:
            service.record_request(record)

        result = service.get_stats_by_model()
        for item in result:
            assert isinstance(item, ModelStats)


class TestGetTimelineStats:
    """get_timeline_stats() のテスト。"""

    def test_empty_returns_empty_list(self, service):
        """記録なしの場合は空リストを返す。"""
        result = service.get_timeline_stats("daily")
        assert result == []

    def test_daily_aggregation(self, service, sample_records):
        """日別集計が正しく行われる。"""
        for record in sample_records:
            service.record_request(record)

        result = service.get_timeline_stats("daily")

        assert len(result) == 3
        # 日付順にソートされている
        assert result[0].period == "2024-01-01"
        assert result[1].period == "2024-01-02"
        assert result[2].period == "2024-01-03"

        # 各バケットのリクエスト数
        assert result[0].request_count == 1
        assert result[1].request_count == 1
        assert result[2].request_count == 1

        # 各バケットのトークン数
        assert result[0].token_count == 150  # 100+50
        assert result[1].token_count == 120  # 80+40
        assert result[2].token_count == 180  # 120+60

    def test_weekly_aggregation(self, service, sample_records):
        """週別集計が正しく行われる。"""
        for record in sample_records:
            service.record_request(record)

        result = service.get_timeline_stats("weekly")

        # 2024-01-01〜03は同じ週（W01）
        assert len(result) == 1
        assert result[0].period == "2024-W01"
        assert result[0].request_count == 3
        assert result[0].token_count == 450

    def test_monthly_aggregation(self, service, sample_records):
        """月別集計が正しく行われる。"""
        for record in sample_records:
            service.record_request(record)

        result = service.get_timeline_stats("monthly")

        # すべて同じ月
        assert len(result) == 1
        assert result[0].period == "2024-01"
        assert result[0].request_count == 3
        assert result[0].token_count == 450

    def test_multiple_months(self, service):
        """複数月にまたがるデータの集計。"""
        records = [
            RequestRecord(
                timestamp=1704067200.0,  # 2024-01-01
                model_name="gpt-4",
                prompt_tokens=100,
                completion_tokens=50,
                response_time=1.0,
            ),
            RequestRecord(
                timestamp=1706745600.0,  # 2024-02-01
                model_name="gpt-4",
                prompt_tokens=200,
                completion_tokens=100,
                response_time=1.5,
            ),
        ]
        for record in records:
            service.record_request(record)

        result = service.get_timeline_stats("monthly")

        assert len(result) == 2
        assert result[0].period == "2024-01"
        assert result[0].token_count == 150
        assert result[1].period == "2024-02"
        assert result[1].token_count == 300

    def test_invalid_period_raises_error(self, service):
        """無効なperiodでValueErrorが発生する。"""
        with pytest.raises(ValueError, match="Invalid period"):
            service.get_timeline_stats("yearly")

    def test_returns_timeline_bucket_type(self, service, sample_records):
        """TimelineBucket型のリストが返される。"""
        for record in sample_records:
            service.record_request(record)

        result = service.get_timeline_stats("daily")
        for item in result:
            assert isinstance(item, TimelineBucket)

    def test_timeline_sorted_ascending(self, service):
        """結果が期間昇順でソートされている。"""
        # 逆順で記録を追加
        records = [
            RequestRecord(
                timestamp=1704240000.0,  # 2024-01-03
                model_name="gpt-4",
                prompt_tokens=100,
                completion_tokens=50,
                response_time=1.0,
            ),
            RequestRecord(
                timestamp=1704067200.0,  # 2024-01-01
                model_name="gpt-4",
                prompt_tokens=100,
                completion_tokens=50,
                response_time=1.0,
            ),
        ]
        for record in records:
            service.record_request(record)

        result = service.get_timeline_stats("daily")
        assert result[0].period == "2024-01-01"
        assert result[1].period == "2024-01-03"
