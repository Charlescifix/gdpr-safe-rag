"""Compliance check example.

This example demonstrates:
- Running compliance checks
- Generating compliance reports
- Interpreting check results
"""

import asyncio
from datetime import datetime, timedelta

from gdpr_safe_rag.audit_logger import AuditLogger
from gdpr_safe_rag.audit_logger.backends.memory_backend import MemoryBackend
from gdpr_safe_rag.compliance_checker import ComplianceChecker


async def main() -> None:
    print("=" * 60)
    print("GDPR Safe RAG - Compliance Check Example")
    print("=" * 60)

    # Create sample documents with metadata
    documents = [
        {
            "id": "doc-001",
            "title": "Employee Handbook",
            "created_at": datetime.now() - timedelta(days=30),
            "pii_detected": True,
            "pii_count": 5,
            "pii_type_counts": {"email": 3, "phone": 2},
        },
        {
            "id": "doc-002",
            "title": "Company Policies",
            "created_at": datetime.now() - timedelta(days=60),
            "pii_detected": False,
            "pii_count": 0,
            "pii_type_counts": {},
        },
        {
            "id": "doc-003",
            "title": "HR Records Summary",
            "created_at": datetime.now() - timedelta(days=90),
            "pii_detected": True,
            "pii_count": 15,
            "pii_type_counts": {"email": 5, "phone": 5, "nhs_number": 5},
        },
        {
            "id": "doc-004",
            "title": "Meeting Notes",
            "created_at": datetime.now() - timedelta(days=10),
            "pii_detected": True,
            "pii_count": 2,
            "pii_type_counts": {"email": 2},
        },
    ]

    # Create audit logger with some sample events
    backend = MemoryBackend()
    async with AuditLogger(backend=backend) as logger:
        # Log some sample events
        await logger.log_ingestion("doc-001", "admin", True, 5)
        await logger.log_ingestion("doc-002", "admin", False, 0)
        await logger.log_query("user-001", "What is the policy?", ["doc-001"])
        await logger.log_deletion("user-002", "old-data", "retention_policy")
        await logger.log_access("user-001", "view", "doc-001", "work task")

        # Initialize compliance checker
        print("\n1. INITIALIZING COMPLIANCE CHECKER")
        print("-" * 40)
        checker = ComplianceChecker(retention_days=2555)
        print(f"Retention period: {checker._retention_days} days")
        print(f"Checks to run: {len(checker.checks)}")
        for check in checker.checks:
            print(f"  - {check.name}: {check.description}")

        # Run all checks
        print("\n2. RUNNING COMPLIANCE CHECKS")
        print("-" * 40)
        report = await checker.run_all_checks(
            documents=documents,
            audit_logger=logger,
        )

        # Display results
        print("\n3. COMPLIANCE REPORT")
        print("-" * 40)
        print(report.to_text(include_remediation=True))

        # Show detailed check results
        print("\n4. DETAILED CHECK RESULTS")
        print("-" * 40)
        for check_result in report.checks:
            print(f"\n{check_result.name.upper()}")
            print(f"  Status: {check_result.status.value}")
            print(f"  Message: {check_result.message}")
            if check_result.details:
                print("  Details:")
                for key, value in check_result.details.items():
                    print(f"    {key}: {value}")

        # Generate JSON report
        print("\n5. JSON REPORT EXPORT")
        print("-" * 40)
        json_report = await checker.generate_report(
            documents=documents,
            audit_logger=logger,
            format="json",
        )
        print(json_report[:500] + "..." if len(json_report) > 500 else json_report)

        # Demonstrate failure scenario
        print("\n6. FAILURE SCENARIO (Expired Documents)")
        print("-" * 40)

        # Add an expired document
        expired_documents = documents + [
            {
                "id": "doc-old",
                "title": "Ancient Document",
                "created_at": datetime.now() - timedelta(days=3000),  # ~8 years old
                "pii_detected": True,
                "pii_count": 10,
                "pii_type_counts": {"email": 10},
            }
        ]

        report_with_failure = await checker.run_all_checks(
            documents=expired_documents,
            audit_logger=logger,
        )

        print(f"Overall status: {'PASS' if report_with_failure.passed else 'FAIL'}")
        print(f"Failed checks: {report_with_failure.failed_checks}")

        for failure in report_with_failure.get_failures():
            print(f"\nFailure: {failure.name}")
            print(f"  {failure.message}")
            if failure.remediation:
                print(f"  Remediation: {failure.remediation}")

    print("\n" + "=" * 60)
    print("Example completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
