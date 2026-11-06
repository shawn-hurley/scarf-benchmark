"""ScarfBench-owned validation API; no agent harness dependencies."""
from .contracts import grade_contracts, prepare_source_contract, copy_conversion, validation_policy, validate_source_pair
from .profiles import prepare_profile, _target_http_port
API_VERSION = 1
from .guidance import migration_guidance
