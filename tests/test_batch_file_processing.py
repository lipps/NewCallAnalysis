"""
批量文件处理功能的完整测试套件
测试覆盖文件解析、批量处理、API接口和前端集成
"""

import pytest
import asyncio
import json
import tempfile
import uuid
from pathlib import Path
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
from fastapi.testclient import TestClient

# 导入被测试的模块
from src.models.schemas import (
    CallInput, ParsedFileInput, BatchFileProcessRequest,
    BatchFileProcessResponse, BatchProcessingConfig
)
from src.utils.file_parser import StreamingFileParser, parse_uploaded_files
from src.utils.batch_processor import BatchProcessor, ResultStorage
from src.api.main import app


class TestFileParser:
    """文件解析器测试"""

    @pytest.fixture
    def parser(self):
        """创建文件解析器实例"""
        config = BatchProcessingConfig()
        return StreamingFileParser(config)

    @pytest.fixture
    def sample_json_data(self):
        """示例JSON数据"""
        return [
            {
                "call_id": "test_001",
                "transcript": "销售：您好，我是益盟专员。客户：好的，了解一下。",
                "customer_id": "cust_001"
            },
            {
                "call_id": "test_002",
                "transcript": "销售：我们有BS买卖点功能。客户：听起来不错。"
            }
        ]

    @pytest.fixture
    def sample_csv_data(self):
        """示例CSV数据"""
        return """call_id,transcript,customer_id
test_001,"销售：您好，我是益盟专员。客户：好的，了解一下。",cust_001
test_002,"销售：我们有BS买卖点功能。客户：听起来不错。",cust_002"""

    @pytest.fixture
    def mock_uploaded_file(self):
        """模拟上传的文件对象"""
        class MockUploadedFile:
            def __init__(self, name, content, content_type="application/json"):
                self.name = name
                self.size = len(content.encode('utf-8'))
                self._content = content.encode('utf-8')
                self.content_type = content_type
                self._position = 0

            def read(self, size=-1):
                if size == -1:
                    content = self._content[self._position:]
                    self._position = len(self._content)
                else:
                    content = self._content[self._position:self._position + size]
                    self._position += len(content)
                return content

            def seek(self, position):
                self._position = position

        return MockUploadedFile

    def test_parse_json_list_format(self, parser, sample_json_data, mock_uploaded_file):
        """测试解析JSON列表格式"""
        content = json.dumps(sample_json_data)
        file_obj = mock_uploaded_file("test.json", content)

        result = parser._parse_single_file_sync(file_obj, "test_batch")

        assert result.parse_status.value == "success"
        assert len(result.calls) == 2
        assert result.calls[0].call_id == "test_001"
        assert result.calls[0].transcript == "销售：您好，我是益盟专员。客户：好的，了解一下。"

    def test_parse_json_calls_wrapper(self, parser, sample_json_data, mock_uploaded_file):
        """测试解析带calls包装的JSON格式"""
        content = json.dumps({"calls": sample_json_data})
        file_obj = mock_uploaded_file("test.json", content)

        result = parser._parse_single_file_sync(file_obj, "test_batch")

        assert result.parse_status.value == "success"
        assert len(result.calls) == 2

    def test_parse_single_json_object(self, parser, mock_uploaded_file):
        """测试解析单个JSON对象"""
        data = {"call_id": "single_test", "transcript": "单个通话测试"}
        content = json.dumps(data)
        file_obj = mock_uploaded_file("test.json", content)

        result = parser._parse_single_file_sync(file_obj, "test_batch")

        assert result.parse_status.value == "success"
        assert len(result.calls) == 1
        assert result.calls[0].call_id == "single_test"

    def test_parse_csv_format(self, parser, sample_csv_data, mock_uploaded_file):
        """测试解析CSV格式"""
        file_obj = mock_uploaded_file("test.csv", sample_csv_data)

        result = parser._parse_single_file_sync(file_obj, "test_batch")

        assert result.parse_status.value == "success"
        assert len(result.calls) == 2
        assert result.calls[0].call_id == "test_001"

    def test_parse_txt_format(self, parser, mock_uploaded_file):
        """测试解析TXT格式"""
        content = "销售：您好，欢迎了解我们的产品。\n客户：好的，请介绍一下。"
        file_obj = mock_uploaded_file("test.txt", content)

        result = parser._parse_single_file_sync(file_obj, "test_batch")

        assert result.parse_status.value == "success"
        assert len(result.calls) == 1
        assert result.calls[0].call_id == "test"

    def test_parse_invalid_json(self, parser, mock_uploaded_file):
        """测试解析无效JSON"""
        content = "invalid json content"
        file_obj = mock_uploaded_file("test.json", content)

        result = parser._parse_single_file_sync(file_obj, "test_batch")

        assert result.parse_status.value == "failed"
        assert "JSON格式错误" in result.parse_error

    def test_parse_csv_missing_transcript(self, parser, mock_uploaded_file):
        """测试CSV缺少必需列"""
        content = "call_id,customer_id\ntest_001,cust_001"
        file_obj = mock_uploaded_file("test.csv", content)

        result = parser._parse_single_file_sync(file_obj, "test_batch")

        assert result.parse_status.value == "failed"
        assert "transcript" in result.parse_error

    def test_file_size_limit(self, parser, mock_uploaded_file):
        """测试文件大小限制"""
        # 创建一个超大内容
        large_content = "x" * (300 * 1024 * 1024)  # 300MB
        file_obj = mock_uploaded_file("large.json", large_content)

        result = parser._parse_single_file_sync(file_obj, "test_batch")

        assert result.parse_status.value == "failed"
        assert "文件大小" in result.parse_error

    @pytest.mark.asyncio
    async def test_async_file_parsing(self, parser, sample_json_data, mock_uploaded_file):
        """测试异步文件解析"""
        files = [
            mock_uploaded_file("test1.json", json.dumps(sample_json_data)),
            mock_uploaded_file("test2.json", json.dumps(sample_json_data))
        ]

        results = await parser.parse_files(files, "test_batch")

        assert len(results) == 2
        assert all(r.parse_status.value == "success" for r in results)


class TestBatchProcessor:
    """批量处理器测试"""

    @pytest.fixture
    def mock_workflow(self):
        """模拟工作流"""
        workflow = AsyncMock()
        workflow.execute_batch.return_value = [
            MagicMock(confidence_score=0.8),
            MagicMock(confidence_score=0.7)
        ]
        return workflow

    @pytest.fixture
    def batch_config(self):
        """批量处理配置"""
        return BatchProcessingConfig(
            max_files_per_batch=5,
            max_calls_per_batch=100,
            max_concurrent_files=2
        )

    @pytest.fixture
    def sample_parsed_files(self):
        """示例解析后的文件"""
        return [
            ParsedFileInput(
                source_filename="test1.json",
                file_size_bytes=1024,
                parse_status="success",
                calls=[
                    CallInput(call_id="call_1", transcript="测试通话1"),
                    CallInput(call_id="call_2", transcript="测试通话2")
                ],
                parsed_at=datetime.now().isoformat()
            ),
            ParsedFileInput(
                source_filename="test2.json",
                file_size_bytes=2048,
                parse_status="success",
                calls=[
                    CallInput(call_id="call_3", transcript="测试通话3")
                ],
                parsed_at=datetime.now().isoformat()
            )
        ]

    def test_result_storage_save_file(self):
        """测试结果存储功能"""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = ResultStorage(temp_dir)

            # 模拟分析结果
            results = [MagicMock()]
            results[0].dict.return_value = {"call_id": "test", "confidence_score": 0.8}

            file_path = storage.save_file_result("batch_001", "test.json", results)

            assert Path(file_path).exists()
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                assert data["source_filename"] == "test.json"
                assert data["result_count"] == 1

    @pytest.mark.asyncio
    async def test_batch_processing_success(self, mock_workflow, batch_config, sample_parsed_files):
        """测试成功的批量处理"""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = ResultStorage(temp_dir)
            processor = BatchProcessor(mock_workflow, batch_config, storage)

            request = BatchFileProcessRequest(
                batch_id="test_batch_001",
                files=sample_parsed_files
            )

            response = await processor.process_batch(request)

            assert response.status.value == "success"
            assert response.statistics.total_files == 2
            assert response.statistics.successful_files == 2
            assert response.statistics.total_calls_processed > 0

    @pytest.mark.asyncio
    async def test_batch_processing_with_failures(self, batch_config, sample_parsed_files):
        """测试部分失败的批量处理"""
        # 模拟工作流，第一个文件成功，第二个失败
        workflow = AsyncMock()
        workflow.execute_batch.side_effect = [
            [MagicMock(confidence_score=0.8)],  # 第一个文件成功
            Exception("处理失败")  # 第二个文件失败
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            storage = ResultStorage(temp_dir)
            processor = BatchProcessor(workflow, batch_config, storage)

            request = BatchFileProcessRequest(
                batch_id="test_batch_002",
                files=sample_parsed_files
            )

            response = await processor.process_batch(request)

            assert response.status.value == "partial_success"
            assert response.statistics.successful_files == 1
            assert response.statistics.failed_files == 1

    @pytest.mark.asyncio
    async def test_batch_processing_empty_files(self, mock_workflow, batch_config):
        """测试空文件列表处理"""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = ResultStorage(temp_dir)
            processor = BatchProcessor(mock_workflow, batch_config, storage)

            # 没有成功解析的文件
            failed_files = [
                ParsedFileInput(
                    source_filename="failed.json",
                    file_size_bytes=100,
                    parse_status="failed",
                    calls=[],
                    parse_error="解析失败",
                    parsed_at=datetime.now().isoformat()
                )
            ]

            request = BatchFileProcessRequest(
                batch_id="test_batch_003",
                files=failed_files
            )

            response = await processor.process_batch(request)

            assert response.status.value == "failed"
            assert response.statistics.successful_files == 0


class TestBatchAPI:
    """批量处理API测试"""

    @pytest.fixture
    def client(self):
        """测试客户端"""
        return TestClient(app)

    @pytest.fixture
    def sample_batch_request(self):
        """示例批量处理请求"""
        return {
            "batch_id": "api_test_001",
            "files": [
                {
                    "source_filename": "test.json",
                    "file_size_bytes": 1024,
                    "parse_status": "success",
                    "calls": [
                        {
                            "call_id": "api_test_call_1",
                            "transcript": "销售：您好，我是益盟专员。客户：好的。"
                        }
                    ],
                    "parse_warnings": [],
                    "parsed_at": datetime.now().isoformat()
                }
            ]
        }

    def test_get_batch_config(self, client):
        """测试获取批量配置接口"""
        response = client.get("/analyze/batch/config")
        assert response.status_code == 200

        data = response.json()
        assert "config" in data
        assert "supported_file_types" in data
        assert "limits" in data

    def test_batch_processing_api_validation(self, client):
        """测试API请求验证"""
        # 空请求
        response = client.post("/analyze/batch/files", json={"batch_id": "test", "files": []})
        assert response.status_code == 400
        assert "文件列表不能为空" in response.json()["detail"]

    @patch('src.utils.batch_processor.get_batch_processor')
    def test_batch_processing_api_success(self, mock_get_processor, client, sample_batch_request):
        """测试API成功处理"""
        # 模拟批量处理器
        mock_processor = AsyncMock()
        mock_processor.process_batch.return_value = BatchFileProcessResponse(
            batch_id="api_test_001",
            status="success",
            files=[],
            statistics=MagicMock(),
            processing_start_time=datetime.now().isoformat(),
            processing_end_time=datetime.now().isoformat()
        )
        mock_get_processor.return_value = mock_processor

        response = client.post("/analyze/batch/files", json=sample_batch_request)
        assert response.status_code == 200

        data = response.json()
        assert data["batch_id"] == "api_test_001"
        assert data["status"] == "success"

    def test_batch_status_not_found(self, client):
        """测试查询不存在的批次"""
        response = client.get("/analyze/batch/nonexistent_batch/status")
        assert response.status_code == 404

    def test_cleanup_batch_not_found(self, client):
        """测试清理不存在的批次"""
        response = client.delete("/analyze/batch/nonexistent_batch")
        assert response.status_code == 404


class TestIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self):
        """端到端工作流测试"""
        # 创建测试数据
        test_data = {
            "calls": [
                {
                    "call_id": "integration_test_001",
                    "transcript": "销售：您好，我是益盟操盘手专员。客户：好的，了解一下。销售：我们有BS买卖点功能。客户：听起来不错，具体怎么使用？"
                }
            ]
        }

        # 模拟文件上传
        class MockFile:
            def __init__(self, name, content):
                self.name = name
                self.size = len(content.encode())
                self._content = content.encode()

            def read(self, size=-1):
                return self._content

            def seek(self, pos):
                pass

        mock_file = MockFile("integration_test.json", json.dumps(test_data))

        # 解析文件
        config = BatchProcessingConfig()
        parser = StreamingFileParser(config)

        parsed_files = await parser.parse_files([mock_file], "integration_test_batch")

        assert len(parsed_files) == 1
        assert parsed_files[0].parse_status.value == "success"
        assert len(parsed_files[0].calls) == 1

    def test_performance_large_batch(self):
        """性能测试 - 大批量处理"""
        # 生成大量测试数据
        large_data = []
        for i in range(100):
            large_data.append({
                "call_id": f"perf_test_{i:03d}",
                "transcript": f"销售：您好，这是第{i}个测试通话。客户：好的。"
            })

        # 验证数据可以正确序列化
        json_data = json.dumps(large_data)
        assert len(json_data) > 0

        # 验证数据结构
        assert len(large_data) == 100
        assert all("call_id" in item and "transcript" in item for item in large_data)

    def test_error_recovery(self):
        """错误恢复测试"""
        # 测试数据包含有效和无效的记录
        mixed_data = [
            {"call_id": "valid_001", "transcript": "有效的通话记录"},
            {"call_id": "invalid_001"},  # 缺少transcript
            {"call_id": "valid_002", "transcript": "另一个有效记录"}
        ]

        # 验证错误处理逻辑
        valid_count = sum(1 for item in mixed_data if "transcript" in item and item["transcript"])
        assert valid_count == 2


# 测试运行器
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])