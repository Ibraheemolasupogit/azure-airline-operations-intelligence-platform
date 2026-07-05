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


class ForecastingConfigurationError(AirlineOperationsError):
    """Raised when passenger forecasting configuration is invalid."""


class ForecastingSourceError(AirlineOperationsError):
    """Raised when a validation source cannot be used for forecasting."""


class ForecastingIntegrityError(ForecastingSourceError):
    """Raised when forecasting input checksums or manifests do not verify."""


class FeatureEngineeringError(AirlineOperationsError):
    """Raised when forecasting features cannot be constructed safely."""


class LeakageDetectedError(FeatureEngineeringError):
    """Raised when a feature would leak target or future information."""


class InsufficientTrainingDataError(AirlineOperationsError):
    """Raised when chronological partitions cannot support training."""


class ForecastTrainingError(AirlineOperationsError):
    """Raised when a forecasting model cannot be trained."""


class ForecastEvaluationError(AirlineOperationsError):
    """Raised when forecast evaluation fails."""


class ModelSelectionError(AirlineOperationsError):
    """Raised when a champion model cannot be selected."""


class ForecastOutputCollisionError(AirlineOperationsError):
    """Raised when forecasting output directories already exist."""


class ForecastArtefactError(AirlineOperationsError):
    """Raised when forecast artefacts cannot be written or verified."""
