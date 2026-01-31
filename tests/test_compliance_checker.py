"""Tests for Compliance Checker module."""

from datetime import datetime, timedelta

import pytest

from gdpr_safe_rag.audit_logger import AuditLogger
from gdpr_safe_rag.audit_logger.backends.memory_backend import MemoryBackend
from gdpr_safe_rag.compliance_checker import ComplianceChecker, ComplianceReport
from gdpr_safe_rag.compliance_checker.checks import (
    CheckResult,
    CheckStatus,
    DataInventoryCheck,
    ErasureCheck,
    RetentionCheck,
)


class TestCheckResult:
    """Tests for CheckResult."""

    def test_passed_property(self) -> None:
        """Test passed property for different statuses."""
        assert CheckResult("test", CheckStatus.PASS, "msg").passed is True
        assert CheckResult("test", CheckStatus.WARNING, "msg").passed is True
        assert CheckResult("test", CheckStatus.FAIL, "msg").passed is False
        assert CheckResult("test", CheckStatus.ERROR, "msg").passed is False

    def test_to_dict(self) -> None:
        """Test converting to dictionary."""
        result = CheckResult(
            name="test_check",
            status=CheckStatus.PASS,
            message="Test passed",
            details={"count": 5},
            remediation="No action needed",
        )
        data = result.to_dict()

        assert data["name"] == "test_check"
        assert data["status"] == "pass"
        assert data["message"] == "Test passed"
        assert data["details"]["count"] == 5
        assert data["remediation"] == "No action needed"


class TestDataInventoryCheck:
    """Tests for DataInventoryCheck."""

    @pytest.mark.asyncio
    async def test_pass_with_documents(self, sample_documents: list[dict]) -> None:
        """Test passing check with documents."""
        check = DataInventoryCheck()
        result = await check.run({"documents": sample_documents})

        assert result.status == CheckStatus.PASS
        assert result.details["document_count"] == 3

    @pytest.mark.asyncio
    async def test_pass_empty_documents(self) -> None:
        """Test passing check with no documents and no minimum."""
        check = DataInventoryCheck(min_documents=0)
        result = await check.run({"documents": []})

        assert result.status == CheckStatus.PASS
        assert result.details["document_count"] == 0

    @pytest.mark.asyncio
    async def test_fail_below_minimum(self) -> None:
        """Test failing check when below minimum documents."""
        check = DataInventoryCheck(min_documents=10)
        result = await check.run({"documents": [{"id": "doc-1"}]})

        assert result.status == CheckStatus.FAIL
        assert "below minimum" in result.message.lower()

    @pytest.mark.asyncio
    async def test_warning_high_pii_rate(self) -> None:
        """Test warning when PII rate is high."""
        check = DataInventoryCheck(max_pii_rate=0.5)
        documents = [
            {"id": "doc-1", "pii_detected": True, "pii_count": 5, "pii_type_counts": {}},
            {"id": "doc-2", "pii_detected": True, "pii_count": 3, "pii_type_counts": {}},
        ]
        result = await check.run({"documents": documents})

        assert result.status == CheckStatus.WARNING
        assert "high pii" in result.message.lower()


class TestRetentionCheck:
    """Tests for RetentionCheck."""

    @pytest.mark.asyncio
    async def test_pass_all_within_retention(self, sample_documents: list[dict]) -> None:
        """Test passing when all documents within retention."""
        check = RetentionCheck(retention_days=2555)
        result = await check.run({"documents": sample_documents})

        assert result.status == CheckStatus.PASS

    @pytest.mark.asyncio
    async def test_fail_expired_documents(self) -> None:
        """Test failing when documents exceed retention."""
        check = RetentionCheck(retention_days=30)
        documents = [
            {"id": "doc-1", "created_at": datetime.now() - timedelta(days=60)},
        ]
        result = await check.run({"documents": documents})

        assert result.status == CheckStatus.FAIL
        assert result.details["expired_count"] == 1

    @pytest.mark.asyncio
    async def test_warning_expiring_soon(self) -> None:
        """Test warning when documents expiring soon."""
        check = RetentionCheck(retention_days=100)
        documents = [
            {
                "id": "doc-1",
                "created_at": datetime.now() - timedelta(days=85),  # 15 days left
            },
        ]
        result = await check.run({"documents": documents})

        assert result.status == CheckStatus.WARNING
        assert result.details["expiring_soon_count"] == 1

    @pytest.mark.asyncio
    async def test_pass_no_documents(self) -> None:
        """Test passing with no documents."""
        check = RetentionCheck()
        result = await check.run({"documents": []})

        assert result.status == CheckStatus.PASS

    @pytest.mark.asyncio
    async def test_handles_iso_date_strings(self) -> None:
        """Test handling ISO date strings."""
        check = RetentionCheck(retention_days=2555)
        documents = [
            {"id": "doc-1", "created_at": datetime.now().isoformat()},
        ]
        result = await check.run({"documents": documents})

        assert result.status == CheckStatus.PASS


class TestErasureCheck:
    """Tests for ErasureCheck."""

    @pytest.mark.asyncio
    async def test_skip_no_logger(self) -> None:
        """Test skipping when no audit logger provided."""
        check = ErasureCheck()
        result = await check.run({})

        assert result.status == CheckStatus.SKIPPED

    @pytest.mark.asyncio
    async def test_pass_no_deletions(self) -> None:
        """Test passing when no deletion events."""
        backend = MemoryBackend()
        async with AuditLogger(backend=backend) as logger:
            check = ErasureCheck()
            result = await check.run({"audit_logger": logger})

            assert result.status == CheckStatus.PASS
            assert result.details["deletion_count"] == 0

    @pytest.mark.asyncio
    async def test_pass_with_deletions(self) -> None:
        """Test passing with deletion events."""
        backend = MemoryBackend()
        async with AuditLogger(backend=backend) as logger:
            await logger.log_deletion("user-1", "data-1", "retention_policy")
            await logger.log_deletion("user-2", "data-2", "user_request")

            check = ErasureCheck()
            result = await check.run({"audit_logger": logger})

            assert result.status == CheckStatus.PASS
            assert result.details["total_deletions"] == 2

    @pytest.mark.asyncio
    async def test_warning_many_user_requests(self) -> None:
        """Test warning when many user deletion requests."""
        backend = MemoryBackend()
        async with AuditLogger(backend=backend) as logger:
            # Log many user-requested deletions
            for i in range(10):
                await logger.log_deletion(f"user-{i}", f"data-{i}", "user_request")

            check = ErasureCheck()
            result = await check.run({"audit_logger": logger})

            assert result.status == CheckStatus.WARNING
            assert "high volume" in result.message.lower()


class TestComplianceReport:
    """Tests for ComplianceReport."""

    def test_passed_all_pass(self) -> None:
        """Test passed property when all checks pass."""
        report = ComplianceReport()
        report.add_check(CheckResult("check1", CheckStatus.PASS, "OK"))
        report.add_check(CheckResult("check2", CheckStatus.WARNING, "Warn"))

        assert report.passed is True

    def test_passed_with_failure(self) -> None:
        """Test passed property when any check fails."""
        report = ComplianceReport()
        report.add_check(CheckResult("check1", CheckStatus.PASS, "OK"))
        report.add_check(CheckResult("check2", CheckStatus.FAIL, "Failed"))

        assert report.passed is False

    def test_counts(self) -> None:
        """Test count properties."""
        report = ComplianceReport()
        report.add_check(CheckResult("check1", CheckStatus.PASS, ""))
        report.add_check(CheckResult("check2", CheckStatus.PASS, ""))
        report.add_check(CheckResult("check3", CheckStatus.WARNING, ""))
        report.add_check(CheckResult("check4", CheckStatus.FAIL, ""))
        report.add_check(CheckResult("check5", CheckStatus.ERROR, ""))
        report.add_check(CheckResult("check6", CheckStatus.SKIPPED, ""))

        assert report.total_checks == 6
        assert report.passed_checks == 2
        assert report.warning_checks == 1
        assert report.failed_checks == 1
        assert report.error_checks == 1
        assert report.skipped_checks == 1

    def test_get_failures(self) -> None:
        """Test getting failed checks."""
        report = ComplianceReport()
        report.add_check(CheckResult("check1", CheckStatus.PASS, "OK"))
        report.add_check(CheckResult("check2", CheckStatus.FAIL, "Failed"))

        failures = report.get_failures()
        assert len(failures) == 1
        assert failures[0].name == "check2"

    def test_to_dict(self) -> None:
        """Test converting report to dictionary."""
        report = ComplianceReport()
        report.add_check(CheckResult("check1", CheckStatus.PASS, "OK"))

        data = report.to_dict()
        assert "generated_at" in data
        assert data["overall_status"] == "PASS"
        assert data["summary"]["total"] == 1

    def test_to_text(self) -> None:
        """Test converting report to text."""
        report = ComplianceReport()
        report.add_check(
            CheckResult("data_inventory", CheckStatus.PASS, "All good")
        )
        report.add_check(
            CheckResult(
                "retention",
                CheckStatus.FAIL,
                "Expired docs",
                remediation="Delete old docs",
            )
        )

        text = report.to_text(include_remediation=True)
        assert "GDPR COMPLIANCE REPORT" in text
        assert "[PASS]" in text
        assert "[FAIL]" in text
        assert "Delete old docs" in text


class TestComplianceChecker:
    """Tests for the main ComplianceChecker class."""

    @pytest.mark.asyncio
    async def test_run_all_checks(self, sample_documents: list[dict]) -> None:
        """Test running all compliance checks."""
        backend = MemoryBackend()
        async with AuditLogger(backend=backend) as logger:
            checker = ComplianceChecker(retention_days=2555)
            report = await checker.run_all_checks(
                documents=sample_documents,
                audit_logger=logger,
            )

            assert isinstance(report, ComplianceReport)
            assert report.total_checks == 3  # Default checks
            assert report.passed is True

    @pytest.mark.asyncio
    async def test_run_all_checks_no_documents(self) -> None:
        """Test running checks with no documents."""
        checker = ComplianceChecker()
        report = await checker.run_all_checks(documents=[])

        assert report.total_checks == 3

    @pytest.mark.asyncio
    async def test_generate_report_text(self, sample_documents: list[dict]) -> None:
        """Test generating text report."""
        checker = ComplianceChecker()
        report_text = await checker.generate_report(
            documents=sample_documents,
            format="text",
        )

        assert "GDPR COMPLIANCE REPORT" in report_text

    @pytest.mark.asyncio
    async def test_generate_report_json(self, sample_documents: list[dict]) -> None:
        """Test generating JSON report."""
        import json

        checker = ComplianceChecker()
        report_json = await checker.generate_report(
            documents=sample_documents,
            format="json",
        )

        data = json.loads(report_json)
        assert "overall_status" in data
        assert "checks" in data

    @pytest.mark.asyncio
    async def test_add_custom_check(self) -> None:
        """Test adding custom checks."""
        from gdpr_safe_rag.compliance_checker.checks.base import BaseCheck

        class CustomCheck(BaseCheck):
            name = "custom_check"
            description = "A custom check"

            async def run(self, context: dict) -> CheckResult:
                return CheckResult(
                    name=self.name,
                    status=CheckStatus.PASS,
                    message="Custom check passed",
                )

        checker = ComplianceChecker()
        checker.add_check(CustomCheck())

        assert len(checker.checks) == 4  # 3 default + 1 custom

        report = await checker.run_all_checks()
        assert report.total_checks == 4

    @pytest.mark.asyncio
    async def test_custom_checks_in_constructor(self) -> None:
        """Test providing custom checks in constructor."""
        from gdpr_safe_rag.compliance_checker.checks.base import BaseCheck

        class CustomCheck(BaseCheck):
            name = "custom"

            async def run(self, context: dict) -> CheckResult:
                return CheckResult(self.name, CheckStatus.PASS, "OK")

        checker = ComplianceChecker(custom_checks=[CustomCheck()])
        assert len(checker.checks) == 4

    @pytest.mark.asyncio
    async def test_check_error_handling(self) -> None:
        """Test handling of check errors."""
        from gdpr_safe_rag.compliance_checker.checks.base import BaseCheck

        class FailingCheck(BaseCheck):
            name = "failing"

            async def run(self, context: dict) -> CheckResult:
                raise RuntimeError("Check failed!")

        checker = ComplianceChecker(custom_checks=[FailingCheck()])
        report = await checker.run_all_checks()

        # Should have error result, not crash
        error_results = [
            c for c in report.checks if c.status == CheckStatus.ERROR
        ]
        assert len(error_results) == 1
        assert "failing" in error_results[0].name
