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


class DelayPredictionConfigurationError(AirlineOperationsError):
    """Raised when flight-delay prediction configuration is invalid."""


class DelayPredictionSourceError(AirlineOperationsError):
    """Raised when delay prediction input sources cannot be used."""


class DelayPredictionIntegrityError(DelayPredictionSourceError):
    """Raised when delay prediction input manifests or checksums do not verify."""


class DelayFeatureEngineeringError(AirlineOperationsError):
    """Raised when delay prediction features cannot be built safely."""


class DelayLeakageDetectedError(DelayFeatureEngineeringError):
    """Raised when delay prediction features leak target or future information."""


class DelayInsufficientDataError(AirlineOperationsError):
    """Raised when delay prediction partitions do not contain enough rows."""


class DelayClassDistributionError(DelayInsufficientDataError):
    """Raised when delay prediction target classes are not trainable."""


class DelayTrainingError(AirlineOperationsError):
    """Raised when a delay prediction model cannot be trained."""


class DelayEvaluationError(AirlineOperationsError):
    """Raised when delay prediction evaluation cannot run."""


class DelayThresholdSelectionError(AirlineOperationsError):
    """Raised when a delay prediction threshold cannot be selected."""


class DelayModelSelectionError(AirlineOperationsError):
    """Raised when a delay prediction champion cannot be selected."""


class DelayOutputCollisionError(AirlineOperationsError):
    """Raised when delay prediction output directories already exist."""


class DelayArtefactError(AirlineOperationsError):
    """Raised when delay prediction artefacts cannot be written or verified."""


class MaintenanceAnalyticsConfigurationError(AirlineOperationsError):
    """Raised when maintenance analytics configuration is invalid."""


class MaintenanceAnalyticsSourceError(AirlineOperationsError):
    """Raised when maintenance analytics sources cannot be used."""


class MaintenanceAnalyticsIntegrityError(MaintenanceAnalyticsSourceError):
    """Raised when maintenance analytics source integrity checks fail."""


class MaintenanceFeatureEngineeringError(AirlineOperationsError):
    """Raised when maintenance features cannot be created."""


class MaintenanceScoringError(AirlineOperationsError):
    """Raised when maintenance scoring cannot be completed."""


class MaintenanceAlertError(AirlineOperationsError):
    """Raised when maintenance alerts cannot be generated."""


class MaintenanceOutputCollisionError(AirlineOperationsError):
    """Raised when maintenance output directories already exist."""


class MaintenanceArtefactError(AirlineOperationsError):
    """Raised when maintenance artefacts cannot be written or read."""


class DisruptionScoringConfigurationError(AirlineOperationsError):
    """Raised when disruption scoring configuration is invalid."""


class DisruptionScoringSourceError(AirlineOperationsError):
    """Raised when disruption scoring sources cannot be used."""


class DisruptionScoringIntegrityError(DisruptionScoringSourceError):
    """Raised when disruption source manifests or checksums do not verify."""


class DisruptionFeatureEngineeringError(AirlineOperationsError):
    """Raised when disruption features cannot be built safely."""


class DisruptionLeakageDetectedError(DisruptionFeatureEngineeringError):
    """Raised when forward disruption risk would use prohibited outcome fields."""


class DisruptionScoringError(AirlineOperationsError):
    """Raised when disruption scoring cannot complete."""


class DisruptionAlertError(AirlineOperationsError):
    """Raised when disruption alerts cannot be generated."""


class DisruptionOutputCollisionError(AirlineOperationsError):
    """Raised when disruption output directories already exist."""


class DisruptionArtefactError(AirlineOperationsError):
    """Raised when disruption artefacts cannot be written or read."""


class MonitoringConfigurationError(AirlineOperationsError):
    """Raised when monitoring configuration is invalid."""


class MonitoringSourceError(AirlineOperationsError):
    """Raised when monitoring input sources cannot be used."""


class MonitoringIntegrityError(MonitoringSourceError):
    """Raised when monitoring source integrity checks fail."""


class MonitoringCompatibilityError(MonitoringSourceError):
    """Raised when monitoring inputs do not share expected lineage."""


class MonitoringCheckError(AirlineOperationsError):
    """Raised when monitoring checks cannot be evaluated."""


class MonitoringDriftError(AirlineOperationsError):
    """Raised when drift-style comparison cannot be evaluated."""


class MonitoringAlertError(AirlineOperationsError):
    """Raised when monitoring alerts cannot be generated."""


class MonitoringOutputCollisionError(AirlineOperationsError):
    """Raised when monitoring output directories already exist."""


class MonitoringArtefactError(AirlineOperationsError):
    """Raised when monitoring artefacts cannot be written or read."""


class GenAIAssistantConfigurationError(AirlineOperationsError):
    """Raised when GenAI assistant configuration is invalid."""


class GenAIAssistantSourceError(AirlineOperationsError):
    """Raised when GenAI assistant input sources cannot be used."""


class GenAIAssistantIntegrityError(GenAIAssistantSourceError):
    """Raised when GenAI assistant source integrity checks fail."""


class GenAIAssistantCompatibilityError(GenAIAssistantSourceError):
    """Raised when GenAI assistant inputs do not share expected lineage."""


class GenAIEvidenceError(AirlineOperationsError):
    """Raised when structured assistant evidence cannot be extracted."""


class GenAIRetrievalError(AirlineOperationsError):
    """Raised when assistant retrieval cannot be completed."""


class GenAIPromptError(AirlineOperationsError):
    """Raised when prompt assembly cannot be completed."""


class GenAIGuardrailError(AirlineOperationsError):
    """Raised when assistant guardrails fail."""


class GenAIResponseError(AirlineOperationsError):
    """Raised when deterministic assistant response generation fails."""


class GenAIOutputCollisionError(AirlineOperationsError):
    """Raised when assistant output directories already exist."""


class GenAIArtefactError(AirlineOperationsError):
    """Raised when assistant artefacts cannot be written or read."""
