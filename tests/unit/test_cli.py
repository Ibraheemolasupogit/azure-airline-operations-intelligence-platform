from pathlib import Path

from airline_operations_intelligence.cli import main, validate_repository
from airline_operations_intelligence.common.exceptions import RepositoryValidationError


def test_package_imports() -> None:
    import airline_operations_intelligence

    assert airline_operations_intelligence.__version__ == "0.1.0"


def test_repository_validation_passes_for_current_repository() -> None:
    assert validate_repository(Path(".")) == ["Repository foundation validation passed."]


def test_repository_validation_reports_missing_required_directories(tmp_path: Path) -> None:
    try:
        validate_repository(tmp_path)
    except RepositoryValidationError as exc:
        message = str(exc)
    else:
        raise AssertionError("Expected repository validation to fail.")

    assert "Missing required directory" in message
    assert "Missing required file" in message


def test_cli_validate_repository_success() -> None:
    assert main(["validate-repository"]) == 0
