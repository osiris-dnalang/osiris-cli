from osiris_cli.node_beta_governance import NodeBetaGovernor
import json
import time

gov = NodeBetaGovernor()
payload_h = "172cb8a6b76fcc8151a3f0e2d940f1bcf7789aa3c62b94a3ae9bd2c50a17e5cb"
permit = gov.issue_grant(target_digest=payload_h, scope="OSIRIS_HP001_PHASE2_RECONSTRUCTED_RECOVERY_V1", ttl_seconds=86400)
print("Issued permit:", permit)
