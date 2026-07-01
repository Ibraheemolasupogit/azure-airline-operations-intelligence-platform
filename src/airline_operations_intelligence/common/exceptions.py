"""Custom exception hierarchy for the platform foundation."""


class AirlineOperationsError(Exception):
    """Base exception for package-specific errors."""


class ConfigurationError(AirlineOperationsError):
    """Raised when platform configuration is missing or invalid."""


class RepositoryValidationError(AirlineOperationsError):
    """Raised when repository foundation validation fails."""


class GenerationConfigurationError(AirlineOperationsError):
    """Raised when synthetic data-generation configuration is invalid."""


class GenerationError(AirlineOperationsError):
    """Raised when synthetic data generation fails."""


class GenerationInvariantError(GenerationError):
    """Raised when generation-time invariants fail."""


class OutputCollisionError(GenerationError):
    """Raised when a generation run would overwrite an existing output."""


class IngestionError(AirlineOperationsError):
    """Raised when governed data ingestion fails."""


class SourceDiscoveryError(IngestionError):
    """Raised when a source generation run cannot be discovered safely."""


class SourceIntegrityError(IngestionError):
    """Raised when source files fail manifest or checksum verification."""


class UnsupportedManifestVersionError(SourceIntegrityError):
    """Raised when a source manifest schema version is unsupported."""


class ValidationConfigurationError(AirlineOperationsError):
    """Raised when validation configuration is invalid."""


class ValidationRuleError(AirlineOperationsError):
    """Raised when a validation rule cannot execute."""


class ValidationThresholdError(AirlineOperationsError):
    """Raised when validation findings exceed configured thresholds."""


class ValidationOutputCollisionError(AirlineOperationsError):
    """Raised when validation output directories already exist."""
